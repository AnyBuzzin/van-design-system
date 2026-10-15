"""First interior fixture. Coordinates and parameters are millimetres.

X runs across the van; Y runs front to rear; Z runs up. This is a
rectangular layout demonstration, not measured vehicle or structural data.
"""
from dataclasses import replace
import hashlib

from ..components.model import AssemblyDefinition, Panel
from ..core.expr import Mm, Param
from ..core.geometry import BoxExpr
from ..core.params import ParamDef, ParameterSet
from ..schemas.cabinet_spec import CabinetSpec
from .cabinet import build_cabinet


def build_interior():
    cabinet = build_cabinet(CabinetSpec())
    defaults = dict(Van_Width=1800, Van_Length=4000, Van_Height=2000,
                    Demo_Ply=18, Bed_Length=1900, Bed_Height=700,
                    Kitchen_X=50, Kitchen_Y=100)
    params = ParameterSet(cabinet.parameters.params + tuple(
        ParamDef(k, value_mm=v, comment="Interior demonstration; mm")
        for k, v in defaults.items()))
    zero = Mm(0)
    W, L, H, T, BL, BH = map(Param, (
        "Van_Width", "Van_Length", "Van_Height", "Demo_Ply", "Bed_Length", "Bed_Height"))
    offset = (Param("Kitchen_X"), Param("Kitchen_Y"), T)

    def shift(box):
        return BoxExpr(tuple(a + b for a, b in zip(box.origin, offset)), box.size)

    panels = [replace(p, box=shift(p.box)) for p in cabinet.panels]
    operations = tuple(replace(o, cut=shift(o.cut)) for o in cabinet.operations)

    def panel(sid, label, origin, size):
        panels.append(Panel(sid, label, sid.split('.')[0], "demo_ply", BoxExpr(origin, size)))

    # Open front and roof; low side sills show the envelope without hiding furniture.
    panel("van.floor.001", "Van floor", (zero, zero, zero), (W, L, T))
    panel("van.left.001", "Van left sill", (zero, zero, T), (T, L, Mm(150)))
    panel("van.right.001", "Van right sill", (W-T, zero, T), (T, L, Mm(150)))
    panel("van.rear.001", "Van rear envelope", (T, L-T, T), (W-2*T, T, H-T))
    panel("bed.deck.001", "Rear bed platform", (T, L-T-BL, BH), (W-2*T, BL, T))
    panel("bed.front.001", "Bed front support", (T, L-T-BL, T), (W-2*T, T, BH-T))
    panel("bed.rear.001", "Bed rear support", (T, L-2*T, T), (W-2*T, T, BH-T))
    result = AssemblyDefinition("interior.demo.001", hashlib.sha256(
        (cabinet.spec_hash + repr(defaults)).encode()).hexdigest(), params,
        tuple(panels), operations, cabinet.constraints)
    result.validate_structure()
    return result


def check_layout(assembly, env):
    """Reject envelope violations and kitchen/bed overlap before CAD or edits."""
    if min(env[k] for k in ("Van_Width", "Van_Length", "Van_Height", "Demo_Ply",
                            "Bed_Length", "Bed_Height")) <= 0:
        raise ValueError("Interior dimensions must be positive mm")
    boxes = {p.stable_id: p.box.resolve(env) for p in assembly.panels}
    from ..core.geometry import Box
    inside = Box((env['Demo_Ply'], 0, env['Demo_Ply']),
                 (env['Van_Width']-env['Demo_Ply'], env['Van_Length']-env['Demo_Ply'], env['Van_Height']))
    for sid, box in boxes.items():
        if not sid.startswith('van.') and not inside.contains_box(box):
            raise ValueError("Outside van envelope: " + sid)
        if sid.startswith('panel.') and box.overlap_volume(boxes['bed.deck.001']) > 0:
            raise ValueError("Kitchen overlaps rear bed: " + sid)
    if env['Kitchen_Y'] + env['Cab_Depth'] >= env['Van_Length']-env['Demo_Ply']-env['Bed_Length']:
        raise ValueError("Kitchen/bed zones overlap")
    return boxes
