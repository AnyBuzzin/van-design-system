"""The complete owner L kitchen (#100) in the reference Crafter: fit, joinery, fixings, review pack."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

from vandesign.arrangement import ArrangementError
from vandesign.arrangement_job import plan_request
from vandesign.layout_report import offline_plan
from vandesign.manufacturing.placement import arrangement_profiles
from vandesign.manufacturing.profile import Hole, Pocket, ProfileError, ThroughCut, world_box

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
EXAMPLE = os.path.join(ROOT, "examples", "crafter_kitchen_l.json")


def example():
    with open(EXAMPLE, encoding="utf-8") as fh:
        return json.load(fh)


def profiles(request=None, values=None):
    plan = offline_plan(request or example())
    return {p.panel_id: p for p in arrangement_profiles(plan.arrangement, values, tool_diameter=6)[0]}


def holes(p, face):
    return [h for h in p.features if isinstance(h, Hole) and h.face == face]


class Kitchen(unittest.TestCase):
    def test_fits_the_crafter_clear_of_the_sliding_door_and_arch(self):
        plan = offline_plan(example())
        self.assertEqual(plan.arrangement.fit["outcome"], "PASS")
        moved = example()
        moved["arrangement"]["instances"][0]["position_mm"][0] = 590       # into the sliding-door zone
        with self.assertRaises(ArrangementError):
            offline_plan(moved)
        with self.assertRaisesRegex(ArrangementError, "tab-and-slot base cabinet only"):
            plan_request(example())                                        # live: not yet

    def test_every_joint_and_fixing_is_hidden(self):
        p = profiles()
        self.assertEqual(len(p), 16)
        for pid in ("kitchen.bulkhead.panel.left.001", "kitchen.side.panel.right.001"):
            self.assertFalse(any(isinstance(f, ThroughCut) for f in p[pid].features), pid)   # blind slots
        blind = p["kitchen.bulkhead.panel.door.002"]
        self.assertEqual((len(holes(blind, "bottom")), len(holes(blind, "top"))), (4, 0))     # pilots, no cups
        side = p["kitchen.side.panel.left.001"]
        self.assertEqual(len([h for h in side.features if isinstance(h, Hole) and h.depth is None]), 4)
        top = p["kitchen.worktop.panel.worktop.001"]
        self.assertEqual(len(holes(top, "bottom")), 12)                     # under both carcass tops
        self.assertEqual(sum(isinstance(f, ThroughCut) for f in top.features), 1)            # the sink
        self.assertEqual(sum(isinstance(f, ThroughCut) for f in p["kitchen.side.panel.top.001"].features), 1)
        self.assertTrue(any(isinstance(f, Pocket) and abs(f.depth - 8) < 1e-9 for f in side.features))  # rabbet

    def test_worktop_sits_on_both_carcasses_against_both_walls(self):
        p = profiles()
        lo, hi = world_box(p["kitchen.worktop.panel.worktop.001"])
        self.assertAlmostEqual(lo[2], 855.0)
        self.assertAlmostEqual(hi[0], 1796 - 5)                             # right wall, 5 mm tolerance
        self.assertAlmostEqual(hi[1], 4570 - 5)                             # cab bulkhead
        for cab in ("kitchen.bulkhead", "kitchen.side"):
            self.assertAlmostEqual(world_box(p[cab + ".panel.top.001"])[1][2], lo[2])

    def test_edits_that_break_the_corner_are_refused_and_others_pass(self):
        profiles(values={"WT_WT_Sink_Y": 900})                              # move the sink along the leg
        with self.assertRaisesRegex(ProfileError, "do not line up"):
            profiles(values={"KB_Cab_Width": 700})                          # B no longer meets the blind panel

    def test_review_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "kitchen")
            run = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "design_layout.py"), EXAMPLE,
                                  "--out", out], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            with open(os.path.join(out, "summary.json"), encoding="utf-8") as fh:
                summary = json.load(fh)
            self.assertEqual(summary["fit"]["outcome"], "PASS")
            self.assertEqual(summary["panels"], 16)
            self.assertEqual(len([f for f in os.listdir(os.path.join(out, "dxf")) if f.endswith(".dxf")]), 16)
            for view in ("top", "front", "side"):
                self.assertTrue(os.path.getsize(os.path.join(out, view + ".svg")) > 1000)


if __name__ == "__main__":
    unittest.main()
