"""ADR-0003 blind corner: fixed blind panel, hidden screw joint between the two L carcasses."""
import copy
import unittest

from vandesign.arrangement import MODULES, ArrangementError, Instance, _canonical, build_arrangement, tab_slot_parts
from vandesign.manufacturing.carcass import cabinet_tab_slot_profiles, cabinet_tab_slot_width_bindings
from vandesign.manufacturing.placement import arrangement_profiles
from vandesign.manufacturing.profile import Hole, ProfileError, world_box

T = 17.6
FRONT = 550.0                # cabinet A's inset front face, world y (footprint depth 567.6 minus T)
JOINERY = {"sheet": {"name": "birch", "nominal_mm": 18, "measured_mm": T}, "clearance_mm": 0.2,
           "tabs_per_edge": 2, "tab_width_mm": None, "tool_diameter_mm": 6, "blind_slot_depth_mm": 12,
           "dado_stop_mm": 20, "back_rabbet_mm": 8}
BLIND = {"style": "inset", "blind": {"side": "right", "width_mm": FRONT + 50}}
BUTT = {"side": "left"}
WORKTOP = {"schema_version": "vandesign.worktop-l/1", "material_ref": "ply_main",
           "parameters": {"leg_a_length_mm": 1200, "leg_a_depth_mm": FRONT + 20, "leg_b_length_mm": FRONT + 800,
                          "leg_b_depth_mm": FRONT + 20, "thickness_mm": T, "front_corner_radius_mm": 10,
                          "inside_corner_radius_mm": 25},
           "sink": {"leg": "b", "centre_x_mm": 300, "centre_y_mm": FRONT + 400, "width_mm": 340,
                    "length_mm": 400, "corner_radius_mm": 15, "margin_mm": 50}}


def cab(width, **joinery):
    return {"cabinet": {"schema_version": "0.2", "module": "cabinet@1", "variant": "base", "profile_version": 1,
                        "parameters": {"width_mm": width, "ply_mm": T}},
            "joinery": dict(JOINERY, **joinery)}


A = cab(1200, fronts=BLIND, top={})
# B's single door hinges away from the corner, so it swings clear of A's blind panel.
B = cab(800, fronts={"style": "inset", "hinge_sides": ["right"]}, top={"sink_rail_mm": 80}, corner_fixings=BUTT)
B["cabinet"]["parameters"]["door_count"] = 1


def kitchen(a=A, b=B, b_y=FRONT, worktop=True):
    """Walls at x = 0 (behind B) and y = 0 (behind A). A runs into the corner; B butts A's blind panel."""
    items = [Instance("kitchen.a", "cabinet_tab_slot", "KA", a, (0, 0, 0), 2),
             Instance("kitchen.b", "cabinet_tab_slot", "KB", b, (0, b_y, 0), 1)]
    if worktop:
        items.append(Instance("kitchen.top", "worktop_l", "WT", WORKTOP, (0, 0, 850), 0))
    return build_arrangement(tuple(items))


def by_id(arr):
    return {p.panel_id: p for p in arrangement_profiles(arr, tool_diameter=6)[0]}


def world_holes(p, face=None):
    return sorted(tuple(round(v, 6) for v in p.frame.to_world(h.center[0], h.center[1],
                                                                   0.0 if h.face == "bottom" else p.thickness))
                  for h in p.features if isinstance(h, Hole) and (face is None or h.face == face))


class Corner(unittest.TestCase):
    def test_the_two_carcasses_are_joined_by_hidden_screws_that_line_up(self):
        p = by_id(kitchen())
        blind = p["kitchen.a.panel.door.002"]                      # module right = the corner end here
        side = p["kitchen.b.panel.left.001"]
        pilots, holes = world_holes(blind, "bottom"), world_holes(side, "bottom")
        self.assertEqual(len(pilots), 4)
        self.assertEqual(pilots, holes)
        self.assertEqual({round(x, 6) for x, _, _ in pilots}, {150.0, 400.0})        # from the corner wall
        self.assertEqual({round(z, 6) for _, _, z in pilots}, {200.0, 600.0})        # up from the floor
        self.assertEqual({round(y, 6) for _, y, _ in pilots}, {FRONT})               # A's front = B's side face
        self.assertFalse(world_holes(blind, "top"))                                    # no hinge cups: fixed

    def test_blind_panel_and_doors(self):
        p = by_id(kitchen())
        (blo, bhi), (dlo, dhi) = world_box(p["kitchen.a.panel.door.002"]), world_box(p["kitchen.a.panel.door.001"])
        self.assertAlmostEqual(blo[0], T + 2.5)                                       # from the opening edge
        self.assertAlmostEqual(bhi[0], FRONT + 50 - 1.25)                             # blind width, half gap
        self.assertAlmostEqual(dlo[0] - bhi[0], 2.5)
        self.assertAlmostEqual(1200 - T - 2.5, dhi[0])
        cups = world_holes(p["kitchen.a.panel.door.001"], "top")
        self.assertTrue(all(abs(x - (1200 - T - 2.5 - 22.5)) < 1e-6 for x, _, _ in cups))   # hinged away

    def test_box_model_shows_the_inset_fronts(self):
        arr = kitchen(worktop=False)
        env = arr.assembly.parameters.resolve()
        p = by_id(arr)
        for pid in ("kitchen.a.panel.door.001", "kitchen.a.panel.door.002", "kitchen.b.panel.door.001"):
            box = next(q for q in arr.assembly.panels if q.stable_id == pid).box.resolve(env)
            lo, hi = world_box(p[pid])
            self.assertTrue(all(abs(a - b) < 1e-6 for a, b in zip(lo + hi, box.lo + box.hi)), pid)

    def test_misaligned_or_unpartnered_fixings_are_refused(self):
        b = copy.deepcopy(B)
        b["joinery"]["corner_fixings"] = {"side": "left", "offsets_mm": [160, 400]}
        with self.assertRaisesRegex(ProfileError, "do not line up"):
            by_id(kitchen(b=b))
        b = copy.deepcopy(B)
        del b["joinery"]["corner_fixings"]
        with self.assertRaisesRegex(ProfileError, "do not line up"):
            by_id(kitchen(b=b))

    def test_refusals(self):
        def blind(**kw):
            a = copy.deepcopy(A)
            a["joinery"]["fronts"].update(kw)
            return a
        bad = [blind(hinge_sides=["right"]),                         # hinge against the blind panel
               blind(hinge_sides=["left", "left"]),                  # one entry per hinged door
               blind(blind={"side": "right", "width_mm": 1150}),     # leaves no room for a door
               blind(blind={"side": "middle", "width_mm": 600})]
        for a in bad:
            with self.assertRaises((ProfileError, ArrangementError, ValueError)):
                by_id(kitchen(a=a))
        two = cab(800, fronts={"style": "inset", "hinge_sides": ["right", "right"]}, top={"sink_rail_mm": 80},
                  corner_fixings=BUTT)                     # B's corner door cannot hinge on a door edge
        with self.assertRaisesRegex(ProfileError, "hinge against a carcass side"):
            by_id(kitchen(b=two))
        one_door = cab(600, fronts=BLIND)
        one_door["cabinet"]["parameters"]["door_count"] = 1
        with self.assertRaises((ProfileError, ArrangementError, ValueError)):
            kitchen(a=one_door)

    def test_blind_cabinet_stays_natively_width_editable(self):
        s = cab(1100, fronts={"style": "inset", "blind": {"side": "left", "width_mm": 600}})
        _, joinery = tab_slot_parts(s)
        asm = MODULES["cabinet_tab_slot"][0](_canonical(s))
        bindings = cabinet_tab_slot_width_bindings(asm, joinery)
        for w in (1000.0, 1050.0):
            env = asm.parameters.resolve({"Cab_Width": w})
            for prof in cabinet_tab_slot_profiles(asm, joinery, {"Cab_Width": w})[0]:
                self.assertIsNone(bindings[prof.panel_id].mismatch(prof, env), (w, prof.panel_id))


if __name__ == "__main__":
    unittest.main()
