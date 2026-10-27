"""ADR-0003 inset doors: equal gaps, flush fronts, set-back shelves and hidden hardware bores."""
from dataclasses import replace
import os
import tempfile
import unittest

from vandesign.arrangement import MODULES, Instance, _canonical, build_arrangement, tab_slot_parts
from vandesign.core.expr import Mm
from vandesign.manufacturing.carcass import (TabSlotJoinery, _features_apart, cabinet_tab_slot_profiles,
                                             cabinet_tab_slot_width_bindings)
from vandesign.manufacturing.dxf import export_profiles, read_dxf
from vandesign.manufacturing.fronts import InsetFronts, hinge_count
from vandesign.manufacturing.placement import arrangement_profiles, arrangement_width_bindings
from vandesign.manufacturing.profile import Hole, ProfileError, world_box

CAB = {"schema_version": "0.2", "module": "cabinet@1", "variant": "base", "profile_version": 1,
       "parameters": {"width_mm": 1100, "ply_mm": 17.6}}
JOINERY = {"sheet": {"name": "birch", "nominal_mm": 18, "measured_mm": 17.6}, "clearance_mm": 0.2,
           "tabs_per_edge": 2, "tab_width_mm": None, "tool_diameter_mm": 6, "blind_slot_depth_mm": 12,
           "dado_stop_mm": 20, "back_rabbet_mm": 8, "fronts": {"style": "inset"}}
T, GAP = 17.6, 2.5


def spec(variant="base", width=1100, **joinery):
    return {"cabinet": dict(CAB, variant=variant, parameters={"width_mm": width, "ply_mm": T}),
            "joinery": dict(JOINERY, **joinery)}


def built(**kw):
    s = spec(**kw)
    _, j = tab_slot_parts(s)
    asm = MODULES["cabinet_tab_slot"][0](_canonical(s))
    profiles, _ = cabinet_tab_slot_profiles(asm, j)
    return asm, j, {p.panel_id: p for p in profiles}


def holes(profile):
    """World centres (on the bored face) of a profile's holes, with diameter and depth."""
    out = []
    for h in profile.features:
        if isinstance(h, Hole):
            c = profile.thickness if h.face == "top" else 0.0
            out.append((profile.frame.to_world(h.center[0], h.center[1], c), h.diameter, h.depth))
    return out


class Doors(unittest.TestCase):
    def test_doors_sit_flush_inside_the_opening_with_equal_gaps(self):
        _, _, p = built()
        box = {pid: world_box(prof) for pid, prof in p.items()}
        (l_lo, l_hi), (r_lo, r_hi) = box["panel.left.001"], box["panel.right.001"]
        (d1_lo, d1_hi), (d2_lo, d2_hi) = box["panel.door.001"], box["panel.door.002"]
        self.assertAlmostEqual(d1_lo[0] - T, GAP)                         # side face to door
        self.assertAlmostEqual(d2_lo[0] - d1_hi[0], GAP)                  # between doors
        self.assertAlmostEqual(1100 - T - d2_hi[0], GAP)
        self.assertAlmostEqual(d1_lo[2] - T, GAP)                         # bottom panel to door
        self.assertAlmostEqual(850 - T - d1_hi[2], GAP)                   # door to top panel
        self.assertAlmostEqual(d1_lo[1], l_lo[1])                         # flush with the carcass front
        self.assertAlmostEqual(d1_hi[0] - d1_lo[0], d2_hi[0] - d2_lo[0])  # equal doors

    def test_no_panel_interferes_with_a_door_and_shelves_clear_the_latch_space(self):
        _, j, p = built()
        box = {pid: world_box(prof) for pid, prof in p.items()}
        for door in ("panel.door.001", "panel.door.002"):
            (a_lo, a_hi) = box[door]
            for pid, (b_lo, b_hi) in box.items():
                if pid != door:
                    overlap = [min(a_hi[k], b_hi[k]) - max(a_lo[k], b_lo[k]) for k in range(3)]
                    self.assertFalse(all(o > 1e-9 for o in overlap), (door, pid))
        door_back = box["panel.door.001"][1][1]
        self.assertAlmostEqual(box["panel.shelf.001"][0][1] - door_back, j.fronts.setback_mm)

    def test_hinge_cups_plates_and_latches(self):
        _, j, p = built()
        h, latch = j.fronts.hinge, j.fronts.latch
        for door, hinge_x, side in (("panel.door.001", T + GAP, "panel.left.001"),
                                    ("panel.door.002", 1100 - T - GAP, "panel.right.001")):
            (lo, hi) = world_box(p[door])
            cups = holes(p[door])
            self.assertEqual(len(cups), hinge_count(hi[2] - lo[2]))
            inward = 1 if hinge_x < 550 else -1
            for (x, y, z), diameter, depth in cups:
                self.assertAlmostEqual(x, hinge_x + inward * h.cup_edge_mm)
                self.assertAlmostEqual(y, hi[1])                          # on the door's back face
                self.assertEqual((diameter, depth), (35.0, 12.5))
                plates = [c for c, _, _ in holes(p[side]) if abs(c[2] - z) <= 16 + 1e-6]
                self.assertEqual(sorted(round(c[2] - z, 6) for c in plates), [-16.0, 16.0])
                self.assertTrue(all(abs(c[1] - (hi[1] + h.plate_setback_mm)) < 1e-6 for c in plates))
            self.assertAlmostEqual(cups[0][0][2] - lo[2], h.end_offset_mm)
        latches = holes(p["panel.bottom.001"])
        self.assertEqual(len(latches), 4)
        door_back = world_box(p["panel.door.001"])[1][1]
        self.assertTrue(all(abs(c[1] - (door_back + latch.setback_mm)) < 1e-6 for c, _, _ in latches))
        for profile in p.values():
            _features_apart(profile)

    def test_taller_doors_get_more_hinges(self):
        self.assertEqual([hinge_count(h) for h in (809.8, 900, 901, 1600, 1601)], [2, 2, 3, 3, 4])
        _, _, p = built(variant="tall", width=800)
        lo, hi = world_box(p["panel.door.001"])
        self.assertEqual(len(holes(p["panel.door.001"])), hinge_count(hi[2] - lo[2]))
        self.assertGreater(len(holes(p["panel.door.001"])), 2)

    def test_dxf_has_the_bores(self):
        _, _, p = built()
        with tempfile.TemporaryDirectory() as tmp:
            export_profiles(tuple(p.values()), tmp)
            with open(os.path.join(tmp, "panel.door.001.dxf"), encoding="ascii") as fh:
                circles = [e for e in read_dxf(fh.read()) if e["type"] == "CIRCLE"]
        self.assertEqual(len(circles), 2)


class Editable(unittest.TestCase):
    def test_width_bindings_cover_the_hardware(self):
        asm, j, _ = built()
        bindings = cabinet_tab_slot_width_bindings(asm, j)
        door2 = bindings["panel.door.002"]
        self.assertEqual([f.kind for f in door2.features], ["hole", "hole"])
        for w in (1000.0, 1050.0, 1100.0):
            env = asm.parameters.resolve({"Cab_Width": w})
            for p in cabinet_tab_slot_profiles(asm, j, {"Cab_Width": w})[0]:
                self.assertIsNone(bindings[p.panel_id].mismatch(p, env), (w, p.panel_id))
        # A cup frozen at 1100 mm is caught at 1000 mm.
        f = door2.features[0]
        frozen = replace(door2, features=(replace(f, center=(f.center[0], Mm(f.center[1].eval(
            asm.parameters.resolve())))),) + door2.features[1:])
        p = next(p for p in cabinet_tab_slot_profiles(asm, j, {"Cab_Width": 1000})[0]
                 if p.panel_id == "panel.door.002")
        self.assertIsNotNone(frozen.mismatch(p, asm.parameters.resolve({"Cab_Width": 1000})))
        for k in range(4):
            arr = build_arrangement((Instance("k", "cabinet_tab_slot", "K", spec(), (1000, 1000, 0), k),))
            self.assertEqual(len(arrangement_profiles(arr, tool_diameter=6)[0]), 8)
            self.assertEqual(len(arrangement_width_bindings(arr, "k")), 8)

    def test_spec_defaults_overrides_and_refusals(self):
        self.assertEqual(InsetFronts.from_json({"style": "inset"}), InsetFronts())
        f = InsetFronts.from_json({"style": "inset", "gap_mm": 3, "hinge": {"cup_edge_mm": 21.5}})
        self.assertEqual((f.gap_mm, f.hinge.cup_edge_mm, f.hinge.cup_diameter_mm), (3, 21.5, 35.0))
        for bad in ({"style": "overlay"}, {"style": "inset", "gap": 2}, {"style": "inset", "gap_mm": 0},
                    {"style": "inset", "hinge": {"cup": 35}}, {"style": "inset", "latch": {"hole_mm": -1}}):
            with self.assertRaises(ProfileError, msg=repr(bad)):
                TabSlotJoinery.from_json(dict(JOINERY, fronts=bad))
        with self.assertRaisesRegex(ProfileError, "leaves less than"):
            built(fronts={"style": "inset", "hinge": {"cup_depth_mm": 14}})        # 3.6 mm behind the cup
        _, _, plain = built(fronts=None)
        self.assertFalse(any(isinstance(f, Hole) for p in plain.values() for f in p.features))


if __name__ == "__main__":
    unittest.main()
