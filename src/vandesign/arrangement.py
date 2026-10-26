"""Any number of furniture instances in one design.

Each instance gets its own parameter namespace (``<prefix>_<name>``, so two
cabinets never share ``Cab_Width``), editable position parameters
(``<prefix>_Pos_X/Y/Z``), a quarter-turn orientation and stable ids
``<instance_id>.<module id>``. Modules keep their own builders unchanged.
Instances may touch but never share material; an optional lined envelope
adds reference geometry and the B1 fit check.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import math
import re

from .cad.protocol import preflight
from .components.ids import make_id
from .components.model import AssemblyDefinition
from .core.expr import Param, substitute
from .core.params import ParamDef, ParameterSet
from .core.placement import place_box
from .modules.bed_platform import build_bed_platform
from .modules.storage_box import build_storage_box
from .modules.variants import build_variant
from .schemas.bed_platform_spec import load_bed_spec
from .schemas.design_spec import load_design_spec
from .schemas.storage_box_spec import load_storage_spec

SCHEMA = "vandesign.arrangement/1"
MAX_INSTANCES = 24
_PREFIX = re.compile(r"^[A-Z][A-Za-z0-9]{0,11}$")
_INSTANCE_KEYS = {"instance_id", "module", "param_prefix", "spec", "position_mm", "quarter_turns"}


def _cabinet(text):
    spec = load_design_spec(text)
    return build_variant(spec.resolved_params, spec.profile)


# module -> (builder from spec JSON text, local footprint (width, depth, height))
MODULES = {
    "cabinet": (_cabinet, lambda p: (p("Cab_Width"), p("Cab_Ply") + p("Cab_Depth"), p("Cab_Height"))),
    "bed": (lambda t: build_bed_platform(load_bed_spec(t)),
            lambda p: (p("Bed_Width"), p("Bed_Length"), p("Bed_Height"))),
    "storage_box": (lambda t: build_storage_box(load_storage_spec(t)),
                    lambda p: (p("Storage_Width"), p("Storage_Length"), p("Storage_Height"))),
}


class ArrangementError(ValueError):
    pass


@dataclass(frozen=True)
class Instance:
    instance_id: str
    module: str
    param_prefix: str
    spec: dict
    position_mm: tuple
    quarter_turns: int = 0

    def __post_init__(self):
        try:
            make_id(self.instance_id)
        except ValueError as exc:
            raise ArrangementError(str(exc)) from None
        if self.module not in MODULES:
            raise ArrangementError("Unknown module %r" % (self.module,))
        if not isinstance(self.param_prefix, str) or not _PREFIX.match(self.param_prefix):
            raise ArrangementError("param_prefix must match %s" % _PREFIX.pattern)
        if not isinstance(self.spec, dict):
            raise ArrangementError("spec must be an object")
        pos = self.position_mm
        if (not isinstance(pos, (list, tuple)) or len(pos) != 3
                or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 100000 for v in pos)):
            raise ArrangementError("position_mm must be three finite numbers")
        if type(self.quarter_turns) is not int or self.quarter_turns not in (0, 1, 2, 3):
            raise ArrangementError("quarter_turns must be 0, 1, 2 or 3")
        object.__setattr__(self, "position_mm", tuple(float(v) for v in pos))


def load_arrangement(text):
    """Strict JSON: {"schema_version": SCHEMA, "instances": [...]}."""
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ArrangementError("Duplicate key " + k)
            out[k] = v
        return out
    if not isinstance(text, (str, bytes)) or len(text) > 262144:
        raise ArrangementError("Arrangement JSON required, at most 256 KiB")
    raw = json.loads(text, object_pairs_hook=unique)
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "instances"} or raw["schema_version"] != SCHEMA:
        raise ArrangementError("Invalid arrangement schema")
    items = raw["instances"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_INSTANCES:
        raise ArrangementError("1-%d instances required" % MAX_INSTANCES)
    out = []
    for item in items:
        if not isinstance(item, dict) or set(item) != _INSTANCE_KEYS:
            raise ArrangementError("Each instance needs exactly: " + ", ".join(sorted(_INSTANCE_KEYS)))
        out.append(Instance(**item))
    return tuple(out)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _place_instance(inst):
    builder, footprint = MODULES[inst.module]
    source = builder(_canonical(inst.spec))
    preflight(source)
    if any(p.corner_radius is not None for p in source.panels):
        raise ArrangementError("%s: rounded panels are not placeable yet" % inst.instance_id)
    # The declared footprint must contain the module at its own values.
    env = source.parameters.resolve()
    fw, fd, fh = (e.eval(env) for e in footprint(Param))
    for p in source.panels:
        b = p.box.resolve(env)
        if min(b.lo) < -1e-9 or b.hi[0] > fw + 1e-9 or b.hi[1] > fd + 1e-9 or b.hi[2] > fh + 1e-9:
            raise ArrangementError("%s: panel %s lies outside the module footprint"
                                   % (inst.instance_id, p.stable_id))

    pre = inst.param_prefix + "_"
    names = source.parameters.names()
    mapping = {n: Param(pre + n) for n in names}
    sub = lambda e: substitute(e, mapping)  # noqa: E731
    pos_names = tuple(pre + "Pos_" + a for a in "XYZ")
    params = [ParamDef(n, value_mm=v, comment="%s placement (finished frame)" % inst.instance_id)
              for n, v in zip(pos_names, inst.position_mm)]
    for d in source.parameters.params:
        params.append(ParamDef(pre + d.name, value_mm=d.value_mm,
                               expr=None if d.expr is None else sub(d.expr),
                               comment=("%s: " % inst.instance_id) + d.comment))
    w, d_, _ = footprint(lambda n: mapping[n])
    pos = tuple(Param(n) for n in pos_names)
    k = inst.quarter_turns

    def placed(box):
        return place_box(type(box)(tuple(sub(e) for e in box.origin), tuple(sub(e) for e in box.size)),
                         k, w, d_, pos)

    ids = {p.stable_id: make_id(inst.instance_id, p.stable_id) for p in source.panels}
    panels = [replace(p, stable_id=ids[p.stable_id], box=placed(p.box)) for p in source.panels]
    ops = [replace(o, operation_id=make_id(inst.instance_id, o.operation_id),
                   target_panel_id=ids[o.target_panel_id], mating_panel_id=ids[o.mating_panel_id],
                   cut=placed(o.cut), groove_depth=sub(o.groove_depth),
                   end_clearance=sub(o.end_clearance), slot_clearance=sub(o.slot_clearance),
                   quarter_turns=(o.quarter_turns + k) % 4)
           for o in source.operations]
    cons = [replace(c, constraint_id=make_id(inst.instance_id, c.constraint_id),
                    lhs=sub(c.lhs), rhs=sub(c.rhs)) for c in source.constraints]
    return source, params, panels, ops, cons


@dataclass(frozen=True)
class Arrangement:
    assembly: AssemblyDefinition
    instances: tuple
    fit: dict | None  # B1 fit report when an envelope was supplied
    owners: dict      # furniture panel id -> instance id, recorded at placement


def collisions(assembly, env, owners):
    """Pairs of panels from different instances that share positive volume.

    Membership comes from ``owners`` (recorded when each instance is placed),
    never from id prefixes, so no instance id can capture another's panels.
    """
    boxes = [(p.stable_id, owners[p.stable_id], p.box.resolve(env))
             for p in assembly.panels if p.material_ref != "reference_only"]
    hits = []
    for i, (a, ia, ba) in enumerate(boxes):
        for b, ib, bb in boxes[i + 1:]:
            if ia != ib and all(min(ba.hi[n], bb.hi[n]) > max(ba.lo[n], bb.lo[n]) for n in range(3)):
                hits.append((a, b))
    return hits


def build_arrangement(instances, envelope=None):
    """Compose instances (and an optional EnvelopeSpec); refuse collisions/misfit."""
    instances = tuple(instances)
    if not 1 <= len(instances) <= MAX_INSTANCES or any(type(i) is not Instance for i in instances):
        raise ArrangementError("1-%d Instance records required" % MAX_INSTANCES)
    for attr in ("instance_id", "param_prefix"):
        values = [getattr(i, attr) for i in instances]
        if len(set(values)) != len(values):
            raise ArrangementError("Duplicate %s" % attr)
    # Nested ids ('a' and 'a.b') would make '<instance>.<module id>' ambiguous.
    ids = sorted(i.instance_id for i in instances)
    for a in ids:
        for b in ids:
            if b.startswith(a + "."):
                raise ArrangementError("Nested instance ids are not allowed: %r inside %r" % (b, a))
    params, panels, ops, cons, sources, owners = [], [], [], [], [], {}
    for inst in instances:
        source, p, pa, o, c = _place_instance(inst)
        params += p; panels += pa; ops += o; cons += c
        owners.update((panel.stable_id, inst.instance_id) for panel in pa)
        sources.append(dict(instance_id=inst.instance_id, module=inst.module, spec_hash=source.spec_hash,
                            prefix=inst.param_prefix, position_mm=list(inst.position_mm),
                            quarter_turns=inst.quarter_turns))
    identity = dict(schema=SCHEMA, instances=sources)
    if envelope is not None:
        from .modules.test_envelope import lined_parameters, lined_reference_panels
        params += list(lined_parameters(envelope))
        panels += lined_reference_panels(envelope)
        identity["envelope"] = envelope.to_json()
    assembly = AssemblyDefinition("arrangement.001",
                                  hashlib.sha256(_canonical(identity).encode()).hexdigest(),
                                  ParameterSet(tuple(params)), tuple(panels), tuple(ops), tuple(cons))
    assembly.validate_structure()
    env = assembly.parameters.resolve()
    failed = [c.constraint_id for c, ok, _, _ in assembly.check_constraints(env) if not ok]
    if failed:
        raise ArrangementError("Constraint violations: " + ", ".join(failed))
    hits = collisions(assembly, env, owners)
    if hits:
        raise ArrangementError("Instances share material: " + "; ".join("%s / %s" % h for h in hits[:5]))
    fit = None
    if envelope is not None:
        from .modules.test_envelope import preview_lined_fit
        try:
            fit = preview_lined_fit(assembly, envelope, env)
        except ValueError as exc:
            raise ArrangementError("Envelope fit refused: %s" % exc) from None
    return Arrangement(assembly, instances, fit, owners)
