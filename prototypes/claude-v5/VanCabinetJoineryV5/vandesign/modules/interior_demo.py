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
VEHICLE_KEYS = frozenset(('Van_Width', 'Van_Length', 'Van_Height', 'Arch_Width', 'Arch_Length',
                          'Arch_Height', 'Arch_Left_Y', 'Arch_Right_Y', 'Min_Aisle'))


def build_interior(layout_mm=None, vehicle_mm=None):
    cabinet = build_cabinet(CabinetSpec())
    defaults = dict(Van_Width=1800, Van_Length=4000, Van_Height=2000,
                    Demo_Ply=18, Bed_Length=1900, Bed_Height=700,
                    Kitchen_X=50, Kitchen_Y=100)
    if vehicle_mm is not None:
        if (not isinstance(vehicle_mm, dict) or set(vehicle_mm)-VEHICLE_KEYS or
                any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                    for v in vehicle_mm.values())):
            raise ValueError('Vehicle inputs must be supported finite millimetre numbers')
        defaults.update(Arch_Width=250, Arch_Length=800, Arch_Height=300,
                        Arch_Left_Y=3000, Arch_Right_Y=3000, Min_Aisle=600)
        defaults.update(vehicle_mm)
    if layout_mm is not None:
        if not isinstance(layout_mm, dict) or set(layout_mm) - LAYOUT_KEYS:
            raise ValueError('Unknown layout input; use explicit supported millimetre parameters')
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in layout_mm.values()):
            raise ValueError('Layout values must be finite millimetre numbers')
        defaults['Bed_Width'] = defaults['Van_Width']-2*defaults['Demo_Ply']
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
    if vehicle_mm is not None:
        aw, al, ah = map(Param, ('Arch_Width', 'Arch_Length', 'Arch_Height'))
        panel('van.arch_left.001', 'Left wheel arch (restricted)', (T, Param('Arch_Left_Y'), T), (aw, al, ah))
        panel('van.arch_right.001', 'Right wheel arch (restricted)', (W-T-aw, Param('Arch_Right_Y'), T), (aw, al, ah))
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
    if 'Arch_Width' in env:
        vehicle_clearances(env, boxes)
    return boxes


def vehicle_clearances(env, boxes, tolerance_mm=1e-7):
    """Check either intended boxes or measured BRep boxes. No CAD dependency.

    Aisle is the straight strip to the right of the kitchen over its full Y
    footprint. Under-bed space admits arches but not bed structural material.
    """
    t = env['Demo_Ply']
    if min(env[k] for k in ('Arch_Width','Arch_Length','Arch_Height','Min_Aisle')) <= 0:
        raise ValueError('Wheel-arch dimensions and minimum aisle must be positive mm')
    inside = Box((boxes['van.left.001'].hi[0], boxes['van.floor.001'].lo[1], boxes['van.floor.001'].hi[2]),
                 (boxes['van.right.001'].lo[0], boxes['van.rear.001'].lo[1], boxes['van.rear.001'].hi[2]))
    arches = [boxes['van.arch_left.001'], boxes['van.arch_right.001']]
    if any(not inside.contains_box(a, eps=tolerance_mm) for a in arches) or arches[0].overlap_volume(arches[1]) > 1e-6:
        raise ValueError('Wheel arches exceed usable envelope or overlap each other')
    kitchen_panels = [b for sid,b in boxes.items() if sid.startswith('panel.')]
    kitchen = Box(tuple(min(b.lo[i] for b in kitchen_panels) for i in range(3)),
                  tuple(max(b.hi[i] for b in kitchen_panels) for i in range(3)))
    for arch in arches:
        if kitchen.overlap_volume(arch) > 1e-6:
            raise ValueError('Kitchen/storage occupies restricted wheel-arch space')
        for sid, body in boxes.items():
            if sid.startswith('bed.') and body.overlap_volume(arch) > 1e-6:
                raise ValueError('Bed structural material occupies restricted wheel-arch space: '+sid)
    # No vehicle intrusion or other furniture may reduce this designated strip.
    limit = boxes['van.right.001'].lo[0]
    for sid, body in boxes.items():
        if sid.startswith(('bed.', 'van.arch_')) and min(body.hi[1],kitchen.hi[1])-max(body.lo[1],kitchen.lo[1]) > 1e-6:
            if body.hi[0] > kitchen.hi[0]:
                limit = min(limit, max(kitchen.hi[0],body.lo[0]))
    aisle = limit-kitchen.hi[0]
    if aisle+tolerance_mm < env['Min_Aisle']:
        raise ValueError('Clear kitchen aisle %.3f mm is below required %.3f mm' % (aisle, env['Min_Aisle']))
    return dict(aisle_width_mm=aisle, minimum_aisle_mm=env['Min_Aisle'],
                bed_deck_above_arch_top_mm=min(boxes['bed.deck.001'].lo[2]-a.hi[2] for a in arches),
                prohibited_overlap_count=0)
