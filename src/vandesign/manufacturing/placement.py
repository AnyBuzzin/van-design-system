"""Manufacturing profiles for a whole arrangement, each with its world frame.

Box-model instances take their profiles from the placed assembly. Profile
modules (cabinet_tab_slot) are profiled in their own module frame at the
instance's current parameter values, then placed with the same quarter-turn
and position mapping the arrangement uses for its box model.
"""
from __future__ import annotations

from dataclasses import replace

from ..arrangement import MODULES, PROFILE_MODULES, _canonical, tab_slot_parts
from ..components.ids import make_id
from ..core.expr import Param, substitute
from .assembly import assembly_profiles
from .carcass import WIDTH, cabinet_tab_slot_profiles, cabinet_tab_slot_width_bindings
from .profile import PanelFrame, ProfileError


def place_point(p, k, w, d, position):
    """Module-frame point -> world, matching core.placement.place_box."""
    x, y, z = p
    x, y = ((x, y), (d - y, x), (w - x, d - y), (y, w - x))[k]
    return (position[0] + x, position[1] + y, position[2] + z)


def place_axis(a, k):
    x, y, z = a
    x, y = ((x, y), (-y, x), (-x, -y), (y, -x))[k]
    return (x + 0.0, y + 0.0, z)


def place_frame(frame, k, w, d, position):
    return PanelFrame(place_point(frame.origin, k, w, d, position), place_axis(frame.u, k),
                      place_axis(frame.v, k), place_axis(frame.w, k))


def _profiled_instance(arrangement, inst, env, relief=True):
    builder, footprint = MODULES[inst.module]
    module = builder(_canonical(inst.spec))
    pre = inst.param_prefix + "_"
    values = {p.name: env[pre + p.name] for p in module.parameters.base()}
    local = module.parameters.resolve(values)
    w, d, _ = (e.eval(local) for e in footprint(Param))
    position = tuple(env[pre + "Pos_" + a] for a in "XYZ")
    _, joinery = tab_slot_parts(inst.spec)
    profiles, results = cabinet_tab_slot_profiles(module, joinery, values, relief=relief)
    placed = {}
    for p in profiles:
        pid = make_id(inst.instance_id, p.panel_id)
        placed[pid] = replace(p, panel_id=pid,
                              frame=place_frame(p.frame, inst.quarter_turns, w, d, position))
    return placed, joinery, results


def arrangement_profiles(arrangement, values=None, *, tool_diameter, relief=True):
    """Profiles (with world frames) for every furniture panel, in arrangement order.

    ``tool_diameter`` relieves box-model parts and must equal the joinery tool
    of every tab-and-slot instance (their relief is part of the joint geometry).
    ``relief=False`` is the relief-free view (#95 Option B): same panels,
    ids, frames and features without dog-bone arcs; ``tool_diameter`` must
    still equal each joinery tool. Default relieved profiles are unchanged.
    Returns (profiles, {instance_id: joint results}).
    """
    asm = arrangement.assembly
    env = asm.parameters.resolve(values)
    placed, joints = {}, {}
    for inst in arrangement.instances:
        if inst.module in PROFILE_MODULES:
            parts, joinery, results = _profiled_instance(arrangement, inst, env, relief)
            if abs(joinery.tool_diameter_mm - tool_diameter) > 1e-9:
                raise ProfileError("%s joinery tool %.3f mm differs from the export tool %.3f mm"
                                   % (inst.instance_id, joinery.tool_diameter_mm, tool_diameter))
            placed.update(parts)
            joints[inst.instance_id] = results
    profiled_ids = {pid for pid, owner in arrangement.owners.items()
                    if next(i for i in arrangement.instances if i.instance_id == owner).module in PROFILE_MODULES}
    for p in assembly_profiles(asm, values, tool_diameter=tool_diameter, relief=relief):
        if p.panel_id not in profiled_ids:
            placed[p.panel_id] = p
    order = [p.stable_id for p in asm.panels if p.material_ref != "reference_only"]
    if set(order) != set(placed):
        raise ProfileError("Profiled panels do not match the arrangement")
    return tuple(placed[pid] for pid in order), joints


def arrangement_width_bindings(arrangement, instance_id, values=None, *, interval=(1000.0, 1100.0), relief=True):
    """World-frame PanelBindings for one tab-and-slot cabinet's native width edit (#95).

    The module-frame bindings are renamed to the instance's parameters and
    placed with the same quarter-turn and position mapping as the profiles;
    the result is checked against ``arrangement_profiles`` at both interval
    ends. ``interval`` is a preflight bound, not a live-qualified range.
    ``relief=False`` binds the relief-free view (lines only, same ids and Expr
    vertices) and checks it against ``arrangement_profiles(relief=False)``.
    Returns {world panel id: PanelBinding}.
    """
    inst = next((i for i in arrangement.instances if i.instance_id == instance_id), None)
    if inst is None or inst.module != "cabinet_tab_slot":
        raise ProfileError("%r is not a tab-and-slot cabinet in this arrangement" % (instance_id,))
    env = arrangement.assembly.parameters.resolve(values)
    builder, footprint = MODULES[inst.module]
    module = builder(_canonical(inst.spec))
    pre = inst.param_prefix + "_"
    _, joinery = tab_slot_parts(inst.spec)
    local = cabinet_tab_slot_width_bindings(module, joinery, {p.name: env[pre + p.name]
                                                              for p in module.parameters.base()},
                                            interval=interval, relief=relief)
    names = {name: Param(pre + name) for name in module.parameters.names()}

    def rename(e):
        return substitute(e, names)
    w, d, _ = (rename(e) for e in footprint(Param))
    position = tuple(Param(pre + "Pos_" + a) for a in "XYZ")
    k = inst.quarter_turns
    out = {}
    for pid, b in local.items():
        world = make_id(inst.instance_id, pid)
        out[world] = replace(
            b, panel_id=world, parameter=pre + b.parameter,
            frame_origin=place_point(tuple(rename(e) for e in b.frame_origin), k, w, d, position),
            frame_axes=tuple(place_axis(a, k) for a in b.frame_axes), thickness=rename(b.thickness),
            outline=b.outline.rename(rename),
            features=tuple(replace(f, feature_id=world + f.feature_id[len(pid):],
                                   depth=None if f.depth is None else rename(f.depth),
                                   loop=f.loop.rename(rename)) for f in b.features))
    base = {p.name: p.value_mm for p in arrangement.assembly.parameters.base()}
    base.update(values or {})
    for x in interval:
        at = dict(base, **{pre + WIDTH: float(x)})
        profiles, _ = arrangement_profiles(arrangement, at, tool_diameter=joinery.tool_diameter_mm, relief=relief)
        world_env = arrangement.assembly.parameters.resolve(at)
        for p in profiles:
            if p.panel_id in out:
                problem = out[p.panel_id].mismatch(p, world_env)
                if problem:
                    raise ProfileError("%s binding differs at %s=%g: %s" % (p.panel_id, pre + WIDTH, x, problem))
    return out
