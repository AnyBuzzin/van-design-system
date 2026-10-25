import ast
import json
import os
import unittest
import zipfile

from _helpers import AUTOMATION, TmpDirCase, cfg, job
from vdrunner.evidence import package
from vdrunner.policy import PolicyError, check_parameter_edit, format_mm, is_plain_mm_expression, load_config
from vdrunner.queue import JobQueue


class PolicyTests(unittest.TestCase):
    def test_format_and_plain_expression(self):
        self.assertEqual(format_mm(10), "10 mm")
        self.assertEqual(format_mm(7.25), "7.25 mm")
        self.assertTrue(is_plain_mm_expression("6 mm"))
        for e in ("( Cab_Width - 2 * Cab_Ply )", "6", "6 in", "abc mm", ""):
            self.assertFalse(is_plain_mm_expression(e), e)

    def test_parameter_edit_checks(self):
        c = cfg()
        self.assertEqual(check_parameter_edit(c, "Cab_Dado_Depth", 10, "6 mm"), "10 mm")
        for args in (("Cab_Back", 5, "6 mm"), ("Cab_Dado_Depth", 0.5, "6 mm"), ("Cab_Dado_Depth", 10, "( Cab_Ply / 3 )")):
            with self.assertRaises(PolicyError):
                check_parameter_edit(c, *args)


class ConfigAndEvidenceTests(TmpDirCase):
    def test_load_config_requires_core_keys(self):
        p = os.path.join(self.tmp, "c.json")
        json.dump({"queue_root": "q"}, open(p, "w"))
        with self.assertRaises(PolicyError):
            load_config(p)
        json.dump(cfg(), open(p, "w"))
        self.assertTrue(load_config(p)["allowed_design_ids"])

    def test_package_is_byte_exact_and_refuses_overwrite(self):
        q = JobQueue(os.path.join(self.tmp, "q")).ensure()
        q.submit(job("ping", target=None)); q.claim("job-001")
        ev = os.path.join(q.result_dir("job-001"), "evidence")
        os.makedirs(ev)
        open(os.path.join(ev, "report.txt"), "wb").write(b"original \x00 bytes")
        q.finish("job-001", {"outcome": "PASS"})
        out = os.path.join(self.tmp, "e.zip")
        info = package(q, ["job-001"], out)
        with zipfile.ZipFile(out) as z:
            self.assertEqual(z.read("jobs/job-001/evidence/report.txt"), b"original \x00 bytes")
            man = json.loads(z.read("MANIFEST.sha256.json"))
        self.assertEqual(len(man["files"]), info["files"])
        with self.assertRaises(FileExistsError):
            package(q, ["job-001"], out)


class LayeringTests(unittest.TestCase):
    def test_pure_core_never_imports_adsk(self):
        core = os.path.join(AUTOMATION, "vdrunner")
        for n in os.listdir(core):
            if n.endswith(".py"):
                tree = ast.parse(open(os.path.join(core, n), encoding="utf-8").read())
                for node in ast.walk(tree):
                    names = [a.name for a in node.names] if isinstance(node, (ast.Import, ast.ImportFrom)) else []
                    mod = getattr(node, "module", None) or ""
                    self.assertFalse(any(x.split(".")[0] == "adsk" for x in names + [mod]), n)

    def test_addin_has_no_forbidden_operations(self):
        """Cloud save is isolated to the guarded demo lifecycle; no arbitrary code."""
        forbidden = ("deleteMe", ".save(", "saveAs", "exportManager", "exec(", "eval(", "subprocess", "os.system",
                     ".compile(")
        for n in ("VanDesignRunner.py", "fusion_backend.py"):
            src = open(os.path.join(AUTOMATION, "VanDesignRunner", n), encoding="utf-8").read()
            for f in forbidden:
                self.assertNotIn(f, src, "%s contains %s" % (n, f))
        # G4: the stored spec is written in exactly ONE place (store_spec_text, used by update_width)
        backend = open(os.path.join(AUTOMATION, "VanDesignRunner", "fusion_backend.py"), encoding="utf-8").read()
        self.assertEqual(backend.count("store_spec_json("), 1)
        self.assertNotIn("store_spec_json", open(os.path.join(AUTOMATION, "VanDesignRunner", "VanDesignRunner.py"), encoding="utf-8").read())
        lifecycle = open(os.path.join(AUTOMATION, "VanDesignRunner", "demo_workflow.py"), encoding="utf-8").read()
        for f in ("deleteMe", ".save(", "exportManager", "exec(", "eval(", "subprocess", "os.system"):
            self.assertNotIn(f, lifecycle)
        # Exactly the original owned-demo save and Issue60 sole-document first save.
        save_sites=[]
        for function in ast.parse(lifecycle).body:
            if isinstance(function,ast.FunctionDef):
                for call in ast.walk(function):
                    if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='saveAs':
                        save_sites.append((function.name,ast.unparse(call.func.value)))
        self.assertCountEqual(save_sites,[('execute','doc'),('phase_a_persistence','doc')])


if __name__ == "__main__":
    unittest.main()
