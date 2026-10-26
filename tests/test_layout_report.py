"""Offline design layout: example Crafter interior, drawings, fit and materials, CLI pack."""
import copy
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from vandesign.arrangement import ArrangementError
from vandesign.arrangement_job import plan_request
from vandesign.layout_report import SHEET_MM, VIEWS, fit_summary, layout_svg, material_summary, offline_plan
from vandesign.manufacturing.placement import arrangement_profiles

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
EXAMPLE = os.path.join(ROOT, "examples", "crafter_interior.json")
TOOL = os.path.join(ROOT, "tools", "design_layout.py")
SVG = "{http://www.w3.org/2000/svg}"


def example():
    with open(EXAMPLE, encoding="utf-8") as fh:
        return json.load(fh)


def moved(request, instance_id, dx):
    request = copy.deepcopy(request)
    for inst in request["arrangement"]["instances"]:
        if inst["instance_id"] == instance_id:
            inst["position_mm"][0] += dx
    return request


class Example(unittest.TestCase):
    def test_example_plans_offline_with_both_sloped_walls(self):
        plan = offline_plan(example())
        self.assertEqual(plan.arrangement.fit["outcome"], "PASS")
        self.assertEqual(plan.envelope.upper_walls, ("left", "right"))
        self.assertIn("ASSUMED", plan.envelope.provenance)
        self.assertEqual([i.instance_id for i in plan.arrangement.instances],
                         ["bed.rear", "storage.under_bed", "kitchen.base", "kitchen.overhead"])

    def test_live_planning_still_refuses_profile_modules(self):
        with self.assertRaisesRegex(ArrangementError, "oriented profile Fusion builder"):
            plan_request(example())

    def test_overhead_cabinet_is_limited_by_the_right_sloped_wall(self):
        gap = fit_summary(offline_plan(example()))["kitchen.overhead"]
        self.assertLess(gap["upper_right"], gap["right"])         # the slope, not the wall, is binding
        self.assertGreaterEqual(gap["upper_right"], 0)
        with self.assertRaisesRegex(ArrangementError, "upper right wall"):
            offline_plan(moved(example(), "kitchen.overhead", 2))
        offline_plan(moved(example(), "kitchen.overhead", -2))   # away from the slope still fits

    def test_fit_summary_is_the_minimum_over_each_instance(self):
        plan = offline_plan(example())
        gaps = plan.arrangement.fit["clearance_to_inset_planes_mm"]
        summary = fit_summary(plan)
        self.assertEqual(set(summary), {i.instance_id for i in plan.arrangement.instances})
        for owner, mine in summary.items():
            for key, value in mine.items():
                expected = min(g[key] for pid, g in gaps.items() if plan.arrangement.owners[pid] == owner)
                self.assertAlmostEqual(value, expected, places=3)


class Drawings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = offline_plan(example())

    def test_every_view_is_valid_svg_with_every_instance_labelled(self):
        for view in VIEWS:
            root = ET.fromstring(layout_svg(self.plan, view))
            texts = {t.text for t in root.iter(SVG + "text")}
            for inst in self.plan.arrangement.instances:
                self.assertIn(inst.instance_id, texts, view)
            titles = {t.text for t in root.iter(SVG + "title")}
            for panel in self.plan.arrangement.assembly.panels:
                if not panel.stable_id.startswith("reference."):
                    self.assertIn(panel.stable_id, titles, view)

    def test_furniture_lies_inside_the_drawn_interior(self):
        w, length, _ = self.plan.envelope.finished_size
        size = {"top": (w, length), "front": (w, self.plan.envelope.heights[0]),
                "side": (length, self.plan.envelope.heights[0])}
        for view, (dw, dh) in size.items():
            root = ET.fromstring(layout_svg(self.plan, view))
            for rect in root.iter(SVG + "rect"):
                x, y, rw, rh = (float(rect.get(k)) for k in ("x", "y", "width", "height"))
                self.assertGreater(min(rw, rh), 0)
                self.assertTrue(-1e-9 <= x and x + rw <= dw + 1e-9 and -1e-9 <= y and y + rh <= dh + 1e-9,
                                (view, rect.find(SVG + "title").text))

    def test_front_view_draws_the_sloped_walls(self):
        root = ET.fromstring(layout_svg(self.plan, "front"))
        points = root.find(SVG + "polygon").get("points").split()
        self.assertEqual(len(points), 6)                           # floor, two walls, two slopes, ceiling
        flat = example()                                            # same layout, vertical walls (/1)
        flat["envelope"]["schema_version"] = "vandesign.lined-envelope/1"
        for key in ("upper_left_break_mm", "upper_left_inset_mm", "upper_right_break_mm", "upper_right_inset_mm"):
            del flat["envelope"]["parameters"][key]
        root = ET.fromstring(layout_svg(offline_plan(flat), "front"))
        self.assertEqual(len(root.find(SVG + "polygon").get("points").split()), 4)

    def test_unknown_view_refused(self):
        with self.assertRaises(ValueError):
            layout_svg(self.plan, "iso")


class Materials(unittest.TestCase):
    def test_summary_accounts_for_every_panel_and_area(self):
        profiles, _ = arrangement_profiles(offline_plan(example()).arrangement, tool_diameter=6)
        summary = material_summary(profiles)
        self.assertEqual(sum(g["panels"] for g in summary), len(profiles))
        self.assertAlmostEqual(sum(g["net_area_m2"] for g in summary),
                               sum(p.net_area_mm2 for p in profiles) / 1e6, places=2)
        sheet = SHEET_MM[0] * SHEET_MM[1] / 1e6
        for g in summary:
            self.assertGreaterEqual(g["blank_area_m2"], g["net_area_m2"])
            n = g["sheets_lower_bound"]
            self.assertTrue((n - 1) * sheet < g["blank_area_m2"] <= n * sheet + 1e-3, g)
        # The tab-slot cabinets are cut from the MEASURED thickness, not the nominal one.
        self.assertIn(17.6, {g["thickness_mm"] for g in summary})


class Tool(unittest.TestCase):
    def run_tool(self, *args):
        return subprocess.run([sys.executable, TOOL] + list(args), capture_output=True, text=True)

    def test_pack_is_complete_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "crafter")
            run = self.run_tool(EXAMPLE, "--out", out)
            self.assertEqual(run.returncode, 0, run.stderr)
            with open(os.path.join(out, "summary.json"), encoding="utf-8") as fh:
                summary = json.load(fh)
            profiles, joints = arrangement_profiles(offline_plan(example()).arrangement, tool_diameter=6)
            self.assertEqual(summary["fit"]["outcome"], "PASS")
            self.assertEqual(summary["panels"], len(profiles))
            self.assertEqual(sorted(summary["joints"]), sorted(joints))
            on_disk = sorted(os.path.relpath(os.path.join(d, f), out).replace(os.sep, "/")
                             for d, _, fs in os.walk(out) for f in fs if f != "summary.json")
            self.assertEqual(summary["files"], on_disk)
            self.assertEqual(sum(f.endswith(".dxf") for f in on_disk), len(profiles))
            self.assertIn("dxf/cutlist.csv", on_disk)
            self.assertTrue(any("not toolpaths" in s for s in summary["limits"]))
            with open(os.path.join(out, "top.svg"), encoding="utf-8") as fh:
                before = fh.read()
            again = self.run_tool(EXAMPLE, "--out", out)
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("new or empty", again.stderr)
            with open(os.path.join(out, "top.svg"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), before)

    def test_tool_diameter_is_required(self):
        request = example()
        del request["tool_diameter_mm"]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "request.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(request, fh)
            run = self.run_tool(path, "--out", os.path.join(tmp, "out"))
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("tool diameter is required", run.stderr)
            self.assertFalse(os.path.exists(os.path.join(tmp, "out")))


if __name__ == "__main__":
    unittest.main()
