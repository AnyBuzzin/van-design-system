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

NOTICE = "TEST ONLY - UNMEASURED"
CABINET_SPEC = '{"schema_version":"0.2","module":"cabinet@1","variant":"base","profile_version":1,"parameters":{"width_mm":1100}}'
REFERENCE = "reference."
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
    ref("left", "left sill", (-guide,zero,zero), (guide,l,Mm(150)))
    ref("right", "right sill", (w,zero,zero), (guide,l,Mm(150)))
    ref("front", "front height guide", (zero,l,zero), (w,guide,h))
    ref("arch.left", "ASSUMED arch 196 x 800 x 300; Y600", (zero,ay,zero), (aw,al,ah), "reference_obstruction")
    ref("arch.right", "ASSUMED arch 196 x 800 x 300; Y600", (w-aw,ay,zero), (aw,al,ah), "reference_obstruction")
    identity = canonical_json(dict(furniture=furniture.spec_hash, reference=DEFAULTS, notice=NOTICE))
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
