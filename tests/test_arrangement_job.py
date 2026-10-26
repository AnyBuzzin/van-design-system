"""Generic arrangement requests: everything validated and previewed before CAD writes."""
import json
import os
import tempfile
import unittest

from vandesign.arrangement import SCHEMA, ArrangementError
from vandesign.arrangement_job import plan_request, preview_values
from vandesign.manufacturing.assembly import assembly_profiles
from vandesign.manufacturing.dxf import export_profiles
from vandesign.schemas.envelope_spec import EnvelopeSpec

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
