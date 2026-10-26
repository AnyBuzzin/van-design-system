"""validate(assembly, source) -> ValidationReport.

Reads the CURRENT base parameter values from the CAD model (so it works after
the user edits parameters in Fusion), re-derives everything with the pure core,
and compares that to the measured solids.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, Mapping, Optional, Tuple

from ..components.model import AssemblyDefinition
from ..core.expr import ExprError
from ..core.geometry import Box, GeometryError, RoundedCornerOutline
from ..core.params import ParameterError
from ..core.placement import box_to_local, point_to_world
from ..core.units import MODEL_EPSILON_MM, VOLUME_REL_TOL
from .geometry_source import GeometrySource, MeasuredBody
from .report import FAIL, PASS, UNKNOWN, Check, ValidationReport

PROBE_OFFSET_MM = 0.1


def _cmp(report, cid, observed, expected, tol, unit="mm", ids=(), note=""):
    if observed is None:
        report.add(Check(cid, UNKNOWN, None, expected, tol, unit, tuple(ids), note or "evidence unavailable"))
        return
    ok = abs(observed - expected) <= tol
    report.add(Check(cid, PASS if ok else FAIL, observed, expected, tol, unit, tuple(ids), note))


def _census_check(rep, assembly, source):
    """entities.managed_ids: exact multiplicity census of managed stable ids."""
    expected = Counter(p.stable_id for p in assembly.panels)
    exp_total = float(sum(expected.values()))
    fn = getattr(source, "managed_ids", None)
    observed = None
    if callable(fn):
        try:
            observed = fn()
        except Exception as e:  # recorded, never silent; check becomes UNKNOWN
            rep.diagnostics.append("managed id census failed: %s" % e)
    if not isinstance(observed, Mapping):
        rep.add(Check("entities.managed_ids", UNKNOWN, None, exp_total, 0.0, "entities", (),
                      "managed-id enumeration unavailable"))
        return
    missing = sorted(i for i in expected if observed.get(i, 0) == 0)
    duplicate = sorted(i for i in expected if observed.get(i, 0) > expected[i])
    unexpected = sorted(i for i in observed if i not in expected and observed[i] > 0)
    problems = []
    if missing:
        problems.append("missing: " + ", ".join(missing))
    if duplicate:
        problems.append("duplicate: " + ", ".join("%s x%d" % (i, observed[i]) for i in duplicate))
    if unexpected:
        problems.append("unexpected: " + ", ".join("%s x%d" % (i, observed[i]) for i in unexpected))
    total = float(sum(v for v in observed.values()))
    rep.add(Check("entities.managed_ids", FAIL if problems else PASS, total, exp_total, 0.0, "entities",
                  tuple(missing + duplicate + unexpected), "; ".join(problems)))


def _range_checks(rep, source, limits, variant, eps_mm):
    """Provisional profile ranges on LIVE parameter values.  Never clamps."""
    for name in sorted(limits):
        lo, hi = limits[name]
        cid = "profile.%s.%s_range" % (variant, name[len("Cab_"):].lower())
        v = source.parameter_value(name)
        note = "provisional fixture range %.1f-%.1f mm (not an engineering limit)" % (lo, hi)
        if v is None:
            rep.add(Check(cid, UNKNOWN, None, None, eps_mm, "mm", (), "parameter not readable; " + note,
                          limit_min=lo, limit_max=hi))
        else:
            ok = lo - eps_mm <= v <= hi + eps_mm
            rep.add(Check(cid, PASS if ok else FAIL, v, None, eps_mm, "mm", (),
                          ("OUT OF RANGE: " if not ok else "") + note, limit_min=lo, limit_max=hi))


def validate(assembly: AssemblyDefinition, source: GeometrySource, eps_mm: float = MODEL_EPSILON_MM,
             profile_limits: Optional[Mapping[str, Tuple[float, float]]] = None,
             profile_variant: str = "profile") -> ValidationReport:
    rep = ValidationReport()

    # 1. Current base parameters as stored in the CAD model.
    overrides: Dict[str, float] = {}
    for p in assembly.parameters.base():
        v = source.parameter_value(p.name)
        if v is None:
            rep.add(Check("param.%s.readable" % p.name, UNKNOWN, note="parameter not readable; nominal value used"))
        else:
            overrides[p.name] = v
    try:
        env = assembly.parameters.resolve(overrides)
    except (ParameterError, ExprError) as e:
        rep.add(Check("parameters.resolve", FAIL, note=str(e)))
        return rep

    # 2. Constraints at the current values.
    for c, ok, a, b in assembly.check_constraints(env):
        rep.add(Check("constraint.%s" % c.constraint_id, PASS if ok else FAIL, a, b, None, "mm", (), c.description))

    # 3. Derived parameters: Fusion's evaluation vs the pure-Python evaluation.
    for p in assembly.parameters.derived():
        _cmp(rep, "param.%s" % p.name, source.parameter_value(p.name), env[p.name], eps_mm)

    # 4. Expected geometry.
    try:
        blank: Dict[str, Box] = {p.stable_id: p.box.resolve(env) for p in assembly.panels}
        cuts = [(o, o.cut.resolve(env)) for o in assembly.operations]
    except GeometryError as e:
        rep.add(Check("geometry.expected", FAIL, note=str(e)))
        return rep

    for i, (oa, ca) in enumerate(cuts):
        for ob, cb in cuts[i + 1:]:
            if oa.target_panel_id == ob.target_panel_id and ca.overlap_volume(cb) > 0:
                rep.add(Check("cuts.disjoint.%s.%s" % (oa.operation_id, ob.operation_id), FAIL, note="cuts overlap at current parameters"))

    expected_volume: Dict[str, float] = {}
    for p in assembly.panels:
        v = blank[p.stable_id].volume
        if p.corner_radius is not None:
            try:
                w, l, t = blank[p.stable_id].size
                v = RoundedCornerOutline(w, l, p.corner_radius.eval(env)).area_mm2 * t
            except GeometryError as e:
                rep.add(Check("geometry.expected", FAIL, note=str(e)))
                return rep
        for o, c in cuts:
            if o.target_panel_id == p.stable_id:
                v -= blank[p.stable_id].overlap_volume(c)
        expected_volume[p.stable_id] = v

    # 5. Per-panel measured bbox and volume.
    bodies = {}
    for p in assembly.panels:
        pid = p.stable_id
        m = source.body(pid)
        bodies[pid] = m
        if m is None:
            rep.add(Check("%s.bbox" % pid, UNKNOWN, note="body not measurable", object_ids=(pid,)))
            rep.add(Check("%s.volume" % pid, UNKNOWN, note="body not measurable", object_ids=(pid,)))
            continue
        dev, where = blank[pid].max_deviation(m.box)
        rep.add(Check("%s.bbox" % pid, PASS if dev <= eps_mm else FAIL, dev, 0.0, eps_mm, "mm", (pid,),
                      "worst at %s" % where if dev > eps_mm else ""))
        exp_v = expected_volume[pid]
        tol = max(1.0, VOLUME_REL_TOL * exp_v)
        _cmp(rep, "%s.volume" % pid, m.volume_mm3, exp_v, tol, "mm3", (pid,),
             "rounded contour area times thickness" if p.corner_radius is not None else
             "blank minus its own grooves only")

    # 6. Dado joint relationships measured on the actual solids, evaluated in
    #    the module's own frame (identity for unrotated modules).
    for o, world_cut in cuts:
        k = o.quarter_turns
        cut = box_to_local(world_cut, k)
        mate = bodies.get(o.mating_panel_id)
        if mate is not None and k:
            mate = MeasuredBody(box_to_local(mate.box, k), mate.volume_mm3)
        ids = (o.target_panel_id, o.mating_panel_id)
        oid = o.operation_id
        depth, ec, sc = o.groove_depth.eval(env), o.end_clearance.eval(env), o.slot_clearance.eval(env)
        if mate is None:
            for tag in ("penetration", "end_gap", "gap_below", "gap_above", "mating_unmodified"):
                rep.add(Check("%s.%s" % (oid, tag), UNKNOWN, object_ids=ids, note="mating body not measurable"))
        else:
            sb = mate.box
            if o.side == "left":
                pen = min(sb.hi[0], cut.hi[0]) - max(sb.lo[0], cut.lo[0])
                end_gap = sb.lo[0] - cut.lo[0]
            else:
                pen = min(sb.hi[0], cut.hi[0]) - max(sb.lo[0], cut.lo[0])
                end_gap = cut.hi[0] - sb.hi[0]
            _cmp(rep, "%s.penetration" % oid, pen, depth - ec, eps_mm, "mm", ids)
            _cmp(rep, "%s.end_gap" % oid, end_gap, ec, eps_mm, "mm", ids)
            _cmp(rep, "%s.gap_below" % oid, sb.lo[2] - cut.lo[2], sc / 2, eps_mm, "mm", ids)
            _cmp(rep, "%s.gap_above" % oid, cut.hi[2] - sb.hi[2], sc / 2, eps_mm, "mm", ids)
            _cmp(rep, "%s.mating_unmodified" % oid, mate.volume_mm3, blank[o.mating_panel_id].volume,
                 max(1.0, VOLUME_REL_TOL * blank[o.mating_panel_id].volume), "mm3", ids,
                 "the cut must not touch the shelf")

        # 7. BRep point probes prove the groove is real, open at the front, and bounded.
        cx, cy, cz = [(l + h) / 2 for l, h in zip(cut.lo, cut.hi)]
        far_x = cut.lo[0] - PROBE_OFFSET_MM if o.side == "left" else cut.hi[0] + PROBE_OFFSET_MM
        probes = [
            ("centre_empty", (cx, cy, cz), False),
            ("front_open", (cx, cut.lo[1] + PROBE_OFFSET_MM, cz), False),
            ("below_solid", (cx, cy, cut.lo[2] - PROBE_OFFSET_MM), True),
            ("above_solid", (cx, cy, cut.hi[2] + PROBE_OFFSET_MM), True),
            ("far_wall_solid", (far_x, cy, cz), True),
            ("rear_wall_solid", (cx, cut.hi[1] + PROBE_OFFSET_MM, cz), True),
        ]
        for tag, pt, want in probes:
            got = source.point_in_material(o.target_panel_id, point_to_world(pt, k))
            cid = "%s.probe.%s" % (oid, tag)
            if got is None:
                rep.add(Check(cid, UNKNOWN, object_ids=(o.target_panel_id,), note="containment unavailable"))
            else:
                rep.add(Check(cid, PASS if got == want else FAIL, object_ids=(o.target_panel_id,),
                              note="expected %s" % ("material" if want else "empty")))

    # 8. Interference among joined panels.
    joined = sorted({o.target_panel_id for o, _ in cuts} | {o.mating_panel_id for o, _ in cuts})
    if joined:
        n = source.interference_count(joined)
        if n is None:
            rep.add(Check("interference.joined", UNKNOWN, object_ids=tuple(joined), note="interference analysis unavailable"))
        else:
            rep.add(Check("interference.joined", PASS if n == 0 else FAIL, float(n), 0.0, 0.0, "pairs", tuple(joined)))

    # 9. Managed-entity census (multiplicity; added check, original checks unchanged).
    _census_check(rep, assembly, source)

    # 10. Optional provisional profile ranges (live values; added checks only).
    if profile_limits:
        _range_checks(rep, source, profile_limits, profile_variant, eps_mm)

    rep.diagnostics.extend(getattr(source, "diagnostics", []))
    return rep
