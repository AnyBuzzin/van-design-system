"""Real canonical planning + fake-backend safety orchestration, NOT CAD evidence."""
import copy
import json
import os
import unittest
from unittest.mock import patch

from _helpers import DESIGN, OTHER, PROTECTED, TmpDirCase, cfg, job
from test_g4_width_update import FakeCabinet
from vdrunner.executor import Executor
from vdrunner.journal import RestoreJournal
from vdrunner.schema import JobSchemaError, is_mutating, validate_job
from vdrunner.shelf_change import JOURNAL_KEY, equivalent, plan_shelf_count_change
from vdrunner.width_change import _boxes, expected_expressions


class ShelfCabinet(FakeCabinet):
    def __init__(self):
        super().__init__()
        self.ident["version_number"] = 1
        self.actions = []
        self.receipt = True
        self.recovering = False
        self.started = False

    def shelf_state(self):
        st = self.cabinet_state()
        for p in st["live_params"].values(): p["unit"] = "mm"
        st.update(ownership_verified=self.receipt, identity=self.identity(),
                  inventory={"live_params": st["live_params"], "geometry": _boxes(self.asm, self._env())})
        return st

    def begin_shelf_regeneration(self, new_text):
        self.actions.append("prepare")
        return self

    def rebuild(self, text):
        ds = self.g3["design_spec"].load_design_spec(text)
        self.asm = self.g3["variants"].build_variant(ds.resolved_params, ds.profile)
        self.exprs = {n: e.replace("(", "( ").replace(")", " )")
                      for n,e in expected_expressions(self.g3,self.asm).items()}
        self.stored = text
        self.timeline = 3*len(self.asm.panels)+2*len(self.asm.operations)

    def apply(self, text):
        self.started = True
        self.actions.append("apply")
        if self.fault == "partial":
            self.exprs.clear()
            raise RuntimeError("controlled partial-construction failure")
        self.rebuild(text)
        if self.fault == "identity":
            self.ident["design_id"] = OTHER

    def restore(self, text):
        self.actions.append("restore")
        self.recovering = True
        if self.fault == "recovery_api":
            raise RuntimeError("recovery API unavailable")
        self.rebuild(text)

    def measure(self, out_dir, label):
        m = super().measure(out_dir,label)
        m["design_counts"] = {"user_parameters": len(self.exprs), "root_occurrences": len(self.asm.panels),
                              "all_components": len(self.asm.panels)+1, "timeline_items": self.timeline}
        if self.actions and self.fault in ("geometry", "recovery_api", "recovery_unknown", "recovery_drift") and not self.recovering:
            m.update(verdict="FAIL", counts={"PASS":58,"FAIL":1,"UNKNOWN":0})
        if self.recovering and self.fault == "recovery_unknown":
            m.update(verdict="UNKNOWN", counts={"PASS":58,"FAIL":0,"UNKNOWN":1})
        if self.recovering and self.fault == "recovery_drift":
            self.exprs["Cab_Width"] = "1199 mm"
        return m

    def audit(self, out_dir, label):
        n = len(self.asm.operations)
        result = {"overall":"PASS","features_passed":n,"features_total":n,
                  "timeline_restored":True,"counts_equal":True,
                  "operations": {o.operation_id:"PASS" for o in self.asm.operations}}
        if self.fault == "extra_cut" and not self.recovering and self.actions:
            result["operations"]["dado.unexpected"] = "PASS"
        return result


class PlannerTests(unittest.TestCase):
    def test_preview_adds_shelf_and_two_explicit_cuts(self):
        b = ShelfCabinet()
        before = copy.deepcopy(b.shelf_state())
        p = plan_shelf_count_change(b.g3, before, 2)
        self.assertEqual(p["refusals"], [])
        self.assertEqual(p["geometry_changes"]["panel.shelf.002"]["old"], None)
        self.assertEqual(p["cut_targets"]["dado.shelf2.left"], "panel.left.001")
        self.assertEqual(p["cut_targets"]["dado.shelf2.right"], "panel.right.001")
        self.assertEqual(p["expected_counts"], {"user_parameters":18,"root_occurrences":9,"all_components":10,"timeline_items":35})
        self.assertEqual(before,b.shelf_state())
        b.rebuild(p["new_stored_text"])
        reverse = plan_shelf_count_change(b.g3,b.shelf_state(),1)
        self.assertEqual(reverse["refusals"], [])
        for name in ("panel.shelf.002","dado.shelf2.left","dado.shelf2.right"):
            self.assertIsNone(reverse["geometry_changes"][name]["new"])
        self.assertEqual(reverse["new_design_spec_hash"],p["old_design_spec_hash"])

    def test_bad_scope_input_and_drift_refused(self):
        for value in (0,3,True,2.0,"2",None,1):
            b = ShelfCabinet()
            self.assertTrue(plan_shelf_count_change(b.g3,b.shelf_state(),value)["refusals"])
        for fault in ("no_receipt","missing_param","extra_param","nan","expression","variant","width"):
            b = ShelfCabinet()
            st = b.shelf_state()
            if fault == "no_receipt": st["ownership_verified"] = False
            elif fault == "missing_param": del st["live_params"]["Cab_Width"]
            elif fault == "extra_param": st["live_params"]["Unknown"] = {}
            elif fault == "nan": st["live_params"]["Cab_Width"]["value_mm"] = float("nan")
            elif fault == "expression": st["live_params"]["Cab_Width"]["expression"] = "1100 mm"
            else:
                raw = json.loads(st["stored_text"])
                if fault == "variant": raw["variant"] = "overhead"
                else: raw["parameters"]["width_mm"] = 1100
                st["stored_text"] = json.dumps(raw)
            self.assertTrue(plan_shelf_count_change(b.g3,st,2)["refusals"],fault)

    def test_schema_and_mutation_classification(self):
        for command in ("preview_shelf_count_change","update_shelf_count"):
            j=job(command,{"new_shelf_count":2})
            validate_job(j)
            self.assertEqual(is_mutating(j),command=="update_shelf_count")
            for value in (0,3,True,2.0,"2"):
                with self.assertRaises(JobSchemaError): validate_job(job(command,{"new_shelf_count":value}))
            with self.assertRaises(JobSchemaError): validate_job(job(command,{"new_shelf_count":2,"expect":{"verdict":"FAIL"}}))
        self.assertTrue(is_mutating(job("run_test_batch",{"steps":[{"command":"update_shelf_count","args":{"new_shelf_count":2}}]})))

    def test_missing_or_nonfinite_measurement_never_equivalent(self):
        for value in (None,float("nan"),float("inf")):
            self.assertFalse(equivalent({"v":value},{"v":value}))


class ExecutionTests(TmpDirCase):
    def execute(self,b,command="update_shelf_count",count=2):
        self.jdir = os.path.join(self.tmp,"journal")
        return Executor(b,cfg(),self.jdir).run(job(command,{"new_shelf_count":count},target=b.ident["design_id"]),self.tmp)

    def test_sequence_and_preview_no_mutation(self):
        b = ShelfCabinet()
        original = b.shelf_state()["inventory"]
        self.assertEqual(self.execute(b,"preview_shelf_count_change")["outcome"],"PASS")
        self.assertEqual(b.actions,[])
        for count in (2,1):
            r=self.execute(b,count=count)
            self.assertEqual(r["outcome"],"PASS",json.dumps(r)[:2500])
            self.assertFalse(RestoreJournal(self.jdir,DESIGN).load()["entries"])
        self.assertEqual(b.shelf_state()["inventory"],original)

    def test_refusals_do_not_prepare_or_mutate(self):
        for scenario in ("unowned","unallowlisted","protected","pending","applied","identity_unknown"):
            b = ShelfCabinet()
            jdir = os.path.join(self.tmp,"journal")
            journal = RestoreJournal(jdir,DESIGN)
            journal.clear("Cab_Width")
            if scenario == "unowned": b.receipt = False
            elif scenario == "unallowlisted": b.ident["design_id"] = OTHER
            elif scenario == "protected": b.ident["design_id"] = PROTECTED
            elif scenario == "identity_unknown": b.ident["version_number"] = None
            else:
                journal.begin_edit("Cab_Width","1200 mm",1200,"1100 mm","old-job")
                journal.mark("Cab_Width",scenario)
            r=self.execute(b)
            self.assertNotEqual(r["outcome"],"PASS",scenario)
            self.assertEqual(b.actions,[],scenario)

    def test_failure_recovers_but_job_still_fails(self):
        for fault in ("partial","geometry","extra_cut"):
            b=ShelfCabinet(); original=b.shelf_state()["inventory"]; b.fault=fault
            r=self.execute(b)
            self.assertEqual(r["outcome"],"FAIL")
            self.assertTrue(r["steps"][0]["recovery"]["verified"],json.dumps(r)[:3000])
            self.assertEqual(b.shelf_state()["inventory"],original)
            self.assertFalse(RestoreJournal(self.jdir,DESIGN).load()["entries"])

    def test_unverified_recovery_blocks_further_mutation(self):
        for fault in ("recovery_api","recovery_unknown","recovery_drift","identity"):
            b=ShelfCabinet(); b.fault=fault
            journal=RestoreJournal(os.path.join(self.tmp,"journal"),DESIGN); journal.clear(JOURNAL_KEY)
            r=self.execute(b)
            self.assertEqual(r["outcome"],"FAIL")
            self.assertFalse(r["steps"][0]["recovery"]["verified"],fault)
            self.assertEqual(journal.entry(JOURNAL_KEY)["state"],"restore_unverified")
            calls=list(b.actions); b.ident["design_id"]=DESIGN
            self.assertEqual(self.execute(b)["outcome"],"REFUSED")
            self.assertEqual(b.actions,calls)

    def test_journal_write_failure_prevents_mutation(self):
        b=ShelfCabinet()
        with patch.object(RestoreJournal,"_save",side_effect=OSError("disk full")):
            r=self.execute(b)
        self.assertEqual(r["outcome"],"FAIL")
        self.assertEqual(b.actions,["prepare"])

    def test_batch_uses_new_structural_baseline(self):
        b=ShelfCabinet()
        steps=[{"command":"measure"}, {"command":"update_shelf_count","args":{"new_shelf_count":2}},
               {"command":"measure"}, {"command":"update_shelf_count","args":{"new_shelf_count":1}}, {"command":"measure"}]
        r=Executor(b,cfg(),os.path.join(self.tmp,"journal")).run(job("run_test_batch",{"steps":steps}),self.tmp)
        self.assertEqual(r["outcome"],"PASS",json.dumps(r)[:3000])
