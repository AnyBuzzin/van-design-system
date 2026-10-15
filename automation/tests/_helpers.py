import os
import shutil
import sys
import tempfile
import unittest

AUTOMATION = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if AUTOMATION not in sys.path:
    sys.path.insert(0, AUTOMATION)

from vdrunner import JOB_SCHEMA_ID  # noqa: E402

DESIGN = "urn:adsk.wipprod:dm.lineage:DISPOSABLE-TEST"
PROTECTED = "urn:adsk.wipprod:dm.lineage:PROTECTED-G2"
OTHER = "urn:adsk.wipprod:dm.lineage:OTHER"


def cfg(queue_root="q"):
    return {"queue_root": queue_root, "g3_script_dir": "g3", "audit_script": "a.py",
            "allowed_design_ids": [{"design_id": DESIGN, "document_name": "v5-auto-demo"}],
            "protected_design_ids": [{"design_id": PROTECTED, "document_name": "v5-smoke-test"}],
            "parameter_bounds_mm": {"Cab_Dado_Depth": [1, 20], "Cab_Ply": [6, 40], "Cab_Width": [200, 2500]}}


def job(command, args=None, target=DESIGN, job_id="job-001", **extra):
    j = {"schema": JOB_SCHEMA_ID, "job_id": job_id, "command": command, "args": args or {}}
    if target:
        j["target"] = {"design_id": target}
    j.update(extra)
    return j


class FakeBackend:
    """In-memory stand-in for FusionBackend: base cabinet arithmetic + scripted faults."""

    def __init__(self, design_id=DESIGN, name="v5-auto-demo"):
        self.ident = {"design_id": design_id, "document_name": name, "is_saved": True, "is_modified": False,
                      "fusion_version": "fake"}
        self.params = {"Cab_Width": "1200 mm", "Cab_Ply": "18 mm", "Cab_Dado_Depth": "6 mm",
                       "Cab_Shelf_Length": "( Cab_Width - 2 * Cab_Ply )"}
        self.fail_ids = []
        self.unknown_ids = []
        self.counts = {"user_parameters": 16, "root_occurrences": 8, "all_components": 9, "timeline_items": 28}
        self.stored_unchanged = True
        self.audit_restored = True
        self.raise_on = None
        self.set_calls = []
        self.measure_calls = 0
        self.switch_identity_after_measure = None

    def _v(self, n):
        return float(self.params[n].split()[0])

    def identity(self):
        return dict(self.ident)

    def inspect(self):
        return {"identity": self.identity(), "params": dict(self.params)}

    def measure(self, out_dir, label):
        if self.raise_on == "measure":
            raise RuntimeError("simulated Fusion API error")
        self.measure_calls += 1
        os.makedirs(out_dir, exist_ok=True)
        open(os.path.join(out_dir, "report.txt"), "w").write("fake report %s" % label)
        w, p, d = self._v("Cab_Width"), self._v("Cab_Ply"), self._v("Cab_Dado_Depth")
        fails = list(self.fail_ids)
        if self.switch_identity_after_measure:
            self.ident["design_id"] = self.switch_identity_after_measure
        return {"verdict": "FAIL" if fails else ("UNKNOWN" if self.unknown_ids else "PASS"),
                "counts": {"PASS": 59 - len(fails) - len(self.unknown_ids), "FAIL": len(fails), "UNKNOWN": len(self.unknown_ids)},
                "total": 59, "fail_ids": fails, "unknown_ids": list(self.unknown_ids),
                "params_mm": {"Cab_Width": w, "Cab_Ply": p, "Cab_Dado_Depth": d,
                              "Cab_Shelf_Length": round(w - 2 * p + 2 * d - 0.6, 6)},
                "design_counts": dict(self.counts), "design_spec_hash": "0" * 64,
                "stored_unchanged": self.stored_unchanged}

    def get_parameter(self, name):
        if name not in self.params:
            return None
        e = self.params[name]
        try:
            return {"expression": e, "value_mm": self._v(name)}
        except ValueError:
            return {"expression": e, "value_mm": 0.0}

    def set_parameter_expression(self, name, expr):
        if self.raise_on == "set":
            raise RuntimeError("simulated failure while setting")
        self.set_calls.append((name, expr))
        self.params[name] = expr
        return self._v(name)

    def audit(self, out_dir, label):
        return {"overall": "PASS" if self.audit_restored else "FAIL", "features_passed": 2, "features_total": 2,
                "timeline_restored": self.audit_restored, "counts_equal": True}


class TmpDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vdrunner-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
