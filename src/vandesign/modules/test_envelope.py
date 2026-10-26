"""Issue #51 nominal development fixture. NOT measured vehicle geometry."""
from dataclasses import replace
import hashlib
import math

from ..composition import compose_layout
from ..layout_preview import make_layout
from ..components.model import Panel
from ..core.expr import Mm, Param
from ..core.geometry import Box, BoxExpr
from ..core.params import ParamDef, ParameterSet
from ..panel_preview import canonical_json, panel_rows
from ..verification.readback import COORDINATE_READBACK_MM, same_except_readback_noise

NOTICE = "TEST ONLY - UNMEASURED"
CABINET_SPEC = '{"schema_version":"0.2","module":"cabinet@1","variant":"base","profile_version":1,"parameters":{"width_mm":1100}}'
REFERENCE = "reference."
B1_RESTORATION_COORDINATE_EPSILON_MM = COORDINATE_READBACK_MM
ARCHES = ("reference.arch.left", "reference.arch.right")
DEFAULTS = dict(Test_Width=1784, Test_Length=3044, Test_Height=2025,
                Test_Arch_Width=196, Test_Arch_Length=800, Test_Arch_Height=300,
                Test_Arch_Y=600)


def build_test_envelope():
    layout = make_layout([
        dict(instance_id="bed.001", translation_mm=[192,50,0]),
        dict(instance_id="cabinet.001", translation_mm=[50,2100,0])],
        cabinet_spec_json=CABINET_SPEC)
    furniture = compose_layout(layout, cabinet_spec_json=CABINET_SPEC).assembly
    params = ParameterSet(furniture.parameters.params + tuple(
        ParamDef(k, value_mm=v, comment=NOTICE + "; arbitrary arch assumptions" if "Arch" in k
                 else NOTICE + "; nominal clear interior, not measured") for k,v in DEFAULTS.items()))
    w,l,h,aw,al,ah,ay = (Param(k) for k in DEFAULTS)
    zero, guide = Mm(0), Mm(10)
    refs = []
    def ref(sid, label, origin, size, role="reference_guide"):
        refs.append(Panel(REFERENCE+sid, NOTICE+" - "+label, role, "reference_only",
                          BoxExpr(origin,size)))
    # Guides lie OUTSIDE the clear envelope. No roof or rear-threshold wall.
    ref("floor", "nominal floor", (zero,zero,-guide), (w,l,guide))
    ref("right", "right sill", (w,zero,zero), (guide,l,Mm(150)))
    ref("front", "front height guide", (zero,l,zero), (w,guide,h))
    ref("arch.left", "ASSUMED arch 196 x 800 x 300; Y600", (zero,ay,zero), (aw,al,ah), "reference_obstruction")
    ref("arch.right", "ASSUMED arch 196 x 800 x 300; Y600", (w-aw,ay,zero), (aw,al,ah), "reference_obstruction")
    identity = canonical_json(dict(furniture=furniture.spec_hash, reference=DEFAULTS,
                                   reference_ids=[p.stable_id for p in refs], notice=NOTICE))
    assembly = replace(furniture, assembly_id="test.transit_l2h3.001",
                       spec_hash=hashlib.sha256(identity.encode()).hexdigest(),
                       parameters=params, panels=furniture.panels+tuple(refs))
    assembly.validate_structure()
    preview_fit(assembly, assembly.parameters.resolve())
    return assembly


def furniture_rows(assembly):
    """Reference objects never enter the nominal furniture cut list."""
    return panel_rows(replace(assembly, panels=tuple(
        p for p in assembly.panels if not p.stable_id.startswith(REFERENCE))))


def preview_fit(assembly, env, boxes=None):
    """Pure guard, also applied to complete measured BRep bounds; no CAD writes."""
    if set(env) != set(assembly.parameters.names()) or any(
            type(v) not in (int,float) or not math.isfinite(v) for v in env.values()):
        raise ValueError("Complete finite parameter observations required")
    if any(not ok for _,ok,_,_ in assembly.check_constraints(env)):
        raise ValueError("Invalid furniture dimensions")
    if any(env[k] <= 0 for k in DEFAULTS):
        raise ValueError("Invalid test envelope dimensions")
    expected_ids = {p.stable_id for p in assembly.panels}
    boxes = boxes if boxes is not None else {p.stable_id:p.box.resolve(env) for p in assembly.panels}
    if set(boxes) != expected_ids or any(not all(math.isfinite(v) for v in b.lo+b.hi)
                                          or min(b.size)<=0 for b in boxes.values()):
        raise ValueError("Missing or invalid bounds")
    inside = Box((0,0,0),(env['Test_Width'],env['Test_Length'],env['Test_Height']))
    arches = [boxes[k] for k in ARCHES]
    furniture = {k:b for k,b in boxes.items() if not k.startswith(REFERENCE)}
    if any(not inside.contains_box(b,eps=0.01) for b in list(furniture.values())+arches):
        raise ValueError("Outside nominal test envelope")
    if arches[0].overlap_volume(arches[1]) > 1e-6:
        raise ValueError("Assumed arches overlap")
    def envelope(prefix):
        group = [b for k,b in furniture.items() if k.startswith(prefix)]
        return Box(tuple(min(b.lo[i] for b in group) for i in range(3)),
                   tuple(max(b.hi[i] for b in group) for i in range(3)))
    bed,cab = envelope('bed.001.'),envelope('cabinet.001.')
    for arch in arches:
        if cab.overlap_volume(arch)>1e-6:
            raise ValueError("Cabinet occupies assumed arch")
        for sid,b in furniture.items():
            if sid.startswith('bed.001.') and b.overlap_volume(arch)>1e-6:
                raise ValueError("Bed panel intrudes into assumed arch: "+sid)
    if bed.overlap_volume(cab)>1e-6:
        raise ValueError("Furniture occupied envelopes overlap")
    return dict(outcome="PASS", notice=NOTICE,
                deck_to_arch_mm=boxes['bed.001.bed.deck.001'].lo[2]-max(a.hi[2] for a in arches),
                nominal_right_strip_mm=inside.hi[0]-cab.hi[0])


def preview_invalid_arch(assembly, env):
    # Fixed proposed bed move +600 mm in Y puts its support into the arches.
    # The preview works on intended boxes only, with no Fusion setter.
    boxes = {p.stable_id:p.box.resolve(env) for p in assembly.panels}
    for sid,b in list(boxes.items()):
        if sid.startswith('bed.001.'):
            boxes[sid] = Box((b.lo[0],b.lo[1]+600,b.lo[2]), (b.hi[0],b.hi[1]+600,b.hi[2]))
    try:
        preview_fit(assembly, env, boxes)
    except ValueError as exc:
        return dict(outcome="REFUSED", reason=str(exc), proposed_bed_delta_y_mm=600)
    return dict(outcome="FAIL", reason="Unsafe bed intrusion was not refused")


# B1 is separate from the accepted Issue #51 fixture and its historical hashes.
_ENV_FIELDS = dict(
    bare_width_mm="Env_Bare_Width", bare_length_mm="Env_Bare_Length",
    bare_height_mm="Env_Bare_Height", lining_mm="Env_Lining",
    tolerance_mm="Env_Tolerance", bare_between_arches_mm="Env_Between_Arches",
    arch_length_mm="Env_Arch_Length", arch_height_mm="Env_Arch_Bare_Height",
    arch_y_mm="Env_Arch_Bare_Y", ceiling_split_mm="Env_Ceiling_Split",
    second_bare_height_mm="Env_Second_Bare_Height",
    upper_left_break_mm="Env_Upper_Left_Break", upper_left_inset_mm="Env_Upper_Left_Inset",
    upper_right_break_mm="Env_Upper_Right_Break", upper_right_inset_mm="Env_Upper_Right_Inset")


# Shared readback policy (verification/readback.py); name kept for existing callers.
restored_lined_measurements = same_except_readback_noise


def _lined_parameters(spec):
    parameters = [ParamDef(name, value_mm=getattr(spec, field),
                          comment=spec.provenance) for field, name in _ENV_FIELDS.items()
                  if getattr(spec, field) is not None]
    for k in spec.keepouts:
        for axis, origin, size in zip("XYZ", k.origin_mm, k.size_mm):
            parameters.extend((
                ParamDef(f"Env_{k.name}_{axis}", value_mm=origin, comment="Finished-frame "+k.kind),
                ParamDef(f"Env_{k.name}_{axis}_Size", value_mm=size, comment="Includes door clearance depth")))
    p = Param
    derived = dict(Env_Width=p("Env_Bare_Width")-2*p("Env_Lining"),
                   Env_Length=p("Env_Bare_Length")-2*p("Env_Lining"),
                   Env_Height=p("Env_Bare_Height")-2*p("Env_Lining"),
                   Env_Arch_Width=(p("Env_Bare_Width")-p("Env_Between_Arches"))/2-p("Env_Lining"),
                   Env_Arch_Height=p("Env_Arch_Bare_Height")-p("Env_Lining"),
                   Env_Arch_Y=p("Env_Arch_Bare_Y")-p("Env_Lining"))
    if spec.ceiling_split_mm is not None:
        derived["Env_Second_Height"] = p("Env_Second_Bare_Height")-2*p("Env_Lining")
    parameters.extend(ParamDef(k, expr=v, comment="Derived finished-frame mm") for k, v in derived.items())
    return tuple(parameters)


def build_lined_envelope(spec):
    """Same furniture, new reference data; no mutation or installed Runner access."""
    from ..schemas.envelope_spec import EnvelopeSpec
    from ..cad.protocol import preflight
    from .storage_box import build_storage_scene
    if type(spec) is not EnvelopeSpec:
        raise ValueError("EnvelopeSpec required")
    source = build_storage_scene()
    dz = Param("Env_Tolerance")
    def raised(box):
        return BoxExpr((box.origin[0], box.origin[1], box.origin[2]+dz), box.size)
    panels = [replace(p, box=raised(p.box)) for p in source.panels
              if not p.stable_id.startswith(REFERENCE)]
    operations = tuple(replace(op, cut=raised(op.cut)) for op in source.operations)
    parameters = ParameterSet(tuple(p for p in source.parameters.params
                                    if not p.name.startswith("Test_")) + _lined_parameters(spec))
    panels.extend(lined_reference_panels(spec))
    identity = canonical_json(dict(source=source.spec_hash, envelope=spec.to_json(),
                                   generator="lined-envelope@1", furniture_z="Env_Tolerance"))
    assembly = replace(source, assembly_id="reference.lined_interior.001",
                       spec_hash=hashlib.sha256(identity.encode()).hexdigest(),
                       parameters=parameters, panels=tuple(panels), operations=operations)
    preflight(assembly)
    preview_lined_fit(assembly, spec, parameters.resolve())
    return assembly


def lined_parameters(spec):
    """B1 envelope parameters (base and derived, finished-frame mm)."""
    return _lined_parameters(spec)


def lined_reference_panels(spec):
    """Reference-only guide/obstruction panels for an EnvelopeSpec (never cut)."""
    panels = []
    w, l, h = map(Param, ("Env_Width", "Env_Length", "Env_Height"))
    aw, al, ah, ay = map(Param, ("Env_Arch_Width", "Env_Arch_Length", "Env_Arch_Height", "Env_Arch_Y"))
    zero, guide = Mm(0), Mm(10)
    def ref(sid, origin, size, role="reference_guide"):
        panels.append(Panel(REFERENCE+sid, spec.provenance+" - "+sid, role,
                            "reference_only", BoxExpr(origin, size)))
    # Open left/rear for visibility; physical guides are outside the usable space.
    ref("floor", (zero, zero, -guide), (w, l, guide))
    ref("right", (w, zero, zero), (guide, l, Mm(150)))
    front_height = h if spec.ceiling_split_mm is None else Param("Env_Second_Height")
    ref("front", (zero, l, zero), (w, guide, front_height))
    first_length = l if spec.ceiling_split_mm is None else Param("Env_Ceiling_Split")
    ref("ceiling.first", (zero, zero, h), (w, first_length, guide))
    if spec.ceiling_split_mm is not None:
        ref("ceiling.second", (zero, first_length, front_height), (w, l-first_length, guide))
    ref("arch.left", (zero, ay, zero), (aw, al, ah), "reference_obstruction")
    ref("arch.right", (w-aw, ay, zero), (aw, al, ah), "reference_obstruction")
    for k in spec.keepouts:
        ref("keepout."+k.name, tuple(Param(f"Env_{k.name}_{a}") for a in "XYZ"),
            tuple(Param(f"Env_{k.name}_{a}_Size") for a in "XYZ"), "reference_obstruction")
    return panels


def _observed_spec(spec, env):
    """Revalidate edited parameters; topology and descriptive metadata stay pinned."""
    from ..schemas.envelope_spec import KeepOut
    fields = {field: env[name] for field, name in _ENV_FIELDS.items() if getattr(spec, field) is not None}
    keepouts = tuple(KeepOut(k.name, k.kind,
                            tuple(env[f"Env_{k.name}_{a}"] for a in "XYZ"),
                            tuple(env[f"Env_{k.name}_{a}_Size"] for a in "XYZ")) for k in spec.keepouts)
    return replace(spec, **fields, keepouts=keepouts)


def _positive_overlap(a, b):
    # Strict positive volume; do not inherit the generic Box epsilon here.
    return all(min(a.hi[i], b.hi[i]) > max(a.lo[i], b.lo[i]) for i in range(3))


def preview_lined_fit(assembly, spec, env, boxes=None):
    """Exact axis-aligned containment, including a non-convex stepped ceiling.

    Pure preview also accepts complete measured bounds. PASS describes this
    supplied geometry, not Fusion or real-vehicle qualification by itself.
    Raw parameter edits are not guarded automatically.
    """
    from ..schemas.envelope_spec import number
    if set(env) != set(assembly.parameters.names()) or not all(number(v) for v in env.values()):
        raise ValueError("Complete finite parameter observations required")
    resolved = assembly.parameters.resolve({p.name: env[p.name] for p in assembly.parameters.base()})
    if any(abs(env[n]-v) > 1e-9 for n, v in resolved.items()):
        raise ValueError("Contradictory derived parameter observations")
    current = _observed_spec(spec, env)
    if any(not ok for _, ok, _, _ in assembly.check_constraints(env)):
        raise ValueError("Invalid furniture dimensions")
    expected = {p.stable_id: p.box.resolve(env) for p in assembly.panels}
    boxes = expected if boxes is None else boxes
    if (set(boxes) != set(expected) or any(not isinstance(b, Box) or len(b.lo) != 3 or len(b.hi) != 3
            or not all(number(v) for v in b.lo+b.hi) or min(b.size) <= 0 for b in boxes.values())):
        raise ValueError("Complete finite positive bounds required")
    # Keep-outs are defined by validated data, never by a possibly misplaced body.
    # Reference body measurements must agree before they can support a fit result.
    if any(expected[k].max_deviation(boxes[k])[0] > 0.01
           for k in expected if k.startswith(REFERENCE)):
        raise ValueError("Reference geometry differs from envelope data")
    furniture = {k: b for k, b in boxes.items() if not k.startswith(REFERENCE)}
    if not furniture:
        raise ValueError("Furniture required")
    t = current.tolerance_mm
    w, length, _ = current.finished_size
    keepouts = {k: Box(tuple(v-t for v in b.lo), tuple(v+t for v in b.hi))
                for k, b in expected.items()
                if k in ARCHES or k.startswith(REFERENCE+"keepout.")}
    clearances, obstacle_gaps = {}, {}
    for sid, b in furniture.items():
        gaps = dict(left=b.lo[0]-t, right=w-t-b.hi[0], rear=b.lo[1]-t,
                    front=length-t-b.hi[1], floor=b.lo[2]-t)
        # Admit coordinate readback noise only; retain the inset and raw gaps.
        if min(gaps.values()) < -COORDINATE_READBACK_MM:
            raise ValueError("Outside inset envelope: "+sid)
        ceiling_gaps = []
        for start, end, height in current.segments:
            # Minkowski inset around the vertical riser as well as the ceiling.
            # Expanding each segment's upper forbidden region by t handles
            # either step direction without treating the space as convex.
            if b.lo[1] < end+t and b.hi[1] > start-t:
                ceiling_gaps.append(height-t-b.hi[2])
        if not ceiling_gaps or min(ceiling_gaps) < -COORDINATE_READBACK_MM:
            raise ValueError("Outside inset ceiling or step: "+sid)
        gaps["ceiling"] = min(ceiling_gaps)
        # B2: each sloped upper wall is a half-space; the usable space is convex
        # at the break, so every box corner at least t from the plane is exact.
        for side in current.upper_walls:
            gap = min(current.upper_wall_distance(side, x, z)
                      for x in (b.lo[0], b.hi[0]) for z in (b.lo[2], b.hi[2])) - t
            if gap < -COORDINATE_READBACK_MM:
                raise ValueError("Outside inset upper %s wall: %s" % (side, sid))
            gaps["upper_" + side] = gap
        for kid, obstacle in keepouts.items():
            if _positive_overlap(b, obstacle):
                raise ValueError("Panel occupies expanded keep-out: "+sid+" / "+kid)
            obstacle_gaps[sid+" / "+kid] = math.sqrt(sum(
                max(0, obstacle.lo[i]-b.hi[i], b.lo[i]-obstacle.hi[i])**2 for i in range(3)))
        clearances[sid] = gaps
    return dict(outcome="PASS", scope="supplied axis-aligned bounds only",
                provenance=current.provenance, finished_size_mm=current.finished_size,
                margin_mm=t, clearance_to_inset_planes_mm=clearances,
                clearance_to_expanded_keepouts_mm=obstacle_gaps,
                mounting_capacity="unqualified", raw_parameter_edits_guarded=False)
