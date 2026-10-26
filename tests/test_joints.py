"""Reusable tab-and-slot joints: geometry, proofs, measured sheets, machinability."""
import math
import unittest

from vandesign.core.geometry import Box
from vandesign.core.tab_slot import RECEIVER, UPRIGHT
from vandesign.manufacturing.assembly import assembly_profiles
from vandesign.manufacturing.catalog import tab_slot_carcass_profiles, tab_slot_profiles
from vandesign.manufacturing.dxf import dxf_text, loop_areas, read_dxf
from vandesign.manufacturing.joints import (Sheet, TabSlot, apply_joints, apply_tab_slot,
                                            unrelieved_inside_corners)
from vandesign.manufacturing.profile import ProfileError
from vandesign.modules.cabinet import build_cabinet
from vandesign.schemas.cabinet_spec import CabinetSpec

K = math.pi / 2 - 1          # relief area per corner, in units of r^2
RECV = Box((0, 0, 0), (200, 120, 18))
UP = Box((40, 51, 18), (160, 69, 118))       # resting on the receiver


def joint(**over):
    fields = dict(inserter="up", receiver="recv", direction="-z", tabs=((30, 60),),
                  engagement_mm=18, clearance_mm=0.5)
    fields.update(over)
    return TabSlot(**fields)


class Materials(unittest.TestCase):
    def test_sheet_uses_supported_nominals_and_plausible_measurements(self):
        self.assertEqual(Sheet("birch", 18, 17.6).measured_mm, 17.6)
        for bad in ((18, float("nan")), (18, 19.5), (16, 16), (12, True), (18, "18")):
            with self.assertRaises(ProfileError, msg=repr(bad)):
                Sheet("x", *bad)


class TabSlotGeometry(unittest.TestCase):
    def test_single_tab_matches_e12_slot_and_mates_with_clearance(self):
        r = apply_tab_slot(joint(), UP, RECV)
        (slot,), (tab,) = r.slots, r.tabs
        self.assertEqual((slot.lo, slot.hi), ((69.75, 50.75, 0), (130.25, 69.25, 18)))
        self.assertEqual((tab.lo, tab.hi), ((70, 51, 0), (130, 69, 18)))
        self.assertAlmostEqual(slot.size[0] - tab.size[0], 0.5)
        self.assertAlmostEqual(slot.size[1] - tab.size[1], 0.5)
        self.assertEqual(r.inserter_box, Box((40, 51, 0), (160, 69, 118)))
        self.assertEqual(sum(1 for pid, _ in r.cuts if pid == "up"), 2)      # two notches
        self.assertEqual(r.proof["assembled_overlap_mm3"], 0.0)
        self.assertEqual(r.proof["clearance_per_face_mm"], 0.25)

    def test_invalid_joints_refused(self):
        for over in (dict(direction="z"), dict(direction="-w"), dict(engagement_mm=0),
                     dict(clearance_mm=-0.1), dict(clearance_mm=6), dict(tabs=()),
                     dict(tabs=((0, 60), (50, 20))), dict(tabs=((0, 0),)), dict(receiver="up")):
            with self.assertRaises(ProfileError, msg=repr(over)):
                joint(**over)
        cases = (
            (joint(), Box((40, 51, 20), (160, 69, 118)), RECV),        # not resting on the receiver
            (joint(direction="-y"), UP, RECV),                         # not through receiver thickness
            (joint(engagement_mm=18.5), UP, RECV),                     # deeper than the receiver
            (joint(tabs=((100, 30),)), UP, RECV),                      # beyond the inserter
            (joint(), Box((150, 51, 18), (270, 69, 118)), RECV),       # tab outside the receiver
        )
        for j, ins, rec in cases:
            with self.assertRaises(ProfileError):
                apply_tab_slot(j, ins, rec)

    def test_e12_coupon_regenerated_by_the_generator_is_machinable(self):
        profs = {p.panel_id: p for p in tab_slot_profiles()}
        for p in profs.values():
            self.assertEqual(unrelieved_inside_corners(p, 6), [], p.panel_id)
        self.assertEqual(profs[UPRIGHT].reliefs, 2)                    # both tab roots
        self.assertEqual(profs[RECEIVER].reliefs, 4)                   # all slot corners


class Carcass(unittest.TestCase):
    def setUp(self):
        self.sheet = Sheet("birch ply", 18, 17.6)
        self.profiles, self.results = tab_slot_carcass_profiles(self.sheet, tool_diameter=6)
        self.by_id = {p.panel_id: p for p in self.profiles}

    def test_measured_thickness_drives_every_carcass_panel(self):
        for pid in ("panel.left.001", "panel.right.001", "panel.bottom.001", "panel.top.001",
                    "panel.shelf.001", "panel.door.001"):
            self.assertAlmostEqual(self.by_id[pid].thickness, 17.6, places=9, msg=pid)
            self.assertIn("measured 17.60 mm (nominal 18 mm)", self.by_id[pid].notes[-1])
        self.assertEqual(self.by_id["panel.back.001"].thickness, 6.0)  # separate back sheet
        for r in self.results:
            self.assertEqual(r.proof["engagement_mm"], 17.6)           # flush through the side

    def test_every_part_is_machinable_and_tabs_mate_with_clearance(self):
        for p in self.profiles:
            self.assertEqual(unrelieved_inside_corners(p, 6), [], p.panel_id)
        self.assertEqual(len(self.results), 4)
        for r in self.results:
            self.assertEqual(r.proof["assembled_overlap_mm3"], 0.0)
            for tab, slot in zip(r.tabs, r.slots):
                self.assertAlmostEqual(slot.size[1] - tab.size[1], 0.2, places=9)   # along the depth
                self.assertAlmostEqual(slot.size[2] - tab.size[2], 0.2, places=9)   # across the thickness
        self.assertGreater(len(unrelieved_inside_corners(
            next(p for p in self._no_relief() if p.panel_id == "panel.bottom.001"), 6)), 0)

    def _no_relief(self):
        asm = build_cabinet(CabinetSpec())
        values = {"Cab_Ply": 17.6}
        env = asm.parameters.resolve(values)
        boxes = {p.stable_id: p.box.resolve(env) for p in asm.panels}
        overrides, cuts, _ = apply_joints([j.joint for j in self.results], boxes)
        return assembly_profiles(asm, values, relief=False, extra_cuts=cuts, box_overrides=overrides)

    def test_volumes_account_for_tabs_slots_grooves_and_relief(self):
        asm = build_cabinet(CabinetSpec())
        env = asm.parameters.resolve({"Cab_Ply": 17.6})
        box = {p.stable_id: p.box.resolve(env) for p in asm.panels}
        r2 = 9.0
        t = 17.6
        bottom_tabs = sum(tab.volume for r in self.results if r.joint.inserter == "panel.bottom.001"
                          for tab in r.tabs)
        self.assertAlmostEqual(self.by_id["panel.bottom.001"].volume_mm3,
                               box["panel.bottom.001"].volume + bottom_tabs - 8 * r2 * K * t, places=4)
        left = box["panel.left.001"]
        slots = sum(left.overlap_volume(s) for r in self.results if r.joint.receiver == "panel.left.001"
                    for s in r.slots)
        dado = sum(left.overlap_volume(op.cut.resolve(env)) for op in asm.operations
                   if op.target_panel_id == "panel.left.001")
        depth = env["Cab_Dado_Depth"]
        self.assertAlmostEqual(self.by_id["panel.left.001"].volume_mm3,
                               left.volume - dado - slots - 2 * r2 * K * depth - 8 * r2 * K * t, places=4)

    def test_carcass_round_trips_through_dxf(self):
        for p in self.profiles:
            got = loop_areas(read_dxf(dxf_text(p)), "OUTLINE")
            self.assertEqual(len(got), 1)
            self.assertAlmostEqual(got[0], p.outline.area, delta=1e-6 * p.outline.area)

    def test_carcass_refusals(self):
        with self.assertRaises(ProfileError):
            tab_slot_carcass_profiles("18mm", tool_diameter=6)
        with self.assertRaises(ProfileError):
            tab_slot_carcass_profiles(self.sheet, tool_diameter=6, tabs_per_edge=0)
        with self.assertRaises(ProfileError):                           # tabs collide at this width
            tab_slot_carcass_profiles(self.sheet, tool_diameter=6, tabs_per_edge=2, tab_width_mm=400)


if __name__ == "__main__":
    unittest.main()
