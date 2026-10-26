"""#95 producer: Expr width bindings for tab-and-slot cabinets (offline)."""
from dataclasses import replace
import hashlib
import json
import os
import unittest

from vandesign.arrangement import MODULES, Instance, _canonical, build_arrangement, tab_slot_parts
from vandesign.arrangement_job import plan_request
from vandesign.core.expr import Mm, Param
from vandesign.manufacturing.assembly import Tracked, recording_decisions
from vandesign.manufacturing.carcass import (WIDTH, cabinet_tab_slot_profiles, cabinet_tab_slot_width_bindings,
                                             check_decisions)
from vandesign.manufacturing.placement import arrangement_profiles, arrangement_width_bindings
from vandesign.manufacturing.profile import ProfileError

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
# Computed on develop df52642 before #95 bindings: numeric outputs must not change.
BASELINE_SHA = "1744f99cc1f713602bfdb9a0fe566a803a1160ada93652d5ecfbebb4b83c516f"
CAB = {"schema_version": "0.2", "module": "cabinet@1", "variant": "base", "profile_version": 1,
       "parameters": {"width_mm": 1100, "ply_mm": 17.6}}
JOINERY = {"sheet": {"name": "birch", "nominal_mm": 18, "measured_mm": 17.6}, "clearance_mm": 0.2,
           "tabs_per_edge": 2, "tab_width_mm": None, "tool_diameter_mm": 6}
WIDTHS = (1000.0, 1050.0, 1100.0, 1000.0, 1100.0)     # edit, intermediate, restore (twice)


def spec(variant="base", width=1100):
    return {"cabinet": dict(CAB, variant=variant, parameters={"width_mm": width, "ply_mm": 17.6}),
            "joinery": JOINERY}


def module(s):
    _, joinery = tab_slot_parts(s)
    return MODULES["cabinet_tab_slot"][0](_canonical(s)), joinery


def refs(binding):
    out = set()
    exprs = list(binding.frame_origin) + [binding.thickness]
    for loop in [binding.outline] + [f.loop for f in binding.features]:
        exprs += [e for uv in loop.vertices for e in uv]
    for e in exprs:
        out |= e.refs()
    return out


class NumericOutputsUnchanged(unittest.TestCase):
    def test_profiles_are_bit_identical_to_develop(self):
        h = hashlib.sha256()
        for k in range(4):
            for variant in ("base", "overhead", "tall"):
                for w in ((1100, 1000) if variant != "tall" else (800, 700)):
                    arr = build_arrangement((Instance("k", "cabinet_tab_slot", "K", spec(variant, w),
                                                      (1000, 1000, 0), k),))
                    h.update(repr(arrangement_profiles(arr, tool_diameter=6)).encode())
                box = dict(CAB, variant=variant, parameters={"width_mm": 900})
                arr = build_arrangement((Instance("c", "cabinet", "C", box, (1000, 1000, 0), k),))
                h.update(repr(arrangement_profiles(arr, tool_diameter=6)).encode())
        with open(os.path.join(ROOT, "automation", "jobs", "requests", "arrangement_request_crafter.json"),
                  encoding="utf-8") as fh:
            request = json.load(fh)
        h.update(repr(arrangement_profiles(plan_request(request).arrangement, tool_diameter=6)).encode())
        self.assertEqual(h.hexdigest(), BASELINE_SHA)


class ModuleBindings(unittest.TestCase):
    def check(self, variant, width, interval, widths):
        asm, joinery = module(spec(variant, width))
        bindings = cabinet_tab_slot_width_bindings(asm, joinery, interval=interval)
        for w in widths:
            values = {WIDTH: w}
            env = asm.parameters.resolve(values)
            profiles, _ = cabinet_tab_slot_profiles(asm, joinery, values)
            self.assertEqual(set(bindings), {p.panel_id for p in profiles})
            for p in profiles:
                self.assertIsNone(bindings[p.panel_id].mismatch(p, env), (variant, w, p.panel_id))
        return asm, joinery, bindings

    def test_bindings_reproduce_the_producer_through_edit_and_restore(self):
        self.check("base", 1100, (1000, 1100), WIDTHS)
        self.check("overhead", 1100, (1000, 1100), WIDTHS)
        self.check("tall", 800, (700, 800), (700.0, 750.0, 800.0))

    def test_at_the_current_width_the_bindings_are_exact(self):
        asm, joinery, bindings = self.check("base", 1100, (1000, 1100), ())
        env = asm.parameters.resolve()
        for p in cabinet_tab_slot_profiles(asm, joinery)[0]:
            b = bindings[p.panel_id]
            self.assertEqual(b.outline.resolve(env), p.outline)
            self.assertEqual([f.loop.resolve(env) for f in b.features], [f.loop for f in p.features])

    def test_width_provenance_is_where_the_geometry_moves(self):
        asm, _, b = self.check("base", 1100, (1000, 1100), ())
        a, z = asm.parameters.resolve({WIDTH: 1100}), asm.parameters.resolve({WIDTH: 1000})

        def moves(e):   # directly or through a derived parameter such as Cab_Shelf_Length
            return e.eval(a) != e.eval(z)

        def shape_moves(binding):
            return any(moves(e) for loop in [binding.outline] + [f.loop for f in binding.features]
                       for uv in loop.vertices for e in uv)
        self.assertFalse(shape_moves(b["panel.left.001"]) or any(map(moves, b["panel.left.001"].frame_origin)))
        self.assertIn(WIDTH, b["panel.right.001"].frame_origin[0].refs())     # moves, shape fixed
        self.assertFalse(shape_moves(b["panel.right.001"]))
        for pid in ("panel.bottom.001", "panel.top.001", "panel.back.001", "panel.shelf.001", "panel.door.001"):
            self.assertTrue(shape_moves(b[pid]), pid)
        self.assertEqual([f.feature_id for f in b["panel.left.001"].features],
                         ["panel.left.001.cut.%03d" % (i + 1) for i in range(len(b["panel.left.001"].features))])

    def test_a_lost_provenance_is_caught(self):
        asm, joinery, b = self.check("base", 1100, (1000, 1100), ())
        bottom = b["panel.bottom.001"]
        i = next(i for i, (u, _) in enumerate(bottom.outline.vertices) if WIDTH in u.refs())
        verts = list(bottom.outline.vertices)
        verts[i] = (Mm(verts[i][0].eval(asm.parameters.resolve())), verts[i][1])   # frozen at 1100
        frozen = replace(bottom, outline=replace(bottom.outline, vertices=tuple(verts)))
        p = next(p for p in cabinet_tab_slot_profiles(asm, joinery, {WIDTH: 1000})[0]
                 if p.panel_id == "panel.bottom.001")
        self.assertIsNotNone(frozen.mismatch(p, asm.parameters.resolve({WIDTH: 1000})))

    def test_refusals(self):
        asm, joinery = module(spec())
        for bad in (dict(parameter="Cab_Depth"), dict(interval=(1000, 1090)), dict(interval=(1100, 1000)),
                    dict(interval=(1000,)), dict(interval=(1000, float("inf")))):
            with self.assertRaises(ProfileError, msg=repr(bad)):
                cabinet_tab_slot_width_bindings(asm, joinery, **bad)
        with self.assertRaises(ValueError):          # the producer itself refuses at the far end
            cabinet_tab_slot_width_bindings(asm, joinery, interval=(1, 1100))


class Decisions(unittest.TestCase):
    def test_tracked_values_are_the_same_floats_with_provenance(self):
        w = Tracked(1100.0, Param("W"))
        x = (w - 17.6) / 2 + 3
        self.assertEqual(x, (1100.0 - 17.6) / 2 + 3)
        self.assertEqual(x.expr.eval({"W": 1000.0}), (1000.0 - 17.6) / 2 + 3)
        self.assertNotIsInstance(w * Tracked(2.0, Mm(2)), Tracked)            # areas carry no provenance
        with recording_decisions() as log:
            max(w, Tracked(1050.0, Mm(1050)))
        self.assertEqual(len(log), 1)
        w < 5                                                                 # not recording: no log
        self.assertEqual(len(log), 1)

    def test_a_decision_that_flips_inside_the_interval_is_refused(self):
        w = Tracked(1100.0, Param("W"))
        with recording_decisions() as log:
            max(w, Tracked(1050.0, Mm(1050)))                                 # W wins at 1100, not at 1000
        check_decisions(log, {"W": 1100.0}, [{"W": 1060.0}])
        with self.assertRaisesRegex(ProfileError, "decision changes"):
            check_decisions(log, {"W": 1100.0}, [{"W": 1000.0}, {"W": 1100.0}])


class WorldBindings(unittest.TestCase):
    def test_all_quarter_turns_match_arrangement_profiles(self):
        for k in range(4):
            arr = build_arrangement((Instance("k", "cabinet_tab_slot", "K", spec(), (1000, 1000, 0), k),))
            bindings = arrangement_width_bindings(arr, "k")
            names = set(arr.assembly.parameters.names())
            for w in WIDTHS:
                values = {"K_" + WIDTH: w}
                env = arr.assembly.parameters.resolve(values)
                profiles, _ = arrangement_profiles(arr, values, tool_diameter=6)
                for p in profiles:
                    self.assertIsNone(bindings[p.panel_id].mismatch(p, env), (k, w, p.panel_id))
            for pid, b in bindings.items():
                self.assertTrue(pid.startswith("k.panel."))
                self.assertEqual(b.parameter, "K_" + WIDTH)
                self.assertLessEqual(refs(b), names)
                self.assertTrue(all(f.feature_id.startswith(pid + ".cut.") for f in b.features))
            # After the quarter turn every frame origin follows the width except where the turn cancels it.
            self.assertIn("K_" + WIDTH, refs(bindings["k.panel.right.001"]))

    def test_other_instances_are_refused(self):
        bed = {"module": "bed-platform@1", "schema_version": "vandesign.bed-platform/1",
               "parameters": {"height_mm": 700.0, "length_mm": 1900.0, "ply_mm": 18.0, "width_mm": 1400.0}}
        arr = build_arrangement((Instance("b", "bed", "B", bed, (0, 0, 0), 0),
                                 Instance("k", "cabinet_tab_slot", "K", spec(), (0, 2500, 0), 0)))
        for iid in ("b", "missing"):
            with self.assertRaises(ProfileError):
                arrangement_width_bindings(arr, iid)
        self.assertEqual(len(arrangement_width_bindings(arr, "k")), 8)


if __name__ == "__main__":
    unittest.main()
