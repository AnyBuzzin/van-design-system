"""One-piece L worktop profile: radiused corners, sink cut-out, hidden fixing pilots.

The box-model panels (modules.worktop: two legs and the conservative
inside-fillet box) are cut as ONE part with the id of leg A; the others are
reported as merged into it. Visible corners are filleted,
never dog-boned: the two front corners by WT_Front_Radius, the inside corner by
WT_Inside_Radius (at least the tool radius, so a round cutter can make it), the
sink cut-out corners by WT_Sink_Radius. Fixing pilots are added at arrangement
level, under carcass-top clearance holes (manufacturing.placement).
"""
from __future__ import annotations

from .profile import PanelFrame, PanelProfile, ProfileError, ThroughCut, polygon_loop, rect_vertices

PANEL, MERGED = "panel.worktop.001", ("panel.worktop.002", "panel.worktop.003")


def worktop_profiles(assembly, values, tool_diameter):
    """({panel id: module-frame PanelProfile}, merged panel ids)."""
    env = assembly.parameters.resolve(values)
    failed = [c.constraint_id for c, ok, _, _ in assembly.check_constraints(env) if not ok]
    if failed:
        raise ProfileError("Worktop constraints fail: " + ", ".join(failed))
    la, da, lb, db, t = (env[n] for n in ("WT_A_Length", "WT_A_Depth", "WT_B_Length", "WT_B_Depth", "WT_Thickness"))
    front, inside = env["WT_Front_Radius"], env["WT_Inside_Radius"]
    tool_r = tool_diameter / 2
    if inside < tool_r - 1e-9:
        raise ProfileError("Worktop inside-corner radius %.3f mm is below the %.3f mm tool radius" % (inside, tool_r))
    # CCW from the outer (wall) corner; index 2 and 4 are the front corners, 3 the inside corner.
    verts = ((0.0, 0.0), (la, 0.0), (la, da), (db, da), (db, lb), (0.0, lb))
    fillets = {3: inside}
    if front > 0:
        fillets.update({2: front, 4: front})
    outline = polygon_loop(verts, waste_inside=False, fillets=fillets)
    features, notes = (), ["one-piece L cut from a single sheet; corners radiused, no dog-bones"]
    if "WT_Sink_X" in env:
        x, y, w, l, rs = (env[n] for n in ("WT_Sink_X", "WT_Sink_Y", "WT_Sink_Width", "WT_Sink_Length",
                                            "WT_Sink_Radius"))
        if rs < tool_r - 1e-9:
            raise ProfileError("Sink corner radius %.3f mm is below the %.3f mm tool radius" % (rs, tool_r))
        cut = polygon_loop(rect_vertices(x - w / 2, y - l / 2, x + w / 2, y + l / 2), waste_inside=True,
                           fillets={i: rs for i in range(4)})
        features = (ThroughCut(cut),)
        notes.append("sink cut-out is a placeholder rectangle: replace with the chosen sink's template")
    panel = next(p for p in assembly.panels if p.stable_id == PANEL)
    frame = PanelFrame((0.0, 0.0, 0.0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
    return {PANEL: PanelProfile(PANEL, "Worktop", panel.material_ref, t, outline, features, 0,
                                tuple(notes), frame)}, MERGED
