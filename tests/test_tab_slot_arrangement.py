"""Tab-and-slot cabinets in arrangements: world frames and assembled joints."""
import itertools
import json
import os
import tempfile
import unittest

from vandesign.arrangement import ArrangementError, Instance, build_arrangement
from vandesign.arrangement_job import plan_request
from vandesign.manufacturing.dxf import export_profiles
from vandesign.manufacturing.placement import arrangement_profiles, place_point
from vandesign.manufacturing.profile import ProfileError, contains_world_point, world_box

CAB = {"schema_version": "0.2", "module": "cabinet@1", "variant": "base", "profile_version": 1,
       "parameters": {"width_mm": 1100, "ply_mm": 17.6}}
JOINERY = {"sheet": {"name": "birch", "nominal_mm": 18, "measured_mm": 17.6}, "clearance_mm": 0.2,
           "tabs_per_edge": 2, "tab_width_mm": None, "tool_diameter_mm": 6}
BED = {"module": "bed-platform@1", "schema_version": "vandesign.bed-platform/1",
       "parameters": {"height_mm": 700.0, "length_mm": 1900.0, "ply_mm": 18.0, "width_mm": 1400.0}}


def tabbed(k, iid="k", prefix="K", pos=(1000, 1000, 0), spec=None):
    return Instance(iid, "cabinet_tab_slot", prefix, spec or {"cabinet": CAB, "joinery": JOINERY}, pos, k)


class Frames(unittest.TestCase):
    def test_box_model_frames_reproduce_every_panel_for_all_turns(self):
        for k in range(4):
            arr = build_arrangement((Instance("c", "cabinet", "C", dict(CAB, parameters={"width_mm": 1100}),
                                              (1000, 1000, 0), k),))
            env = arr.assembly.parameters.resolve()
            profs, _ = arrangement_profiles(arr, tool_diameter=6)
            for p in profs:
                b = next(q for q in arr.assembly.panels if q.stable_id == p.panel_id).box.resolve(env)
                self.assertEqual(world_box(p), (b.lo, b.hi), (k, p.panel_id))

    def test_grooves_sit_on_the_inner_faces_for_all_turns(self):
        for k in range(4):
            arr = build_arrangement((Instance("c", "cabinet", "C", dict(CAB, parameters={"width_mm": 1100}),
                                              (1000, 1000, 0), k),))
            env = arr.assembly.parameters.resolve()
            profs = {p.panel_id: p for p in arrangement_profiles(arr, tool_diameter=6)[0]}
            boxes = {p.stable_id: p.box.resolve(env) for p in arr.assembly.panels}
            for op in arr.assembly.operations:
                cut, side = op.cut.resolve(env), profs[op.target_panel_id]
                centre = tuple((a + b) / 2 for a, b in zip(cut.lo, cut.hi))
                self.assertIs(contains_world_point(side, centre), False, (k, op.operation_id))
                # 0.5 mm beyond the groove floor, inside the side panel.
                panel = boxes[op.target_panel_id]
                axis = min(range(3), key=lambda i: panel.size[i])
                floor = cut.lo[axis] if abs(cut.hi[axis] - panel.hi[axis]) < 1e-6 else cut.hi[axis]
                inward = -0.5 if floor == cut.lo[axis] else 0.5
                probe = list(centre); probe[axis] = floor + inward
                self.assertIs(contains_world_point(side, tuple(probe)), True, (k, op.operation_id))


class AssembledJoints(unittest.TestCase):
    def placed(self, k):
        arr = build_arrangement((tabbed(k),))
        env = arr.assembly.parameters.resolve()
        profs, joints = arrangement_profiles(arr, tool_diameter=6)
        w, d = env["K_Cab_Width"], env["K_Cab_Ply"] + env["K_Cab_Depth"]
        pos = (env["K_Pos_X"], env["K_Pos_Y"], env["K_Pos_Z"])
        world = lambda p: place_point(p, k, w, d, pos)  # noqa: E731
        return {p.panel_id: p for p in profs}, joints["k"], world

    def test_tabs_seat_in_slots_in_world_for_all_turns(self):
        for k in range(4):
            profs, results, world = self.placed(k)
            self.assertEqual(len(results), 4)
            for r in results:
                inserter, receiver = profs["k." + r.joint.inserter], profs["k." + r.joint.receiver]
                for tab, slot in zip(r.tabs, r.slots):
                    centre = tuple((a + b) / 2 for a, b in zip(tab.lo, tab.hi))
                    self.assertIs(contains_world_point(inserter, world(centre)), True, (k, r.joint))
                    self.assertIs(contains_world_point(receiver, world(centre)), False, (k, r.joint))
                    beyond = list(centre); beyond[1] = slot.hi[1] + 0.5           # past the clearance
                    self.assertIs(contains_world_point(receiver, world(tuple(beyond))), True)
                    self.assertIs(contains_world_point(inserter, world(tuple(beyond))), False)
                    gap = list(centre); gap[1] = tab.lo[1] - 3.0                  # between/beside tabs
                    self.assertIs(contains_world_point(inserter, world(tuple(gap))), False)

    @staticmethod
    def joint_zone(a, b):
        """World region where two placed parts' bounds overlap (the joint)."""
        (alo, ahi), (blo, bhi) = world_box(a), world_box(b)
        return [(max(x0, y0), min(x1, y1)) for x0, x1, y0, y1 in zip(alo, ahi, blo, bhi)]

    def shared_samples(self, a, b, n=24):
        zone = self.joint_zone(a, b)
        self.assertTrue(all(hi > lo for lo, hi in zone))
        steps = [(i + 0.5) / n for i in range(n)]
        return [p for f in itertools.product(steps, repeat=3)
                for p in (tuple(lo + fi * (hi - lo) for (lo, hi), fi in zip(zone, f)),)
                if contains_world_point(a, p) is True and contains_world_point(b, p) is True]

    def test_no_point_is_solid_in_two_panels(self):
        for k in (0, 1):
            profs, results, _ = self.placed(k)
            for r in results:
                a, b = profs["k." + r.joint.inserter], profs["k." + r.joint.receiver]
                self.assertEqual(self.shared_samples(a, b), [], (k, r.joint))

    def test_overlap_check_detects_a_joint_without_notches(self):
        from dataclasses import replace
        from vandesign.manufacturing.profile import polygon_loop, rect_vertices
        profs, results, _ = self.placed(1)
        r = results[0]
        a, b = profs["k." + r.joint.inserter], profs["k." + r.joint.receiver]
        (a0, b0), (a1, b1) = a.outline.bounds
        solid_edge = replace(a, outline=polygon_loop(rect_vertices(a0, b0, a1, b1), waste_inside=False))
        self.assertGreater(len(self.shared_samples(solid_edge, b)), 0)

    def test_instance_edits_regenerate_the_joinery(self):
        arr = build_arrangement((tabbed(0),))
        base = {p.panel_id: p for p in arrangement_profiles(arr, tool_diameter=6)[0]}
        wide = {p.panel_id: p for p in arrangement_profiles(arr, {"K_Cab_Width": 1000}, tool_diameter=6)[0]}
        size = lambda p: [hi - lo for lo, hi in zip(*world_box(p))]  # noqa: E731
        self.assertAlmostEqual(size(base["k.panel.bottom.001"])[0] - size(wide["k.panel.bottom.001"])[0], 100)


class Integration(unittest.TestCase):
    def test_mixed_arrangement_exports_dxf_with_prefixed_ids(self):
        arr = build_arrangement((Instance("bed.rear", "bed", "Bed1", BED, (0, 0, 0), 0),
                                 tabbed(1, pos=(1600, 0, 0))))
        profs, joints = arrangement_profiles(arr, tool_diameter=6)
        self.assertEqual(len(profs), 3 + 8)
        self.assertEqual(sum(p.reliefs for p in profs if p.panel_id.startswith("k.")), 36)
        with tempfile.TemporaryDirectory() as d:
            files = export_profiles(profs, d)
            self.assertIn("k.panel.bottom.001.dxf", [os.path.basename(f) for f in files])

    def test_refusals(self):
        with self.assertRaisesRegex(ArrangementError, "measured sheet thickness"):
            build_arrangement((tabbed(0, spec={"cabinet": dict(CAB, parameters={"width_mm": 1100}),
                                              "joinery": JOINERY}),))
        for bad in ({"cabinet": CAB}, {"cabinet": CAB, "joinery": dict(JOINERY, colour="oak")},
                    {"cabinet": CAB, "joinery": dict(JOINERY, tabs_per_edge=0)},
                    {"cabinet": CAB, "joinery": dict(JOINERY, sheet=dict(JOINERY["sheet"], measured_mm=20))}):
            with self.assertRaises(ArrangementError):
                build_arrangement((tabbed(0, spec=bad),))
        arr = build_arrangement((tabbed(0),))
        with self.assertRaisesRegex(ProfileError, "differs from the export tool"):
            arrangement_profiles(arr, tool_diameter=8)
        from vandesign.schemas.envelope_spec import EnvelopeSpec
        request = {"arrangement": {"schema_version": "vandesign.arrangement/1", "instances": [
            dict(instance_id="k", module="cabinet_tab_slot", param_prefix="K", spec={"cabinet": CAB, "joinery": JOINERY},
                 position_mm=[600, 1500, 5], quarter_turns=0)]},
            "envelope": json.loads(EnvelopeSpec().to_json()), "edits": []}
        with self.assertRaisesRegex(ArrangementError, "oriented profile Fusion builder"):
            plan_request(request)                                       # live builds refuse it
        self.assertEqual(plan_request(request, allow_profile_modules=True).arrangement.fit["outcome"], "PASS")


if __name__ == "__main__":
    unittest.main()
