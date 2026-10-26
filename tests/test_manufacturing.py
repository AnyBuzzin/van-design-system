"""Manufacturing profiles and DXF output, checked against the box models."""
import math
import os
import re
import tempfile
import unittest

from vandesign.core.geometry import Box, RoundedCornerOutline
from vandesign.core.tab_slot import RECEIVER, UPRIGHT
from vandesign.manufacturing.assembly import assembly_profiles, panel_profile, rectilinear_outline
from vandesign.manufacturing.catalog import MODULES, module_profiles, tab_slot_profiles
from vandesign.manufacturing.dxf import (dxf_text, export_profiles, loop_areas, pocket_layer,
                                         read_dxf)
from vandesign.manufacturing.profile import (Arc, Hole, Line, Loop, Pocket, PanelProfile, ProfileError,
                                             ThroughCut, polygon_loop, rect_vertices,
                                             rounded_corner_outline)
from vandesign.modules.cabinet import build_cabinet
from vandesign.modules.tab_slot import build_tab_slot
from vandesign.schemas.cabinet_spec import CabinetSpec
from vandesign.schemas.tab_slot_spec import TabSlotSpec

R_EXTRA = math.pi / 2 - 1  # area added per relieved corner, in units of r^2


class Panel:
    def __init__(self, sid):
        self.stable_id, self.display_name, self.material_ref = sid, sid, "ply"


class LoopGeometry(unittest.TestCase):
    def test_rounded_outline_matches_e11_area(self):
        loop = rounded_corner_outline(600, 800, 50)
        self.assertAlmostEqual(loop.area, RoundedCornerOutline(600, 800, 50).area_mm2, places=6)

    def test_slot_relief_adds_exact_area_and_centres(self):
        r = 3.0
        loop = polygon_loop(rect_vertices(10, 20, 70.5, 38.5), waste_inside=True, relief_radius=r)
        self.assertAlmostEqual(loop.area, 60.5 * 18.5 + 4 * r * r * R_EXTRA, places=9)
        centres = sorted(s.center for s in loop.segments if isinstance(s, Arc))
        a = r / math.sqrt(2)
        self.assertEqual(len(centres), 4)
        for c, e in zip(centres, sorted([(10 + a, 20 + a), (70.5 - a, 20 + a),
                                         (70.5 - a, 38.5 - a), (10 + a, 38.5 - a)])):
            self.assertAlmostEqual(math.dist(c, e), 0, places=9)

    def test_outline_relief_removes_material_at_inside_corners_only(self):
        r = 3.0
        verts = rectilinear_outline(100, 50, [(0, 0, 30, 20)])  # corner notch: 1 inside corner
        plain = polygon_loop(verts, waste_inside=False)
        relieved = polygon_loop(verts, waste_inside=False, relief_radius=r)
        self.assertAlmostEqual(plain.area, 100 * 50 - 30 * 20, places=9)
        self.assertAlmostEqual(plain.area - relieved.area, r * r * R_EXTRA, places=9)
        self.assertEqual(sum(isinstance(s, Arc) for s in relieved.segments), 1)

    def test_open_pocket_corners_are_not_relieved(self):
        loop = polygon_loop(rect_vertices(0, 10, 40, 30), waste_inside=True, relief_radius=3,
                            open_points=[(0, 10), (0, 30)])
        self.assertEqual(sum(isinstance(s, Arc) for s in loop.segments), 2)

    def test_invalid_geometry_refused(self):
        with self.assertRaises(ProfileError):
            Loop((Line((0, 0), (1, 0)), Line((1, 0), (1, 1))))          # open
        with self.assertRaises(ProfileError):
            polygon_loop(((0, 0), (0, 1), (1, 1), (1, 0)), waste_inside=True)  # clockwise
        with self.assertRaises(ProfileError):
            polygon_loop(rect_vertices(0, 0, 8, 8), waste_inside=True, relief_radius=3)  # reliefs overlap
        with self.assertRaises(ProfileError):
            polygon_loop(rect_vertices(0, 0, 8, 8), waste_inside=True, relief_radius=float("nan"))
        with self.assertRaises(ProfileError):
            rectilinear_outline(100, 50, [(40, -1, 60, 51)])            # splits the panel
        outline = polygon_loop(rect_vertices(0, 0, 100, 50), waste_inside=False)
        pocket = polygon_loop(rect_vertices(10, 10, 20, 20), waste_inside=True)
        with self.assertRaises(ProfileError):
            PanelProfile("p", "p", "ply", 18, outline, (Pocket(pocket, 18, "top"),))
        with self.assertRaises(ProfileError):
            PanelProfile("p", "p", "ply", 18, outline,
                         (ThroughCut(polygon_loop(rect_vertices(90, 40, 120, 45), waste_inside=True)),))


class FeatureContainment(unittest.TestCase):
    """Regressions from review: features must lie in actual material, not just its bounds."""

    def profile(self, outline, *features):
        return PanelProfile("p", "p", "ply", 18, outline, features)

    def cut(self, x0, y0, x1, y1, relief=None):
        return polygon_loop(rect_vertices(x0, y0, x1, y1), waste_inside=True, relief_radius=relief)

    def test_through_cut_beyond_rounded_corner_refused(self):
        outline = rounded_corner_outline(100, 100, 90)       # corner (90,90)..(100,100) is not material
        with self.assertRaisesRegex(ProfileError, "outside the outline material"):
            self.profile(outline, ThroughCut(self.cut(90, 90, 99, 99)))
        with self.assertRaisesRegex(ProfileError, "outside the outline material"):
            self.profile(outline, ThroughCut(self.cut(60, 60, 85, 85)))  # partly past the arc
        ok = self.profile(outline, ThroughCut(self.cut(10, 10, 40, 40)))
        self.assertAlmostEqual(ok.net_area_mm2, outline.area - 900, places=6)

    def test_relieved_cut_must_keep_its_relief_inside(self):
        outline = polygon_loop(rect_vertices(0, 0, 100, 50), waste_inside=False)
        self.profile(outline, ThroughCut(self.cut(1, 10, 40, 30, relief=3)))  # bone reaches x = 0.12: inside
        with self.assertRaisesRegex(ProfileError, "touches|outside"):
            self.profile(outline, ThroughCut(self.cut(0.5, 10, 40, 30, relief=3)))  # bone reaches x = -0.38

    def test_edge_contact_rules(self):
        outline = polygon_loop(rect_vertices(0, 0, 100, 50), waste_inside=False)
        with self.assertRaisesRegex(ProfileError, "notch"):
            self.profile(outline, ThroughCut(self.cut(0, 10, 20, 30)))           # edge-touching through-cut
        open_pocket = polygon_loop(rect_vertices(0, 10, 20, 30), waste_inside=True, relief_radius=3,
                                   open_points=[(0, 10), (0, 30)])
        self.assertEqual(len(self.profile(outline, Pocket(open_pocket, 6, "top")).features), 1)
        with self.assertRaisesRegex(ProfileError, "outside"):
            self.profile(outline, Pocket(self.cut(80, 10, 120, 30), 6, "top"))   # overhangs the edge

    def test_holes_need_material_all_round(self):
        outline = rounded_corner_outline(100, 100, 90)
        self.profile(outline, Hole((20, 20), 8))
        with self.assertRaisesRegex(ProfileError, "outside"):
            self.profile(outline, Hole((96, 96), 4))
        with self.assertRaisesRegex(ProfileError, "touches"):
            self.profile(outline, Hole((4, 50), 8))

    def test_explicit_tool_diameter_is_never_replaced(self):
        for bad in (0, -1, float("nan"), float("inf"), True, "6"):
            with self.assertRaises(ProfileError, msg=repr(bad)):
                tab_slot_profiles(tool_diameter=bad)
        default = {p.panel_id: p for p in tab_slot_profiles()}
        explicit = {p.panel_id: p for p in tab_slot_profiles(tool_diameter=6.35)}
        self.assertNotAlmostEqual(default[RECEIVER].volume_mm3, explicit[RECEIVER].volume_mm3, places=3)
        self.assertIn("6.350 mm tool", explicit[RECEIVER].notes[0])


class PanelConversion(unittest.TestCase):
    def test_refusals(self):
        box = Box((0, 0, 0), (100, 50, 18))
        with self.assertRaises(ProfileError):
            panel_profile(Panel("p"), box, [Box((10, 10, 5), (20, 20, 10))], tool_diameter=6)  # void
        with self.assertRaises(ProfileError):
            panel_profile(Panel("p"), Box((0, 0, 0), (18, 18, 50)), [], tool_diameter=6)    # ambiguous
        with self.assertRaises(ProfileError):
            panel_profile(Panel("p"), box, [], tool_diameter=None)                        # relief needs tool
        with self.assertRaises(ProfileError):
            panel_profile(Panel("p"), box, [Box((0, 0, 0), (10, 10, 18))], tool_diameter=6,
                          corner_radius=5)                                                 # rounded + notch
        with self.assertRaises(ProfileError):
            panel_profile(Panel("p"), box, [Box((200, 0, 0), (210, 10, 18))], tool_diameter=6)  # misses panel

    def test_cabinet_volumes_equal_box_model_without_relief(self):
        asm = build_cabinet(CabinetSpec())
        env = asm.parameters.resolve()
        boxes = {p.stable_id: p.box.resolve(env) for p in asm.panels}
        expected = {pid: b.volume for pid, b in boxes.items()}
        for op in asm.operations:
            expected[op.target_panel_id] -= boxes[op.target_panel_id].overlap_volume(op.cut.resolve(env))
        for prof in assembly_profiles(asm, relief=False):
            self.assertTrue(math.isclose(prof.volume_mm3, expected[prof.panel_id], rel_tol=1e-12),
                            prof.panel_id)

    def test_cabinet_grooves_on_machined_face_with_stopped_end_relief(self):
        asm = build_cabinet(CabinetSpec())
        env = asm.parameters.resolve()
        profs = {p.panel_id: p for p in assembly_profiles(asm, tool_diameter=6)}
        for side in ("panel.left.001", "panel.right.001"):
            p = profs[side]
            self.assertEqual(p.faces_machined, ("top",), side)       # no flip needed
            pockets = [f for f in p.features if isinstance(f, Pocket)]
            self.assertEqual(len(pockets), CabinetSpec().shelf_count)
            self.assertAlmostEqual(pockets[0].depth, env["Cab_Dado_Depth"], places=9)
            self.assertEqual(p.reliefs, 2 * len(pockets))            # open front, stopped back
        no_relief = {p.panel_id: p for p in assembly_profiles(asm, relief=False)}
        p, q = profs["panel.left.001"], no_relief["panel.left.001"]
        self.assertAlmostEqual(q.volume_mm3 - p.volume_mm3, p.reliefs * 9 * R_EXTRA * 6, places=6)


class TabSlotCoupon(unittest.TestCase):
    def test_profiles_reproduce_e12_volumes_and_relief(self):
        spec = TabSlotSpec()
        g = build_tab_slot(spec).geometry()
        profs = {p.panel_id: p for p in tab_slot_profiles(spec)}
        r = g.radius
        self.assertTrue(math.isclose(profs[RECEIVER].volume_mm3, g.volumes[RECEIVER], rel_tol=1e-12))
        # The upright additionally gets two tab-root dog-bones (absent from the E1.2 model).
        self.assertEqual(profs[UPRIGHT].reliefs, 2)
        self.assertTrue(math.isclose(profs[UPRIGHT].volume_mm3,
                                     g.volumes[UPRIGHT] - 2 * r * r * R_EXTRA * 18, rel_tol=1e-12))
        arcs = [s for f in profs[RECEIVER].features for s in f.loop.segments if isinstance(s, Arc)]
        for c, e in zip(sorted(a.center for a in arcs), sorted(g.centres)):
            self.assertAlmostEqual(math.dist(c, e), 0, places=9)

    def test_tab_fits_slot_with_specified_clearance(self):
        spec = TabSlotSpec()
        profs = {p.panel_id: p for p in tab_slot_profiles(spec)}
        (sx0, sy0), (sx1, sy1) = profs[RECEIVER].features[0].loop.bounds
        r = spec.tool_diameter_mm / 2
        slot_w = sx1 - sx0 - 2 * (r - r / math.sqrt(2))   # strip relief bulge from bounds
        slot_h = sy1 - sy0 - 2 * (r - r / math.sqrt(2))
        self.assertAlmostEqual(slot_w - spec.tab_width_mm, spec.clearance_mm, places=6)
        self.assertAlmostEqual(slot_h - profs[UPRIGHT].thickness, spec.clearance_mm, places=6)


class DxfOutput(unittest.TestCase):
    def test_every_module_round_trips_through_dxf(self):
        layer_re = re.compile(r"^[A-Z0-9_$-]+$")
        for name in MODULES:
            for prof in module_profiles(name, tool_diameter=6):
                text = dxf_text(prof)
                self.assertIn("$INSUNITS\n70\n4\n", text)
                ents = read_dxf(text)
                self.assertTrue(all(layer_re.match(e["layer"]) for e in ents), prof.panel_id)
                self.assertEqual(sum(e["type"] == "ARC" for e in ents),
                                 sum(isinstance(s, Arc) for s in prof.outline.segments)
                                 + sum(isinstance(s, Arc) for f in prof.features for s in f.loop.segments))
                got = loop_areas(ents, "OUTLINE")
                self.assertEqual(len(got), 1)
                self.assertAlmostEqual(got[0], prof.outline.area, delta=1e-6 * prof.outline.area)
                by_layer = {}
                for f in prof.features:
                    layer = "THROUGH" if isinstance(f, ThroughCut) else pocket_layer(f.face, f.depth)
                    by_layer.setdefault(layer, []).append(f.loop.area)
                for layer, areas in by_layer.items():
                    for a, b in zip(loop_areas(ents, layer), sorted(areas)):
                        self.assertAlmostEqual(a, b, delta=1e-6 * b)

    def test_export_writes_files_and_never_overwrites(self):
        profs = tab_slot_profiles()
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "coupon")
            written = export_profiles(profs, out)
            self.assertEqual(sorted(os.listdir(out)),
                             sorted(["cutlist.csv", RECEIVER + ".dxf", UPRIGHT + ".dxf"]))
            self.assertEqual(len(written), 3)
            with open(os.path.join(out, "cutlist.csv"), encoding="utf-8") as fh:
                self.assertEqual(len(fh.read().strip().splitlines()), 3)
            with self.assertRaises(FileExistsError):
                export_profiles(profs, out)


if __name__ == "__main__":
    unittest.main()
