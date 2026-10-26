"""ADR-0003 stopped dados and back rabbets: no joint visible at the front, tongues inside housings."""
import os
import tempfile
import unittest

from vandesign.arrangement import MODULES, Instance, _canonical, build_arrangement, tab_slot_parts
from vandesign.manufacturing.carcass import (TabSlotJoinery, _features_apart, cabinet_tab_slot_profiles,
                                             cabinet_tab_slot_width_bindings)
from vandesign.manufacturing.dxf import export_profiles, loop_areas, pocket_layer, read_dxf
from vandesign.manufacturing.placement import arrangement_profiles, arrangement_width_bindings
from vandesign.manufacturing.profile import (PanelProfile, Pocket, ProfileError, contains_world_point,
                                             polygon_loop, rect_vertices)

CAB = {"schema_version": "0.2", "module": "cabinet@1", "variant": "base", "profile_version": 1,
       "parameters": {"width_mm": 1100, "ply_mm": 17.6}}
JOINERY = {"sheet": {"name": "birch", "nominal_mm": 18, "measured_mm": 17.6}, "clearance_mm": 0.2,
           "tabs_per_edge": 2, "tab_width_mm": None, "tool_diameter_mm": 6, "blind_slot_depth_mm": 12,
           "dado_stop_mm": 20, "back_rabbet_mm": 8}
T, W, H, FRONT = 17.6, 1100.0, 850.0, 17.6        # ply, width, height, carcass front (behind the doors)


def spec(**joinery):
    optional = ("blind_slot_depth_mm", "dado_stop_mm", "back_rabbet_mm")     # None = omit the key
    return {"cabinet": CAB, "joinery": {k: v for k, v in dict(JOINERY, **joinery).items()
                                        if v is not None or k not in optional}}


def built(**joinery):
    s = spec(**joinery)
    _, j = tab_slot_parts(s)
    asm = MODULES["cabinet_tab_slot"][0](_canonical(s))
    profiles, _ = cabinet_tab_slot_profiles(asm, j)
    env = asm.parameters.resolve()
    return asm, j, {p.panel_id: p for p in profiles}, env


class Geometry(unittest.TestCase):
    def test_dado_is_hidden_at_the_front_and_the_shelf_still_sits_in_it(self):
        asm, _, p, env = built()
        z = env["Cab_Shelf1_Z"] + T / 2                       # mid shelf thickness
        left, shelf = p["panel.left.001"], p["panel.shelf.001"]
        groove_x = T - env["Cab_Dado_Depth"] / 2             # inside the groove depth, left side
        self.assertIs(contains_world_point(left, (groove_x, FRONT + 5, z)), True)     # stopped: front intact
        self.assertIs(contains_world_point(left, (groove_x, FRONT + 100, z)), False)  # groove behind the stop
        self.assertIs(contains_world_point(shelf, (groove_x, FRONT + 5, z)), False)   # notched shelf corner
        self.assertIs(contains_world_point(shelf, (groove_x, FRONT + 100, z)), True)  # tongue in the groove
        self.assertIs(contains_world_point(shelf, (W / 2, FRONT + 1, z)), True)       # full-width front edge

    def test_back_sits_in_rabbets_open_only_to_the_rear(self):
        asm, _, p, env = built()
        back_y = FRONT + env["Cab_Depth"] - env["Cab_Back"] / 2
        left, back = p["panel.left.001"], p["panel.back.001"]
        x = T - 4                                             # 4 mm into the left side
        self.assertIs(contains_world_point(left, (x, back_y, H / 2)), False)          # rabbet
        self.assertIs(contains_world_point(back, (x, back_y, H / 2)), True)           # back tongue fills it
        self.assertIs(contains_world_point(left, (x, back_y, T / 2)), True)           # stopped at the bottom
        self.assertIs(contains_world_point(left, (x, back_y, H - T / 2)), True)       # and at the top
        self.assertIs(contains_world_point(left, (1.0, back_y, H / 2)), True)         # outer face intact
        rabbet = [f for f in left.features if isinstance(f, Pocket) and abs(f.depth - 8) < 1e-9]
        self.assertEqual(len(rabbet), 1)

    def test_no_machined_features_overlap_and_dxf_has_the_new_pockets(self):
        for blind in (12, None):
            _, _, p, _ = built(blind_slot_depth_mm=blind)
            for profile in p.values():
                _features_apart(profile)
        _, _, p, _ = built()
        with tempfile.TemporaryDirectory() as tmp:
            export_profiles(tuple(p.values()), tmp)
            with open(os.path.join(tmp, "panel.left.001.dxf"), encoding="ascii") as fh:
                entities = read_dxf(fh.read())
        self.assertEqual(len(loop_areas(entities, pocket_layer("top", 8.0))), 1)
        self.assertEqual(len(loop_areas(entities, pocket_layer("top", 6.0))), 1)

    def test_overlapping_features_are_refused(self):
        a = Pocket(polygon_loop(rect_vertices(10, 10, 60, 40), waste_inside=True), 6.0, "top")
        b = Pocket(polygon_loop(rect_vertices(50, 20, 90, 50), waste_inside=True), 8.0, "top")
        outline = polygon_loop(rect_vertices(0, 0, 200, 100), waste_inside=False)
        with self.assertRaisesRegex(ProfileError, "overlap"):
            _features_apart(PanelProfile("p", "p", "ply", 17.6, outline, (a, b)))

    def test_options_are_independent_and_off_by_default(self):
        _, _, plain, _ = built(dado_stop_mm=None, back_rabbet_mm=None)
        self.assertEqual(len(plain["panel.shelf.001"].outline.segments), 4)          # untouched rectangle
        _, _, stop_only, _ = built(back_rabbet_mm=None)
        _, _, rabbet_only, _ = built(dado_stop_mm=None)
        self.assertGreater(len(stop_only["panel.shelf.001"].outline.segments), 4)
        self.assertGreater(len(rabbet_only["panel.shelf.001"].outline.segments), 4)  # rear notches only
        self.assertEqual(stop_only["panel.back.001"].outline.bounds, plain["panel.back.001"].outline.bounds)


class EditableAndPlaced(unittest.TestCase):
    def test_width_bindings_still_prove(self):
        asm, j, _, _ = built()
        self.assertEqual(len(cabinet_tab_slot_width_bindings(asm, j)), 8)
        for k in range(4):
            arr = build_arrangement((Instance("k", "cabinet_tab_slot", "K", spec(), (1000, 1000, 0), k),))
            self.assertEqual(len(arrangement_profiles(arr, tool_diameter=6)[0]), 8)
            self.assertEqual(len(arrangement_width_bindings(arr, "k")), 8)

    def test_refusals(self):
        for bad in (dict(back_rabbet_mm=14), dict(dado_stop_mm=600)):
            with self.assertRaises(ProfileError, msg=repr(bad)):
                built(**bad)
        for bad in (dict(dado_stop_mm=0), dict(dado_stop_mm="20"), dict(back_rabbet_mm=0.1),
                    dict(back_rabbet_mm=float("inf")), dict(stopped=True)):
            with self.assertRaises(ProfileError, msg=repr(bad)):
                TabSlotJoinery.from_json(dict(JOINERY, **bad))


if __name__ == "__main__":
    unittest.main()
