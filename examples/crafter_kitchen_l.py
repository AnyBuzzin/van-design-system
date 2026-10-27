"""Regenerates examples/crafter_kitchen_l.json (run from the repo root).

The owner's L kitchen (#100) in the reference Crafter: every position is derived
from the envelope, tolerance and cabinet sizes below, so edit those and rerun.
Uses the envelope of examples/crafter_interior.json (ASSUMED, UNMEASURED).
"""
import json

T = 17.6
TOL = 5.0
W_ENV, L_ENV = 1832 - 36, 4606 - 36           # finished interior (lining 18 each side)
RIGHT, FRONT = W_ENV - TOL, L_ENV - TOL       # the two kitchen walls: right side wall, cab bulkhead
Z = TOL                                       # cabinets stand on the finished floor + tolerance
DEPTH, HEIGHT = 550.0, 850.0                  # carcass depth (behind the inset fronts) and height
FOOT = T + DEPTH                              # cabinet footprint depth
A_W, B_W = 1150.0, 800.0                      # bulkhead and side-wall cabinet widths
OVERHANG = 20.0

envelope = json.load(open("examples/crafter_interior.json", encoding="utf-8"))["envelope"]

joinery = {"sheet": {"name": "birch ply", "nominal_mm": 18, "measured_mm": T}, "clearance_mm": 0.2,
           "tabs_per_edge": 2, "tab_width_mm": None, "tool_diameter_mm": 6, "blind_slot_depth_mm": 12,
           "dado_stop_mm": 20, "back_rabbet_mm": 8}


def cabinet(width, doors, **extra):
    return {"cabinet": {"schema_version": "0.2", "module": "cabinet@1", "variant": "base", "profile_version": 1,
                        "parameters": {"width_mm": width, "height_mm": HEIGHT, "depth_mm": DEPTH, "ply_mm": T,
                                       "door_count": doors}},
            "joinery": dict(joinery, **extra)}


# Cabinet A along the bulkhead, back to the bulkhead (k = 0), blind panel at the right-wall corner.
a_pos = (RIGHT - A_W, FRONT - FOOT, Z)
a_front = a_pos[1] + T                         # inset door faces (world y)
blind = {"side": "right", "width_mm": DEPTH + 50.0}
cab_a = cabinet(A_W, 2, fronts={"style": "inset", "blind": blind}, top={})
# Cabinet B along the right wall, back to the wall (k = 3), its corner side butting A's blind panel.
b_pos = (RIGHT - FOOT, a_front - B_W, Z)
b_front = b_pos[0] + T                         # inset door faces (world x)
cab_b = cabinet(B_W, 1, fronts={"style": "inset", "hinge_sides": ["right"]}, top={"sink_rail_mm": 80},
                corner_fixings={"side": "left"})
# One-piece L worktop, back edges on both walls (k = 2 puts its module corner at the world corner).
la, lb = RIGHT - a_pos[0], FRONT - b_pos[1]
da, db = FRONT - a_front + OVERHANG, RIGHT - b_front + OVERHANG
worktop = {"schema_version": "vandesign.worktop-l/1", "material_ref": "ply_main",
           "parameters": {"leg_a_length_mm": la, "leg_a_depth_mm": da, "leg_b_length_mm": lb,
                          "leg_b_depth_mm": db, "thickness_mm": T, "front_corner_radius_mm": 10,
                          "inside_corner_radius_mm": 25},
           "sink": {"leg": "b", "centre_x_mm": 300, "centre_y_mm": round(FRONT - a_front + B_W / 2, 1),
                    "width_mm": 340, "length_mm": 400, "corner_radius_mm": 15, "margin_mm": 50}}

request = {
    "arrangement": {"schema_version": "vandesign.arrangement/1", "instances": [
        dict(instance_id="kitchen.bulkhead", module="cabinet_tab_slot", param_prefix="KA", spec=cab_a,
             position_mm=[round(v, 3) for v in a_pos], quarter_turns=0),
        dict(instance_id="kitchen.side", module="cabinet_tab_slot", param_prefix="KB", spec=cab_b,
             position_mm=[round(v, 3) for v in b_pos], quarter_turns=3),
        dict(instance_id="kitchen.worktop", module="worktop_l", param_prefix="WT", spec=worktop,
             position_mm=[round(RIGHT - la, 3), round(FRONT - lb, 3), Z + HEIGHT], quarter_turns=2)]},
    "envelope": envelope, "edits": [], "tool_diameter_mm": 6}
with open("examples/crafter_kitchen_l.json", "w", encoding="utf-8") as fh:
    json.dump(request, fh, indent=2)
    fh.write("\n")
print("A", a_pos, "B", b_pos, "worktop", (la, da, lb, db))
