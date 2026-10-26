"""Generic arrangement requests: everything validated and previewed before CAD writes."""
import json
import os
import tempfile
import unittest
from copy import deepcopy

from vandesign.arrangement import SCHEMA, ArrangementError
from vandesign.arrangement_job import plan_request, preview_values
from vandesign.manufacturing.assembly import assembly_profiles
from vandesign.manufacturing.dxf import export_profiles
from vandesign.schemas.envelope_spec import EnvelopeSpec
from vandesign.core.geometry import Box
from vandesign.modules.test_envelope import preview_lined_fit
from vandesign.verification.readback import COORDINATE_READBACK_MM

CABINET = {"schema_version": "0.2", "module": "cabinet@1", "variant": "base",
           "profile_version": 1, "parameters": {"width_mm": 1100}}
BED = {"module": "bed-platform@1", "schema_version": "vandesign.bed-platform/1",
       "parameters": {"height_mm": 700.0, "length_mm": 1900.0, "ply_mm": 18.0, "width_mm": 1400.0}}
STORAGE = {"module": "storage-box@1", "schema_version": "vandesign.storage-box/1",
           "parameters": {"height_mm": 250.0, "length_mm": 800.0, "ply_mm": 18.0, "width_mm": 600.0}}
CRAFTER = EnvelopeSpec(bare_width_mm=1832, bare_length_mm=4606, bare_height_mm=1961, lining_mm=18,
                       tolerance_mm=5, bare_between_arches_mm=1380, arch_length_mm=800,
                       arch_height_mm=300, arch_y_mm=2000,
                       provenance="TEST ONLY: published Crafter CR35 LWB; arches ASSUMED")


def instance(iid, module, prefix, spec, pos, k):
    return dict(instance_id=iid, module=module, param_prefix=prefix, spec=spec,
                position_mm=list(pos), quarter_turns=k)


def request(edits=(), **extra):
    req = {"arrangement": {"schema_version": SCHEMA, "instances": [
               instance("bed.rear", "bed", "Bed1", BED, (213, 5, 5), 0),
               instance("storage.under", "storage_box", "Box1", STORAGE, (600, 400, 5), 0),
               instance("kitchen.left", "cabinet", "K1", CABINET, (5, 2800, 5), 1),
               instance("kitchen.right", "cabinet", "K2", CABINET, (1223, 2800, 5), 3)]},
           "envelope": json.loads(CRAFTER.to_json()), "edits": list(edits)}
    req.update(extra)
    return req


EDIT_OK = {"parameter": "K1_Cab_Width", "value_mm": 1000, "expect": "pass"}
INTO_ARCH = {"parameter": "K1_Pos_Y", "value_mm": 2100, "expect": "refused"}


class PlanRequests(unittest.TestCase):
    def test_captured_rotated_back_readback_keeps_inset_without_rounding(self):
        plan = plan_request(request([EDIT_OK, INTO_ARCH], tool_diameter_mm=6))
        asm = plan.arrangement.assembly
        values = {p.name: p.value_mm for p in asm.parameters.base()}
        # Exact differing base values from failed live job vd-20261026T143054-eef89a.
        values.update(K1_Cab_Back=6.000000000000001, K1_Cab_Gap=3.0000000000000004,
                      K1_Cab_Dado_Depth=6.000000000000001, K2_Cab_Back=6.000000000000001,
                      K2_Cab_Gap=3.0000000000000004, K2_Cab_Dado_Depth=6.000000000000001,
                      Env_Bare_Width=1832.0000000000002, Env_Bare_Height=1961.0000000000002,
                      K1_Cab_Width=1000.0)
        before = deepcopy(values)
        self.assertEqual(preview_values(plan.arrangement, plan.envelope, values)['outcome'], 'PASS')
        env = asm.parameters.resolve(values)
        fit = preview_lined_fit(asm, plan.envelope, env)
        gap = fit['clearance_to_inset_planes_mm']['kitchen.left.panel.back.001']['left']
        self.assertEqual(gap, 4.999999999999999 - 5.0)
        self.assertEqual(fit['margin_mm'], 5.0)
        self.assertEqual(values, before)
        self.assertEqual(preview_values(plan.arrangement, plan.envelope,
                         dict(values, K1_Pos_X=5.0-1e-6))['outcome'], 'REFUSED')
        self.assertEqual(preview_values(plan.arrangement, plan.envelope,
                         dict(values, K1_Pos_Y=2100.0))['outcome'], 'REFUSED')

    def test_all_inset_planes_accept_only_coordinate_noise(self):
        plan = plan_request(request())
        asm = plan.arrangement.assembly
        env = asm.parameters.resolve()
        boxes = {p.stable_id: p.box.resolve(env) for p in asm.panels}
        sid = 'kitchen.left.panel.back.001'
        limits = plan.envelope.finished_size
        for axis in range(3):
            for side in ('low', 'high'):
                for outside in (-1e-6, 0.0, COORDINATE_READBACK_MM/2, 2*COORDINATE_READBACK_MM, 1e-6):
                    with self.subTest(axis=axis, side=side, outside=outside):
                        lo, hi = [10.0]*3, [20.0]*3
                        if side == 'low':lo[axis] = 5.0-outside
                        else:
                            hi[axis] = limits[axis]-5.0+outside
                            lo[axis] = hi[axis]-10.0
                        observed = dict(boxes, **{sid: Box(tuple(lo), tuple(hi))})
                        before = deepcopy(observed)
                        if outside > COORDINATE_READBACK_MM:
                            with self.assertRaisesRegex(ValueError, 'Outside inset'):
                                preview_lined_fit(asm, plan.envelope, env, observed)
                        else:
                            fit = preview_lined_fit(asm, plan.envelope, env, observed)
                            self.assertEqual(fit['outcome'], 'PASS')
                            self.assertEqual(fit['margin_mm'], 5.0)
                        self.assertEqual(observed, before)

    def test_valid_plan_with_pass_and_refused_edits(self):
        plan = plan_request(request([EDIT_OK, INTO_ARCH], tool_diameter_mm=6))
        self.assertEqual(plan.arrangement.fit["outcome"], "PASS")
        self.assertEqual([e.preview["outcome"] for e in plan.edits], ["PASS", "REFUSED"])
        self.assertIn("keep-out", plan.edits[1].preview["reason"])
        self.assertEqual(plan.tool_diameter_mm, 6.0)

    def test_expectation_mismatch_refuses_the_whole_job(self):
        with self.assertRaisesRegex(ArrangementError, "expected pass but preview gives REFUSED"):
            plan_request(request([dict(INTO_ARCH, expect="pass")]))
        with self.assertRaisesRegex(ArrangementError, "expected refused but preview gives PASS"):
            plan_request(request([dict(EDIT_OK, expect="refused")]))

    def test_collision_edit_is_refused_by_preview(self):
        # Right kitchen moved onto the left one: shared material.
        plan = plan_request(request([{"parameter": "K2_Pos_X", "value_mm": 300, "expect": "refused"}]))
        self.assertIn("share material", plan.edits[0].preview["reason"])

    def test_malformed_requests_refused(self):
        bad = [
            {"arrangement": {}, "envelope": {}},                                   # no edits
            dict(request(), script="x.py"),                                        # unknown key
            request([dict(EDIT_OK, parameter="Cab_Width")]),                       # not namespaced
            request([dict(EDIT_OK, parameter="K1_Cab_Shelf_Length")]),             # derived parameter
            request([dict(EDIT_OK, value_mm=float("nan"))]),
            request([dict(EDIT_OK, value_mm=1100)]),                               # no change
            request([dict(EDIT_OK, expect="maybe")]),
            request([dict(EDIT_OK, colour="oak")]),
            request([EDIT_OK] * 7),
            request(tool_diameter_mm=0),
            request(tool_diameter_mm=True),
        ]
        for req in bad:
            with self.assertRaises(ArrangementError, msg=str(req)[:120]):
                plan_request(req)
        broken = request()
        broken["envelope"]["parameters"]["lining_mm"] = "18"
        with self.assertRaisesRegex(ArrangementError, "envelope"):
            plan_request(broken)

    def test_preview_follows_current_values_not_only_the_plan(self):
        plan = plan_request(request())
        base = {p.name: p.value_mm for p in plan.arrangement.assembly.parameters.base()}
        self.assertEqual(preview_values(plan.arrangement, plan.envelope, base)["outcome"], "PASS")
        moved = dict(base, K1_Pos_X=1300)                                      # into K2
        self.assertEqual(preview_values(plan.arrangement, plan.envelope, moved)["outcome"], "REFUSED")

    def test_shipped_example_request_plans(self):
        path = os.path.join(os.path.dirname(__file__), "..", "automation", "jobs", "requests",
                            "arrangement_request_crafter.json")
        with open(path, encoding="utf-8") as fh:
            example = json.load(fh)
        self.assertEqual(example, request([EDIT_OK, INTO_ARCH], tool_diameter_mm=6))
        plan = plan_request(example)
        self.assertEqual(len(plan.arrangement.instances), 4)
        self.assertEqual(sum(i.quarter_turns != 0 for i in plan.arrangement.instances), 2)

    def test_expected_evidence_is_derived_from_the_model_and_request(self):
        from vandesign.arrangement_job import expected_evidence
        from vandesign.verification.model_source import ModelGeometrySource
        from vandesign.verification.validate import validate
        plan = plan_request(request([EDIT_OK, INTO_ARCH]))
        ev = expected_evidence(plan)
        asm = plan.arrangement.assembly
        self.assertEqual([s["label"] for s in ev["stages"]],
                         ["baseline", "edit_K1_Cab_Width", "restore_K1_Cab_Width", "after_refusal_K1_Pos_Y"])
        self.assertEqual(ev["stages"][1]["parameters_mm"]["K1_Cab_Width"], 1000.0)
        self.assertNotEqual(ev["stages"][1]["parameters_mm"]["K1_Cab_Shelf_Length"],
                            ev["stages"][0]["parameters_mm"]["K1_Cab_Shelf_Length"])   # derived follow
        self.assertEqual(ev["body_ids"], sorted(p.stable_id for p in asm.panels))
        ideal = {c.check_id for c in validate(asm, ModelGeometrySource(asm)).checks}
        self.assertTrue(ideal <= set(ev["required_checks"]))
        for extra in ("furniture_interference", "inventory", "lined_clearances", "instances.no_shared_material",
                      "reference.arch.left.interference"):
            self.assertIn(extra, ev["required_checks"])
        self.assertTrue(all(op.operation_id + ".affected_body_ownership" in ev["required_checks"]
                            for op in asm.operations))
        self.assertTrue(set(ev["numeric_checks"]) <= set(ev["required_checks"]))
        self.assertTrue(any(c.endswith(".volume") for c in ev["numeric_checks"]))
        self.assertEqual(ev["inventory"]["timeline_items"], 3 * len(asm.panels) + 2 * len(asm.operations))
        self.assertEqual(json.loads(json.dumps(ev)), ev)                      # plain JSON data
        # The ideal model source itself passes every validate() check.
        self.assertTrue(all(c.status == "PASS" for c in validate(asm, ModelGeometrySource(asm)).checks))

    def test_dxf_pack_excludes_reference_geometry(self):
        plan = plan_request(request(tool_diameter_mm=6))
        asm = plan.arrangement.assembly
        profiles = assembly_profiles(asm, tool_diameter=6)
        furniture = [p.stable_id for p in asm.panels if p.material_ref != "reference_only"]
        self.assertEqual([p.panel_id for p in profiles], furniture)
        with tempfile.TemporaryDirectory() as d:
            files = export_profiles(profiles, d)
            self.assertEqual(len(files), len(furniture) + 1)
            self.assertFalse(any(os.path.basename(f).startswith("reference.") for f in files))


if __name__ == "__main__":
    unittest.main()
