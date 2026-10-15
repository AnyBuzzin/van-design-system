import json
import os
import unittest

from _helpers import AUTOMATION, DESIGN, job
from vdrunner.schema import ALL_COMMANDS, JobSchemaError, is_mutating, steps_of, validate_job


class SchemaTests(unittest.TestCase):
    def test_minimal_valid_jobs(self):
        validate_job(job("ping", target=None))
        validate_job(job("inspect_design", target=None))
        validate_job(job("measure", {"expect": {"verdict": "PASS", "pass_count": 59, "params_mm": {"Cab_Shelf_Length": 1175.4}}}))
        validate_job(job("set_parameter", {"name": "Cab_Dado_Depth", "value": 10, "unit": "mm"}))
        validate_job(job("restore_parameter", {"name": "Cab_Dado_Depth"}))
        validate_job(job("audit_cuts", {"expect": {"features_passed": 2}}))

    def test_rejects_unknown_command_and_keys(self):
        for bad in (job("python_exec", {"code": "x"}), job("measure", {"bogus": 1}),
                    dict(job("ping", target=None), extra=1), job("delete_body", {})):
            with self.assertRaises(JobSchemaError):
                validate_job(bad)

    def test_requires_target_for_design_commands(self):
        for cmd, args in (("measure", {}), ("set_parameter", {"name": "Cab_Ply", "value": 15, "unit": "mm"}), ("audit_cuts", {})):
            with self.assertRaises(JobSchemaError):
                validate_job(job(cmd, args, target=None))

    def test_parameter_and_unit_validation(self):
        for args in ({"name": "Width", "value": 10, "unit": "mm"},          # not a Cab_* name
                     {"name": "Cab_Ply", "value": 10, "unit": "in"},        # unsupported unit
                     {"name": "Cab_Ply", "value": -1, "unit": "mm"},        # non-positive
                     {"name": "Cab_Ply", "value": "10", "unit": "mm"},      # string, not coerced
                     {"name": "Cab_Ply", "value": float("nan"), "unit": "mm"},
                     {"name": "Cab_Ply", "value": True, "unit": "mm"}):
            with self.assertRaises(JobSchemaError, msg=args):
                validate_job(job("set_parameter", args))

    def test_bad_job_id_and_schema(self):
        with self.assertRaises(JobSchemaError):
            validate_job(job("ping", target=None, job_id="../escape"))
        j = job("ping", target=None)
        j["schema"] = "other/9"
        with self.assertRaises(JobSchemaError):
            validate_job(j)

    def test_batch_rules(self):
        steps = [{"command": "measure"}, {"command": "set_parameter", "args": {"name": "Cab_Dado_Depth", "value": 10, "unit": "mm"}},
                 {"command": "restore_parameter", "args": {"name": "Cab_Dado_Depth"}}, {"command": "audit_cuts"}]
        j = validate_job(job("run_test_batch", {"steps": steps}))
        self.assertTrue(is_mutating(j))
        self.assertEqual([s["command"] for s in steps_of(j)], [s["command"] for s in steps])
        for bad_steps in ([], [{"command": "run_test_batch", "args": {"steps": []}}], [{"command": "ping"}],
                          [{"command": "measure", "args": {"expect": {"verdict": "MAYBE"}}}]):
            with self.assertRaises(JobSchemaError):
                validate_job(job("run_test_batch", {"steps": bad_steps}))
        self.assertFalse(is_mutating(validate_job(job("run_test_batch", {"steps": [{"command": "measure"}]}))))

    def test_example_jobs_and_json_schema_file_are_valid(self):
        ex = os.path.join(AUTOMATION, "jobs", "examples")
        names = sorted(n for n in os.listdir(ex) if n.endswith(".json"))
        self.assertTrue(names)
        for n in names:
            with open(os.path.join(ex, n)) as fh:
                j = json.load(fh)
            j.setdefault("job_id", "example-job")
            if j["command"] not in ("ping", "inspect_design"):
                j["target"] = {"design_id": DESIGN}
            validate_job(j)
        with open(os.path.join(AUTOMATION, "schema", "vdrunner-job-v1.schema.json")) as fh:
            doc = json.load(fh)
        self.assertEqual(sorted(doc["properties"]["command"]["enum"]),
                         sorted(ALL_COMMANDS))


if __name__ == "__main__":
    unittest.main()
