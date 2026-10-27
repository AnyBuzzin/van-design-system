"""ADR-0003 blind tab-and-slot: clean outer faces, exact end gap and skin, zero overlap."""
import os
import tempfile
import unittest

from vandesign.arrangement import MODULES, Instance, _canonical, build_arrangement, tab_slot_parts
from vandesign.core.geometry import Box
from vandesign.manufacturing.carcass import TabSlotJoinery, cabinet_tab_slot_profiles, cabinet_tab_slot_width_bindings
from vandesign.manufacturing.dxf import export_profiles, loop_areas, pocket_layer, read_dxf
from vandesign.manufacturing.joints import MIN_SKIN_MM, TabSlot, apply_tab_slot
from vandesign.manufacturing.placement import arrangement_profiles, arrangement_width_bindings, place_point
from vandesign.manufacturing.profile import Pocket, ProfileError, ThroughCut, contains_world_point

CAB = {"schema_version": "0.2", "module": "cabinet@1", "variant": "base", "profile_version": 1,
       "parameters": {"width_mm": 1100, "ply_mm": 17.6}}
JOINERY = {"sheet": {"name": "birch", "nominal_mm": 18, "measured_mm": 17.6}, "clearance_mm": 0.2,
           "tabs_per_edge": 2, "tab_width_mm": None, "tool_diameter_mm": 6, "blind_slot_depth_mm": 12}
SIDES = ("panel.left.001", "panel.right.001")


def spec(**joinery):
    return {"cabinet": CAB, "joinery": dict(JOINERY, **joinery)}


def module(s):
    _, joinery = tab_slot_parts(s)
    return MODULES["cabinet_tab_slot"][0](_canonical(s)), joinery


class Joint(unittest.TestCase):
    # Horizontal 17.6 mm inserter resting on a vertical 17.6 mm receiver's inner (+x) face.
    receiver = Box((0.0, 0.0, 0.0), (17.6, 500.0, 600.0))
    inserter = Box((17.6, 0.0, 200.0), (800.0, 500.0, 217.6))

    def joint(self, engagement, blind=True):
        return TabSlot("in", "rx", "-x", ((100.0, 120.0), (300.0, 120.0)), engagement, 0.2, blind)

    def test_blind_slot_is_a_pocket_with_exact_end_gap_and_skin(self):
        r = apply_tab_slot(self.joint(11.9), self.inserter, self.receiver)
        for tab, slot in zip(r.tabs, r.slots):
            self.assertAlmostEqual(slot.hi[0], 17.6)                   # open on the inner face only
            self.assertAlmostEqual(slot.lo[0], 17.6 - 12.0)
            self.assertAlmostEqual(tab.lo[0] - slot.lo[0], 0.1)          # end gap = clearance / 2
            self.assertGreater(slot.lo[0], self.receiver.lo[0])           # outer face untouched
        self.assertTrue(r.proof["blind"])
        self.assertAlmostEqual(r.proof["min_skin_mm"], 5.6)
        self.assertEqual(r.proof["assembled_overlap_mm3"], 0.0)

    def test_through_stays_the_default(self):
        r = apply_tab_slot(TabSlot("in", "rx", "-x", ((100.0, 120.0),), 17.6, 0.2), self.inserter, self.receiver)
        self.assertEqual((r.slots[0].lo[0], r.slots[0].hi[0]), (0.0, 17.6))
        self.assertNotIn("blind", r.proof)

    def test_thin_skin_and_bad_flags_refused(self):
        depth_limit = 17.6 - MIN_SKIN_MM - 0.1                        # engagement that leaves exactly the skin
        apply_tab_slot(self.joint(depth_limit), self.inserter, self.receiver)
        with self.assertRaisesRegex(ProfileError, "outer face"):
            apply_tab_slot(self.joint(depth_limit + 0.01), self.inserter, self.receiver)
        with self.assertRaises(ProfileError):
            TabSlot("in", "rx", "-x", ((100.0, 120.0),), 11.9, 0.2, 1)


class Cabinet(unittest.TestCase):
    def test_sides_carry_only_pockets_and_the_proofs_hold(self):
        asm, joinery = module(spec())
        profiles, results = cabinet_tab_slot_profiles(asm, joinery)
        by_id = {p.panel_id: p for p in profiles}
        for pid in SIDES:
            features = by_id[pid].features
            self.assertFalse(any(isinstance(f, ThroughCut) for f in features), pid)
            self.assertEqual({f.face for f in features}, {"top"}, pid)       # one machined (inner) face
            self.assertEqual(sorted(round(f.depth, 6) for f in features if isinstance(f, Pocket))[-4:], [12.0] * 4)
        for r in results:
            self.assertEqual(r.proof["assembled_overlap_mm3"], 0.0)
            self.assertAlmostEqual(r.proof["end_gap_mm"], 0.1)
            self.assertAlmostEqual(r.proof["min_skin_mm"], 17.6 - 12.0)

    def test_outer_faces_are_clean_and_tabs_sit_in_their_pockets_for_all_turns(self):
        asm, joinery = module(spec())
        _, results = cabinet_tab_slot_profiles(asm, joinery)            # module-frame slots
        for k in range(4):
            arr = build_arrangement((Instance("k", "cabinet_tab_slot", "K", spec(), (1000, 1000, 0), k),))
            by_id = {p.panel_id: p for p in arrangement_profiles(arr, tool_diameter=6)[0]}
            for r in results:
                side = by_id["k." + r.joint.receiver]
                outer_face = 0.0 if r.joint.direction == "-x" else 1100.0
                inward = 1.0 if r.joint.direction == "-x" else -1.0
                for slot in r.slots:
                    cy, cz = (slot.lo[1] + slot.hi[1]) / 2, (slot.lo[2] + slot.hi[2]) / 2
                    # 0.5 mm in from the outer face: skin. 16.6 mm in: inside the pocket.
                    for depth, material in ((0.5, True), (16.6, False)):
                        p = place_point((outer_face + inward * depth, cy, cz), k, 1100.0, 17.6 + 550.0,
                                        (1000.0, 1000.0, 0.0))
                        self.assertIs(contains_world_point(side, p), material, (k, side.panel_id, depth))

    def test_dxf_pack_has_the_blind_pockets(self):
        asm, joinery = module(spec())
        profiles, _ = cabinet_tab_slot_profiles(asm, joinery)
        with tempfile.TemporaryDirectory() as tmp:
            export_profiles(profiles, tmp)
            with open(os.path.join(tmp, "panel.left.001.dxf"), encoding="ascii") as fh:
                entities = read_dxf(fh.read())
            self.assertEqual(len(loop_areas(entities, pocket_layer("top", 12.0))), 4)

    def test_width_bindings_still_prove_with_blind_slots(self):
        asm, joinery = module(spec())
        self.assertEqual(len(cabinet_tab_slot_width_bindings(asm, joinery)), 8)
        arr = build_arrangement((Instance("k", "cabinet_tab_slot", "K", spec(), (1000, 1000, 0), 3),))
        self.assertEqual(len(arrangement_width_bindings(arr, "k")), 8)


class Spec(unittest.TestCase):
    def test_optional_key_and_refusals(self):
        self.assertIsNone(TabSlotJoinery.from_json({k: v for k, v in JOINERY.items()
                                                    if k != "blind_slot_depth_mm"}).blind_slot_depth_mm)
        self.assertEqual(TabSlotJoinery.from_json(JOINERY).blind_slot_depth_mm, 12)
        for bad in (0.1, 0, -3, "12", float("nan")):
            with self.assertRaises(ProfileError, msg=repr(bad)):
                TabSlotJoinery.from_json(dict(JOINERY, blind_slot_depth_mm=bad))
        with self.assertRaises(ProfileError):
            TabSlotJoinery.from_json(dict(JOINERY, slot_depth=12))
        asm, joinery = module(spec(blind_slot_depth_mm=14))           # 3.6 mm skin
        with self.assertRaisesRegex(ProfileError, "outer face"):
            cabinet_tab_slot_profiles(asm, joinery)


if __name__ == "__main__":
    unittest.main()
