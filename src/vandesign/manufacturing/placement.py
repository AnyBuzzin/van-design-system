"""Manufacturing profiles for a whole arrangement, each with its world frame.

Box-model instances take their profiles from the placed assembly. Profile
modules (cabinet_tab_slot, worktop_l) are profiled in their own module frame
at the instance's current parameter values, then placed with the same
quarter-turn and position mapping the arrangement uses for its box model.
A worktop is one part for two box-model panels; it gets pilot holes under
every carcass-top fixing hole it rests on, and a sink cut-out must sit over a
carcass-top opening, never a solid top.
"""
from __future__ import annotations

from dataclasses import replace

from ..arrangement import MODULES, PROFILE_MODULES, _canonical, tab_slot_parts
from ..components.ids import make_id
from ..core.expr import Param, substitute
from .assembly import assembly_profiles
from .carcass import WIDTH, cabinet_tab_slot_profiles, cabinet_tab_slot_width_bindings
from .profile import Hole, PanelFrame, ProfileError, ThroughCut, contains_point, world_box
from .worktop import worktop_profiles


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


def _profiled_instance(arrangement, inst, env, tool_diameter):
    builder, footprint = MODULES[inst.module]
    module = builder(_canonical(inst.spec))
    pre = inst.param_prefix + "_"
    values = {p.name: env[pre + p.name] for p in module.parameters.base()}
    local = module.parameters.resolve(values)
    w, d, _ = (e.eval(local) for e in footprint(Param))
    position = tuple(env[pre + "Pos_" + a] for a in "XYZ")
    if inst.module == "worktop_l":
        profiles, merged = worktop_profiles(module, values, tool_diameter)
        profiles, joinery, results = tuple(profiles.values()), None, ()
    else:
        _, joinery = tab_slot_parts(inst.spec)
        (profiles, results), merged = cabinet_tab_slot_profiles(module, joinery, values), ()
    placed = {}
    for p in profiles:
        pid = make_id(inst.instance_id, p.panel_id)
        placed[pid] = replace(p, panel_id=pid,
                              frame=place_frame(p.frame, inst.quarter_turns, w, d, position))
    return placed, joinery, results, tuple(make_id(inst.instance_id, m) for m in merged)


def arrangement_profiles(arrangement, values=None, *, tool_diameter):
    """Profiles (with world frames) for every furniture panel, in arrangement order.

    ``tool_diameter`` relieves box-model parts and must equal the joinery tool
    of every tab-and-slot instance (their relief is part of the joint geometry).
    Returns (profiles, {instance_id: joint results}).
    """
    asm = arrangement.assembly
    env = asm.parameters.resolve(values)
    placed, joints, merged, tops = {}, {}, set(), {}
    for inst in arrangement.instances:
        if inst.module in PROFILE_MODULES:
            parts, joinery, results, gone = _profiled_instance(arrangement, inst, env, tool_diameter)
            merged.update(gone)
            if joinery is not None:
                if abs(joinery.tool_diameter_mm - tool_diameter) > 1e-9:
                    raise ProfileError("%s joinery tool %.3f mm differs from the export tool %.3f mm"
                                       % (inst.instance_id, joinery.tool_diameter_mm, tool_diameter))
                joints[inst.instance_id] = results
                if joinery.top is not None:
                    tops[make_id(inst.instance_id, "panel.top.001")] = joinery.top
            placed.update(parts)
    profiled_ids = {pid for pid, owner in arrangement.owners.items()
                    if next(i for i in arrangement.instances if i.instance_id == owner).module in PROFILE_MODULES}
    for p in assembly_profiles(asm, values, tool_diameter=tool_diameter):
        if p.panel_id not in profiled_ids:
            placed[p.panel_id] = p
    order = [p.stable_id for p in asm.panels if p.material_ref != "reference_only" and p.stable_id not in merged]
    if set(order) != set(placed) - merged:
        raise ProfileError("Profiled panels do not match the arrangement")
    for inst in arrangement.instances:
        if inst.module == "worktop_l":
            pid = make_id(inst.instance_id, "panel.worktop.001")
            placed[pid] = _fix_worktop(placed[pid], {t: (placed[t], spec) for t, spec in tops.items()},
                                       [placed[q] for q in order if q != pid])
    return tuple(placed[pid] for pid in order), joints


def _world_rect(profile, loop):
    (a0, b0), (a1, b1) = loop.bounds
    p, q = profile.frame.to_world(a0, b0, 0.0), profile.frame.to_world(a1, b1, 0.0)
    return (min(p[0], q[0]), min(p[1], q[1])), (max(p[0], q[0]), max(p[1], q[1]))


def _fix_worktop(worktop, tops, panels):
    """Refuse a sink cut-out over ANY panel whose top touches the worktop
    underside (a solid carcass top, a side's top edge, a divider) unless the
    panel lies flat and has a through opening containing the sink; then add
    pilot holes under each carcass-top fixing hole the worktop rests on."""
    underside = worktop.frame.to_world(0.0, 0.0, 0.0)[2]
    sinks = [_world_rect(worktop, f.loop) for f in worktop.features if isinstance(f, ThroughCut)]
    for panel in panels:
        (px0, py0, _), (px1, py1, pz1) = world_box(panel)
        if abs(pz1 - underside) > 1e-6:
            continue                                      # not directly under this worktop
        flat = abs(panel.frame.w[2]) == 1.0
        openings = [_world_rect(panel, f.loop) for f in panel.features if isinstance(f, ThroughCut)] if flat else []
        for (sx0, sy0), (sx1, sy1) in sinks:
            if min(sx1, px1) > max(sx0, px0) and min(sy1, py1) > max(sy0, py0) and not any(
                    ox0 <= sx0 and oy0 <= sy0 and sx1 <= ox1 and sy1 <= oy1 for (ox0, oy0), (ox1, oy1) in openings):
                raise ProfileError("%s: the sink cut-out sits over %s without an opening (for a carcass top, "
                                   "set top.sink_rail_mm)" % (worktop.panel_id, panel.panel_id))
    pilots = []
    for top, spec in tops.values():
        if abs(top.frame.to_world(0.0, 0.0, top.thickness)[2] - underside) > 1e-6:
            continue                                      # not directly under this worktop
        for h in top.features:
            if isinstance(h, Hole) and h.depth is None:
                x, y, _ = top.frame.to_world(h.center[0], h.center[1], top.thickness)
                a, b, _ = worktop.frame.to_local((x, y, underside))
                if contains_point(worktop.outline, (a, b)):
                    pilots.append(Hole((a, b), spec.pilot_hole_mm, spec.pilot_depth_mm, "bottom"))
    if not pilots:
        return worktop
    return replace(worktop, features=worktop.features + tuple(pilots),
                   notes=worktop.notes + ("%d hidden fixing pilots under carcass-top holes" % len(pilots),))


def arrangement_width_bindings(arrangement, instance_id, values=None, *, interval=(1000.0, 1100.0)):
    """World-frame PanelBindings for one tab-and-slot cabinet's native width edit (#95).

    The module-frame bindings are renamed to the instance's parameters and
    placed with the same quarter-turn and position mapping as the profiles;
    the result is checked against ``arrangement_profiles`` at both interval
    ends. ``interval`` is a preflight bound, not a live-qualified range.
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
                                            interval=interval)
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
            features=tuple(f.rename(rename, world + f.feature_id[len(pid):]) for f in b.features))
    base = {p.name: p.value_mm for p in arrangement.assembly.parameters.base()}
    base.update(values or {})
    for x in interval:
        at = dict(base, **{pre + WIDTH: float(x)})
        profiles, _ = arrangement_profiles(arrangement, at, tool_diameter=joinery.tool_diameter_mm)
        world_env = arrangement.assembly.parameters.resolve(at)
        for p in profiles:
            if p.panel_id in out:
                problem = out[p.panel_id].mismatch(p, world_env)
                if problem:
                    raise ProfileError("%s binding differs at %s=%g: %s" % (p.panel_id, pre + WIDTH, x, problem))
    return out
