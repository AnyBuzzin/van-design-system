"""B2 angled upper walls: schema, exact sloped-plane fit, refusals, unchanged /1."""
from dataclasses import replace
import hashlib
import json
import math
import os
import unittest

from vandesign.arrangement import ArrangementError, Instance, build_arrangement
from vandesign.arrangement_job import expected_evidence, plan_request
from vandesign.schemas.envelope_spec import SCHEMA, SCHEMA2, EnvelopeSpec, KeepOut, load_envelope_spec

ROOT = os.path.join(os.path.dirname(__file__), "..")
# Computed on develop 3ca905d before B2: existing specs and accepted M1 evidence keep their identity.
V1_DEFAULT_JSON_SHA = "8c5bab305e6c2c057bb92ee4c302bdd04b2e5ae128beee2040d40f39d42696ba"
M1_CRAFTER_PLAN_HASH = "bb0c3afaed7f125eeb5003a1e48146cf3945f77f19a484663ee172a489c35001"

CRAFTER = EnvelopeSpec(bare_width_mm=1832, bare_length_mm=4606, bare_height_mm=1961, lining_mm=18,
                       tolerance_mm=5, bare_between_arches_mm=1380, arch_length_mm=800,
                       arch_height_mm=300, arch_y_mm=2000, provenance="TEST ONLY: Crafter CR35; walls ASSUMED")
SLOPED = replace(CRAFTER, upper_left_break_mm=1200, upper_left_inset_mm=150,
                 upper_right_break_mm=1250, upper_right_inset_mm=120)
CABINET = {"schema_version": "0.2", "module": "cabinet@1", "variant": "base",
           "profile_version": 1, "parameters": {"width_mm": 1100}}


def left_cabinet(x, z=1000, y=2800):
    # Quarter-turned against the left wall: back panel nearest the wall, 850 high.
    return (Instance("kitchen.left", "cabinet", "K1", CABINET, (x, y, z), 1),)


class Schema(unittest.TestCase):
    def test_existing_specs_and_m1_request_are_byte_identical(self):
        self.assertEqual(hashlib.sha256(EnvelopeSpec().to_json().encode()).hexdigest(), V1_DEFAULT_JSON_SHA)
        self.assertNotIn("upper_", EnvelopeSpec().to_json())
        with open(os.path.join(ROOT, "automation", "jobs", "requests", "arrangement_request_crafter.json"),
                  encoding="utf-8") as fh:
            request = json.load(fh)
        self.assertEqual(plan_request(request).arrangement.assembly.spec_hash, M1_CRAFTER_PLAN_HASH)

    def test_schema2_round_trip(self):
        text = SLOPED.to_json()
        self.assertEqual(json.loads(text)["schema_version"], SCHEMA2)
        self.assertEqual(load_envelope_spec(text), SLOPED)
        self.assertEqual(SLOPED.upper_walls, ("left", "right"))
        one = replace(CRAFTER, upper_right_break_mm=1250, upper_right_inset_mm=120)
        self.assertEqual(load_envelope_spec(one.to_json()).upper_walls, ("right",))

    def test_invalid_walls_and_schemas_refused(self):
        h = CRAFTER.heights[0]
        for bad in (dict(upper_left_break_mm=1200), dict(upper_left_inset_mm=150),
                    dict(upper_left_break_mm=h, upper_left_inset_mm=150),
                    dict(upper_left_break_mm=0, upper_left_inset_mm=150),
                    dict(upper_left_break_mm=1200, upper_left_inset_mm=-1),
                    dict(upper_left_break_mm=1200, upper_left_inset_mm=float("nan")),
                    dict(upper_left_break_mm=True, upper_left_inset_mm=150),
                    dict(upper_left_break_mm=1200, upper_left_inset_mm=900,
                         upper_right_break_mm=1200, upper_right_inset_mm=900)):
            with self.assertRaises(ValueError, msg=repr(bad)):
                replace(CRAFTER, **bad)
        v1 = json.loads(CRAFTER.to_json())
        with self.assertRaises(ValueError):                         # /1 cannot carry walls
            load_envelope_spec(json.dumps(dict(v1, parameters=dict(
                v1["parameters"], upper_left_break_mm=1200, upper_left_inset_mm=150, upper_right_break_mm=None,
                upper_right_inset_mm=None))))
        with self.assertRaises(ValueError):                         # /2 must carry a wall
            load_envelope_spec(json.dumps(dict(schema_version=SCHEMA2, parameters=dict(
                v1["parameters"], upper_left_break_mm=None, upper_left_inset_mm=None,
                upper_right_break_mm=None, upper_right_inset_mm=None))))
        self.assertEqual(json.loads(CRAFTER.to_json())["schema_version"], SCHEMA)

    def test_each_wheel_arch_is_checked_against_its_own_sloped_wall(self):
        """Review regression: the right arch was never checked (asymmetric walls)."""
        ah = CRAFTER.arch_height_mm - CRAFTER.lining_mm             # exposed arch top, 282 mm
        with self.assertRaisesRegex(ValueError, "Obstruction outside"):
            replace(CRAFTER, upper_right_break_mm=100, upper_right_inset_mm=500)   # Jack's repro
        with self.assertRaisesRegex(ValueError, "Obstruction outside"):
            replace(CRAFTER, upper_left_break_mm=100, upper_left_inset_mm=500)
        # Valid asymmetric cases: one low steep wall above the arch top, the other vertical.
        for side in ("left", "right"):
            ok = replace(CRAFTER, **{"upper_%s_break_mm" % side: ah + 1, "upper_%s_inset_mm" % side: 500})
            self.assertEqual(ok.upper_walls, (side,))
            # The arch corner nearest the slope is just inside the plane.
            w = ok.finished_size[0]
            x = 0 if side == "left" else w
            self.assertGreater(ok.upper_wall_distance(side, x, ah), 0)
        # The other side's slope may not reach its arch either (break just under the arch top).
        for side in ("left", "right"):
            with self.assertRaisesRegex(ValueError, "Obstruction outside"):
                replace(CRAFTER, **{"upper_%s_break_mm" % side: ah - 1, "upper_%s_inset_mm" % side: 500})

    def test_obstruction_must_stay_inside_the_sloped_wall(self):
        high = KeepOut("cab_light", "obstruction", (0, 1000, 1700), (40, 100, 50))  # in the leaning corner
        with self.assertRaisesRegex(ValueError, "Obstruction outside"):
            replace(SLOPED, keepouts=(high,))
        replace(CRAFTER, keepouts=(high,))                          # fine without the slope


class Distance(unittest.TestCase):
    def test_plane_geometry(self):
        h, w = SLOPED.heights[0], SLOPED.finished_size[0]
        self.assertAlmostEqual(SLOPED.upper_wall_distance("left", 0, 1200), 0, places=9)
        self.assertAlmostEqual(SLOPED.upper_wall_distance("left", 150, h), 0, places=9)
        self.assertAlmostEqual(SLOPED.upper_wall_distance("right", w, 1250), 0, places=9)
        self.assertAlmostEqual(SLOPED.upper_wall_distance("right", w - 120, h), 0, places=9)
        rise = h - 1200
        self.assertAlmostEqual(SLOPED.upper_wall_distance("left", 250, h),
                               100 * rise / math.hypot(rise, 150), places=9)
        self.assertLess(SLOPED.upper_wall_distance("left", 100, h), 0)    # behind the leaning lining
        self.assertGreater(SLOPED.upper_wall_distance("left", 5, 600), 0)  # below the break: no extra limit


class Fit(unittest.TestCase):
    def required_x(self):
        """Smallest wall gap so the worst corner (back top) is exactly t from the slope."""
        top, t = 1000 + 850, SLOPED.tolerance_mm
        rise, inset = SLOPED.heights[0] - 1200, 150
        return (t * math.hypot(rise, inset) + (top - 1200) * inset) / rise

    def test_cabinet_under_the_slope_fits_exactly_at_the_tolerance(self):
        x = self.required_x()
        arr = build_arrangement(left_cabinet(x), SLOPED)
        gaps = arr.fit["clearance_to_inset_planes_mm"]
        self.assertAlmostEqual(min(g["upper_left"] for g in gaps.values()), 0, places=6)
        with self.assertRaisesRegex(ArrangementError, "upper left wall"):
            build_arrangement(left_cabinet(x - 0.01), SLOPED)
        # The same cabinet against the vertical wall of the /1 envelope fits at 5 mm.
        build_arrangement(left_cabinet(5), CRAFTER)
        with self.assertRaisesRegex(ArrangementError, "upper left wall"):
            build_arrangement(left_cabinet(5), SLOPED)

    def test_low_furniture_is_unaffected_by_the_slope(self):
        build_arrangement(left_cabinet(5, z=5), replace(SLOPED, upper_left_break_mm=1000))   # top 855 < break

    def test_live_plan_carries_editable_wall_parameters(self):
        request = {"arrangement": {"schema_version": "vandesign.arrangement/1", "instances": [
            dict(instance_id="kitchen.left", module="cabinet", param_prefix="K1", spec=CABINET,
                 position_mm=[self.required_x() + 1, 2800, 1000], quarter_turns=1)]},
            "envelope": json.loads(SLOPED.to_json()),
            "edits": [{"parameter": "Env_Upper_Left_Inset", "value_mm": 400, "expect": "refused"}]}
        plan = plan_request(request)
        names = expected_evidence(plan)["parameter_names"]
        for name in ("Env_Upper_Left_Break", "Env_Upper_Left_Inset", "Env_Upper_Right_Break",
                     "Env_Upper_Right_Inset"):
            self.assertIn(name, names)
        self.assertIn("upper left wall", plan.edits[0].preview["reason"])


if __name__ == "__main__":
    unittest.main()
