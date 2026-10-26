"""ADR-0003 kitchen: one-piece L worktop, sink cut-out, hidden fixings into carcass tops."""
import copy
import json
import math
import os
import tempfile
import unittest

from vandesign.arrangement import MODULES, Instance, _canonical, build_arrangement, tab_slot_parts
from vandesign.arrangement_job import plan_request
from vandesign.manufacturing.carcass import cabinet_tab_slot_width_bindings
from vandesign.manufacturing.dxf import export_profiles, loop_areas, read_dxf
from vandesign.manufacturing.placement import arrangement_profiles
from vandesign.manufacturing.profile import Hole, ProfileError, ThroughCut, world_box
from vandesign.manufacturing.top import CarcassTop
from vandesign.schemas.envelope_spec import EnvelopeSpec

T = 17.6
D = T + 550                                                   # cabinet footprint depth
JOINERY = {"sheet": {"name": "birch", "nominal_mm": 18, "measured_mm": T}, "clearance_mm": 0.2,
           "tabs_per_edge": 2, "tab_width_mm": None, "tool_diameter_mm": 6, "blind_slot_depth_mm": 12,
           "dado_stop_mm": 20, "back_rabbet_mm": 8, "fronts": {"style": "inset"}, "top": {}}
WORKTOP = {"schema_version": "vandesign.worktop-l/1", "material_ref": "ply_main",
           "parameters": {"leg_a_length_mm": D + 1100, "leg_a_depth_mm": D + 20, "leg_b_length_mm": D + 800,
                          "leg_b_depth_mm": D + 20, "thickness_mm": T, "front_corner_radius_mm": 10,
                          "inside_corner_radius_mm": 25},
           "sink": {"leg": "b", "centre_x_mm": 300, "centre_y_mm": D + 400, "width_mm": 340, "length_mm": 400,
                    "corner_radius_mm": 15, "margin_mm": 50}}


def cab(width, **top):
    return {"cabinet": {"schema_version": "0.2", "module": "cabinet@1", "variant": "base", "profile_version": 1,
                        "parameters": {"width_mm": width, "ply_mm": T}},
            "joinery": dict(JOINERY, top=top)}


def kitchen(worktop=WORKTOP, sink_rail=80, top_a=None):
    """Two inset-door base cabinets in an L (walls at x = 0 and y = 0) under one L worktop."""
    return build_arrangement((
        Instance("kitchen.a", "cabinet_tab_slot", "KA", cab(1100) if top_a is None else top_a, (D, 0, 0), 2),
        Instance("kitchen.b", "cabinet_tab_slot", "KB", cab(800, sink_rail_mm=sink_rail), (0, D, 0), 1),
        Instance("kitchen.top", "worktop_l", "WT", worktop, (0, 0, 850), 0)))


def by_id(arr, values=None):
    return {p.panel_id: p for p in arrangement_profiles(arr, values, tool_diameter=6)[0]}


class Worktop(unittest.TestCase):
    def test_one_l_profile_with_radiused_corners_and_no_dog_bones(self):
        arr = kitchen()
        p = by_id(arr)
        self.assertNotIn("kitchen.top.panel.worktop.002", p)               # leg B is part of the one piece
        self.assertIn("kitchen.top.panel.worktop.002", {q.stable_id for q in arr.assembly.panels})
        top = p["kitchen.top.panel.worktop.001"]
        la, da, lb, db = D + 1100, D + 20, D + 800, D + 20
        k = 1 - math.pi / 4
        area = la * da + db * (lb - da) - 2 * k * 10 ** 2 + k * 25 ** 2
        self.assertAlmostEqual(top.outline.area, area, places=6)
        self.assertEqual(top.reliefs, 0)
        self.assertEqual(world_box(top), ((0.0, 0.0, 850.0), (la, lb, 850.0 + T)))
        sink = [f for f in top.features if isinstance(f, ThroughCut)]
        self.assertEqual(len(sink), 1)
        self.assertAlmostEqual(sink[0].loop.area, 340 * 400 - 4 * k * 15 ** 2, places=6)

    def test_box_model_is_the_exact_l(self):
        arr = kitchen()
        env = arr.assembly.parameters.resolve()
        legs = [q.box.resolve(env) for q in arr.assembly.panels if q.stable_id.startswith("kitchen.top.")]
        self.assertAlmostEqual(sum(b.volume for b in legs), ((D + 1100) * (D + 20) + (D + 20) * (800 - 20)) * T,
                               places=3)

    def test_hidden_fixings_line_up_through_the_carcass_tops(self):
        p = by_id(kitchen())
        top = p["kitchen.top.panel.worktop.001"]
        pilots = [h for h in top.features if isinstance(h, Hole)]
        clearance = [(q, h) for pid, q in p.items() if pid.endswith("panel.top.001")
                     for h in q.features if isinstance(h, Hole)]
        self.assertEqual(len(pilots), len(clearance))
        self.assertEqual(len(pilots), 12)
        world = sorted(tuple(round(v, 6) for v in top.frame.to_world(h.center[0], h.center[1], 0.0)) for h in pilots)
        below = sorted(tuple(round(v, 6) for v in q.frame.to_world(h.center[0], h.center[1], q.thickness))
                       for q, h in clearance)
        self.assertEqual(world, below)                                      # same points, worktop underside
        self.assertTrue(all(h.face == "bottom" and h.depth == 10.0 and h.diameter == 3.0 for h in pilots))
        self.assertTrue(all(h.depth is None and h.diameter == 5.0 for _, h in clearance))

    def test_sink_needs_an_opening_in_the_cabinet_below(self):
        with self.assertRaisesRegex(ProfileError, "sink_rail_mm"):
            by_id(kitchen(sink_rail=None))
        opening = [f for f in by_id(kitchen())["kitchen.b.panel.top.001"].features if isinstance(f, ThroughCut)]
        self.assertEqual(len(opening), 1)

    def test_everything_stays_editable(self):
        arr = kitchen()
        p = by_id(arr, {"WT_WT_A_Length": D + 1000, "WT_WT_Sink_Y": D + 350})
        self.assertEqual(world_box(p["kitchen.top.panel.worktop.001"])[1][0], D + 1000)
        # The sink cabinet stays width-editable natively with its rail frame and fixing holes.
        s = cab(800, sink_rail_mm=80)
        _, joinery = tab_slot_parts(s)
        asm = MODULES["cabinet_tab_slot"][0](_canonical(s))
        self.assertEqual(len(cabinet_tab_slot_width_bindings(asm, joinery, interval=(700, 800))), 8)

    def test_dxf_round_trip(self):
        top = by_id(kitchen())["kitchen.top.panel.worktop.001"]
        with tempfile.TemporaryDirectory() as tmp:
            export_profiles((top,), tmp)
            with open(os.path.join(tmp, top.panel_id + ".dxf"), encoding="ascii") as fh:
                entities = read_dxf(fh.read())
        self.assertAlmostEqual(loop_areas(entities, "OUTLINE")[0], top.outline.area, places=3)
        self.assertEqual(sum(1 for e in entities if e["type"] == "CIRCLE"), 12)


class Refusals(unittest.TestCase):
    def test_bad_geometry_and_specs(self):
        def changed(**kw):
            w = copy.deepcopy(WORKTOP)
            for key, value in kw.items():
                (w["sink"] if key in w["sink"] else w["parameters"])[key] = value
            return w
        with self.assertRaisesRegex(ProfileError, "tool radius"):
            by_id(kitchen(changed(inside_corner_radius_mm=2)))
        with self.assertRaisesRegex(ProfileError, "tool radius"):
            by_id(kitchen(changed(corner_radius_mm=2)))
        for bad in (changed(centre_x_mm=200), changed(width_mm=600)):            # inside the 50 mm margin
            with self.assertRaises(ValueError):
                kitchen(bad)
        for bad in (dict(WORKTOP, colour="oak"), dict(WORKTOP, sink=dict(WORKTOP["sink"], leg="c"))):
            with self.assertRaises(ValueError):
                kitchen(bad)
        with self.assertRaises(ProfileError):
            CarcassTop(sink_rail_mm=30)                                         # fixings outside the rails

    def test_live_planning_refuses_the_worktop(self):
        request = {"arrangement": {"schema_version": "vandesign.arrangement/1", "instances": [
            dict(instance_id="kitchen.top", module="worktop_l", param_prefix="WT", spec=WORKTOP,
                 position_mm=[5, 5, 850], quarter_turns=0)]},
            "envelope": json.loads(EnvelopeSpec().to_json()), "edits": []}
        with self.assertRaisesRegex(ValueError, "tab-and-slot base cabinet only"):
            plan_request(request)
        self.assertEqual(len(plan_request(request, allow_profile_modules=True).arrangement.instances), 1)


if __name__ == "__main__":
    unittest.main()
