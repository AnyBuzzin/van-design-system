"""First interior fixture. Coordinates and parameters are millimetres.

X runs across the van; Y runs front to rear; Z runs up. This is a
rectangular layout demonstration, not measured vehicle or structural data.
"""
from dataclasses import replace
import hashlib
import math

from ..components.model import AssemblyDefinition, Panel
from ..core.expr import Mm, Param
from ..core.geometry import Box, BoxExpr
from ..core.params import ParamDef, ParameterSet
from ..schemas.cabinet_spec import CabinetSpec
from .cabinet import build_cabinet


LAYOUT_KEYS = frozenset(('Bed_Width', 'Bed_Length', 'Bed_Height', 'Kitchen_X', 'Kitchen_Y'))


def build_interior(layout_mm=None):
    cabinet = build_cabinet(CabinetSpec())
    defaults = dict(Van_Width=1800, Van_Length=4000, Van_Height=2000,
                    Demo_Ply=18, Bed_Length=1900, Bed_Height=700,
                    Kitchen_X=50, Kitchen_Y=100)
    if layout_mm is not None:
        if not isinstance(layout_mm, dict) or set(layout_mm) - LAYOUT_KEYS:
            raise ValueError('Unknown layout input; use explicit supported millimetre parameters')
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in layout_mm.values()):
            raise ValueError('Layout values must be finite millimetre numbers')
        defaults['Bed_Width'] = 1764
        defaults.update(layout_mm)
    params = ParameterSet(cabinet.parameters.params + tuple(
        ParamDef(k, value_mm=v, comment="Interior demonstration; mm")
        for k, v in defaults.items()))
    zero = Mm(0)
    W, L, H, T, BL, BH = map(Param, (
        "Van_Width", "Van_Length", "Van_Height", "Demo_Ply", "Bed_Length", "Bed_Height"))
    offset = (Param("Kitchen_X"), Param("Kitchen_Y"), T)
    bed_width = Param('Bed_Width') if layout_mm is not None else W-2*T
    bed_x = (W-bed_width)/2 if layout_mm is not None else T

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
    panel("bed.deck.001", "Rear bed platform", (bed_x, L-T-BL, BH), (bed_width, BL, T))
    panel("bed.front.001", "Bed front support", (bed_x, L-T-BL, T), (bed_width, T, BH-T))
    panel("bed.rear.001", "Bed rear support", (bed_x, L-2*T, T), (bed_width, T, BH-T))
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
    if env['Bed_Length'] < 2*env['Demo_Ply']:
        raise ValueError('Bed length is too short for separate front/rear supports')
    boxes = {p.stable_id: p.box.resolve(env) for p in assembly.panels}
    from ..core.geometry import Box
    inside = Box((env['Demo_Ply'], 0, env['Demo_Ply']),
                 (env['Van_Width']-env['Demo_Ply'], env['Van_Length']-env['Demo_Ply'], env['Van_Height']))
    for sid, box in boxes.items():
        if not sid.startswith('van.') and not inside.contains_box(box):
            raise ValueError("Outside van envelope: " + sid)
    # Conservative occupied furniture envelopes include doors and under-bed space.
    # This prevents a cabinet being placed in a bed void merely because solids miss.
    furniture = []
    for prefix in ('bed.', 'panel.'):
        group = [box for sid, box in boxes.items() if sid.startswith(prefix)]
        furniture.append(Box(tuple(min(b.lo[i] for b in group) for i in range(3)),
                             tuple(max(b.hi[i] for b in group) for i in range(3))))
    if furniture[0].overlap_volume(furniture[1]) > 0:
        raise ValueError('Kitchen/storage overlaps rear-bed occupied envelope')
    return boxes
