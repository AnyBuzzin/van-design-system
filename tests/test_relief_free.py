"""#95 Option B producer: relief-free CAD oracle, exact relation to the relieved DXF truth."""
from dataclasses import replace
import os
import tempfile
import unittest

from vandesign.arrangement import MODULES, Instance, _canonical, build_arrangement, tab_slot_parts
from vandesign.manufacturing.assembly import relief_area, relief_proof
from vandesign.manufacturing.carcass import cabinet_tab_slot_profiles, cabinet_tab_slot_width_bindings
from vandesign.manufacturing.dxf import export_profiles, loop_areas, pocket_layer, read_dxf
from vandesign.manufacturing.placement import arrangement_profiles, arrangement_width_bindings
from vandesign.manufacturing.profile import (Arc, PanelFrame, PanelProfile, Pocket, ProfileError,
                                             rounded_corner_outline)

CAB = {"schema_version": "0.2", "module": "cabinet@1", "variant": "base", "profile_version": 1,
       "parameters": {"width_mm": 1100, "ply_mm": 17.6}}
JOINERY = {"sheet": {"name": "birch", "nominal_mm": 18, "measured_mm": 17.6}, "clearance_mm": 0.2,
           "tabs_per_edge": 2, "tab_width_mm": None, "tool_diameter_mm": 6}
HOUSED = dict(JOINERY, blind_slot_depth_mm=12, dado_stop_mm=20, back_rabbet_mm=8)
WIDTHS = (1000.0, 1050.0, 1100.0, 1000.0, 1100.0)                 # edit, intermediate, restore


def arrangement(k=1, joinery=JOINERY):
    """The #95 qualification cabinet: base, 1100 mm, at its live request position."""
    return build_arrangement((Instance("k", "cabinet_tab_slot", "K", {"cabinet": CAB, "joinery": joinery},
                                       (100, 2800, 5), k),))


def lines_only(profile):
    return not any(isinstance(s, Arc) for loop in [profile.outline] + [f.loop for f in profile.features]
                   for s in loop.segments)


class ReliefFreeView(unittest.TestCase):
    def test_default_is_unchanged_and_relieved(self):
        arr = arrangement()
        self.assertEqual(arrangement_profiles(arr, tool_diameter=6),
                         arrangement_profiles(arr, tool_diameter=6, relief=True))
        self.assertTrue(any(p.reliefs for p in arrangement_profiles(arr, tool_diameter=6)[0]))

    def test_same_parts_lines_only_and_exactly_related_for_every_turn_and_option(self):
        for joinery in (JOINERY, HOUSED):
            for k in range(4):
                arr = arrangement(k, joinery)
                relieved, joints = arrangement_profiles(arr, tool_diameter=6)
                free, free_joints = arrangement_profiles(arr, tool_diameter=6, relief=False)
                self.assertEqual([p.panel_id for p in free], [p.panel_id for p in relieved])
                self.assertTrue(all(lines_only(p) and p.reliefs == 0 for p in free))
                self.assertEqual(repr(joints), repr(free_joints))            # joints are not reliefs
                records = relief_proof(relieved, free, 6)
                self.assertEqual(sum(r["reliefs"] for r in records), sum(p.reliefs for p in relieved))
                self.assertGreater(sum(r["removed_volume_mm3"] for r in records), 0)

    def test_proof_refuses_anything_but_dog_bones(self):
        arr = arrangement()
        relieved, _ = arrangement_profiles(arr, tool_diameter=6)
        free, _ = arrangement_profiles(arr, tool_diameter=6, relief=False)
        with self.assertRaises(ProfileError):
            relief_proof(relieved, free, 8)                                     # wrong tool radius
        with self.assertRaisesRegex(ProfileError, "not lines only"):
            relief_proof(relieved, relieved, 6)
        side = next(i for i, p in enumerate(free) if any(isinstance(f, Pocket) for f in p.features))
        f = next(f for f in free[side].features if isinstance(f, Pocket))
        moved = list(free)
        moved[side] = replace(free[side], features=tuple(replace(g, depth=g.depth + 1) if g is f else g
                                                         for g in free[side].features))
        with self.assertRaisesRegex(ProfileError, "feature differs"):
            relief_proof(relieved, tuple(moved), 6)
        with self.assertRaisesRegex(ProfileError, "different panels"):
            relief_proof(relieved, free[:-1], 6)
        frame = PanelFrame((0.0, 0.0, 0.0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
        rounded = PanelProfile("r", "r", "ply", 18.0, rounded_corner_outline(200, 120, 20), frame=frame)
        with self.assertRaisesRegex(ProfileError, "not lines only|not a .* dog-bone"):
            relief_proof((rounded,), (rounded,), 6)

    def test_relieved_dxf_rereads_to_the_relief_free_oracle_plus_exact_reliefs(self):
        arr = arrangement()
        relieved, _ = arrangement_profiles(arr, tool_diameter=6)
        free = {p.panel_id: p for p in arrangement_profiles(arr, tool_diameter=6, relief=False)[0]}
        d = relief_area(3.0)
        with tempfile.TemporaryDirectory() as tmp:
            export_profiles(relieved, tmp)                                     # the DXF stays relieved
            for p in relieved:
                with open(os.path.join(tmp, p.panel_id + ".dxf"), encoding="ascii") as fh:
                    entities = read_dxf(fh.read())
                outline = loop_areas(entities, "OUTLINE")
                arcs = sum(isinstance(s, Arc) for s in p.outline.segments)
                self.assertEqual(len(outline), 1)
                tol = 1e-8 * p.outline.area + 1e-3                              # DXF decimal rounding
                self.assertAlmostEqual(outline[0], p.outline.area, delta=tol)
                self.assertAlmostEqual(outline[0], free[p.panel_id].outline.area - arcs * d, delta=tol)
                for fr, ff in zip(p.features, free[p.panel_id].features):
                    if isinstance(fr, Pocket):
                        areas = loop_areas(entities, pocket_layer(fr.face, fr.depth))
                        n = sum(isinstance(s, Arc) for s in fr.loop.segments)
                        self.assertTrue(any(abs(a - (ff.loop.area + n * d)) < 1e-3 for a in areas), p.panel_id)


class ReliefFreeBindings(unittest.TestCase):
    def test_lines_only_native_width_bindings_with_the_same_provenance(self):
        for k in range(4):
            arr = arrangement(k)
            free = arrangement_width_bindings(arr, "k", relief=False)
            relieved = arrangement_width_bindings(arr, "k")
            self.assertEqual(set(free), set(relieved))
            for pid, b in free.items():
                r = relieved[pid]
                loops = [b.outline] + [f.loop for f in b.features]
                self.assertTrue(all(s[0] == "line" for loop in loops for s in loop.sources), pid)
                self.assertEqual([f.feature_id for f in b.features], [f.feature_id for f in r.features])
                self.assertEqual((b.parameter, b.interval, b.frame_axes), (r.parameter, r.interval, r.frame_axes))
                self.assertEqual([e.render() for e in b.frame_origin], [e.render() for e in r.frame_origin])
                self.assertEqual([(u.render(), v.render()) for u, v in b.outline.vertices],
                                 [(u.render(), v.render()) for u, v in r.outline.vertices])
            for w in WIDTHS:
                values = {"K_Cab_Width": w}
                env = arr.assembly.parameters.resolve(values)
                for p in arrangement_profiles(arr, values, tool_diameter=6, relief=False)[0]:
                    self.assertIsNone(free[p.panel_id].mismatch(p, env), (k, w, p.panel_id))

    def test_module_bindings_follow_the_flag(self):
        s = {"cabinet": CAB, "joinery": JOINERY}
        _, joinery = tab_slot_parts(s)
        asm = MODULES["cabinet_tab_slot"][0](_canonical(s))
        free = cabinet_tab_slot_width_bindings(asm, joinery, relief=False)
        env = asm.parameters.resolve({"Cab_Width": 1000})
        for p in cabinet_tab_slot_profiles(asm, joinery, {"Cab_Width": 1000}, relief=False)[0]:
            self.assertIsNone(free[p.panel_id].mismatch(p, env))
        relieved_side = next(p for p in cabinet_tab_slot_profiles(asm, joinery, {"Cab_Width": 1000})[0]
                             if p.panel_id == "panel.left.001")
        self.assertIsNotNone(free["panel.left.001"].mismatch(relieved_side, env))   # views never mix


if __name__ == "__main__":
    unittest.main()
