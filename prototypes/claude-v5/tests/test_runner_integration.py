"""C4: run_cabinet wiring against a fake adapter and mocked adsk (offline; NOT real Fusion).

Each scenario runs in a fresh interpreter.  The fake adapter records every
mutating call so we can prove: bad specs mutate nothing, measure mode never
stores/compiles, and the default build stores the exact legacy G2 text.
"""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

from core_path import SCRIPT_DIR

TESTS = os.path.dirname(os.path.abspath(__file__))
SPECS = os.path.join(os.path.dirname(TESTS), "specs")
LEGACY_HASH = "a0a43e005535b33f069dd786dc847682734819a09bd0803650688bb5e4b0a750"

DRIVER = textwrap.dedent("""
    import json, os, sys, types
    from types import SimpleNamespace as N
    adsk = types.ModuleType('adsk'); adsk.core = types.ModuleType('adsk.core'); adsk.fusion = types.ModuleType('adsk.fusion')
    adsk.fusion.Design = N(cast=lambda x: x)
    sys.modules.update({'adsk': adsk, 'adsk.core': adsk.core, 'adsk.fusion': adsk.fusion})
    sys.path.insert(0, %(tests)r)
    from sim_geometry import SimGeometry
    from vandesign.cad.fusion import runner
    from vandesign.modules.variants import build_variant
    from vandesign.schemas.design_spec import load_design_spec

    cfg = json.loads(%(cfg)r)
    calls = []

    class Fake:
        def __init__(self, design):
            self.stored = cfg.get('stored')
            self.assembly = None
        def has_managed_assembly(self): return cfg.get('stored') is not None or cfg.get('managed_no_spec', False)
        def stored_spec_json(self): return self.stored
        def store_spec_json(self, text): calls.append(('store', text)); self.stored = text
        def compile(self, assembly):
            calls.append(('compile', assembly.assembly_id)); self.assembly = assembly
            if cfg.get('compile_raises'): raise RuntimeError('boom')
        def geometry_source(self):
            asm = self.assembly
            if asm is None:
                d = load_design_spec(self.stored); asm = build_variant(d.resolved_params, d.profile)
            return SimGeometry(asm, overrides=cfg.get('overrides'))

    runner.FusionAdapter = Fake
    params = [N(name='Cab_Width', value=1.0, expression='1 mm')]
    design = N(userParameters=N(count=1, item=params.__getitem__))
    box = []
    ui = N(messageBox=lambda m: box.append(m))
    app = N(version='mock', activeProduct=design, activeDocument=N(name='mock-doc'), log=lambda m: None)
    runner.run_cabinet(app, ui, cfg['folder'])
    reports = sorted(os.listdir(os.path.join(cfg['folder'], 'reports'))) if os.path.isdir(os.path.join(cfg['folder'], 'reports')) else []
    out = {'calls': calls, 'messages': box, 'reports': reports}
    for r in reports:
        if r.endswith('.json'):
            out['json'] = json.load(open(os.path.join(cfg['folder'], 'reports', r)))
    print('RESULT=' + json.dumps(out))
""")


def run_scenario(**cfg):
    with tempfile.TemporaryDirectory() as folder:
        cfg["folder"] = folder
        if "spec_file" in cfg:
            spec = cfg.pop("spec_file")
            mode = "wb" if isinstance(spec, bytes) else "w"
            with open(os.path.join(folder, "cabinet_spec.json"), mode) as fh:
                fh.write(spec)
        code = DRIVER % {"script": SCRIPT_DIR, "tests": TESTS, "cfg": json.dumps(cfg)}
        r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
        if r.returncode != 0:
            raise AssertionError(r.stdout + r.stderr)
        line = [ln for ln in r.stdout.splitlines() if ln.startswith("RESULT=")][0]
        return json.loads(line[len("RESULT="):])


def read(name):
    with open(os.path.join(SPECS, name), "r", encoding="utf-8") as fh:
        return fh.read()


class BuildPath(unittest.TestCase):
    def test_no_spec_file_stores_exact_legacy_g2_default(self):
        out = run_scenario()
        legacy_text = ('{"module":"base_cabinet@1","parameters":{"back_mm":6.0,"cabinet_id":"cabinet.001",'
                       '"dado_depth_mm":6.0,"depth_mm":550.0,"door_count":2,"end_clearance_mm":0.3,"gap_mm":3.0,'
                       '"height_mm":850.0,"material_ref":"ply_main","ply_mm":18.0,"shelf_count":1,'
                       '"slot_clearance_mm":0.5,"width_mm":1200.0},"schema_version":"0.1"}')
        self.assertEqual([c[0] for c in out["calls"]], ["compile", "store"])
        self.assertEqual(out["calls"][1][1], legacy_text)
        j = out["json"]
        self.assertEqual(j["design_spec_hash"], LEGACY_HASH)
        self.assertEqual(j["assembly_legacy_spec_hash"], LEGACY_HASH)
        self.assertEqual(j["spec_hash"], LEGACY_HASH)
        self.assertEqual(j["hash_scheme"], "legacy-0.1-canonical-sha256")
        self.assertEqual(j["design_schema_version"], "0.1")
        self.assertEqual(j["variant"], "base")
        self.assertEqual(j["mode"], "build")
        self.assertEqual(j["schema_version"], "0.1")   # legacy field keeps legacy meaning
        self.assertIn("PASS", j["validation"]["verdict"])

    def test_each_02_fixture_builds_and_reports_metadata(self):
        for v, n_checks_extra in (("base", 0), ("tall", 3), ("overhead", 3)):
            with self.subTest(variant=v):
                out = run_scenario(spec_file=read(v + ".json"))
                self.assertEqual([c[0] for c in out["calls"]], ["compile", "store"])
                j = out["json"]
                self.assertEqual(j["variant"], v)
                self.assertEqual(j["profile_version"], 1)
                self.assertEqual(j["design_schema_version"], "0.2")
                self.assertEqual(j["hash_scheme"], "g3-0.2-canonical-sha256")
                self.assertNotEqual(j["design_spec_hash"], j["assembly_legacy_spec_hash"])
                self.assertEqual(j["spec_hash"], j["assembly_legacy_spec_hash"])
                self.assertEqual(j["stored_spec"]["raw_sha256_before"], None)
                self.assertEqual(len([k for k in j["profile_limits"]]), n_checks_extra)
                self.assertEqual(j["validation"]["verdict"], "PASS")
                self.assertEqual(json.loads(out["calls"][1][1])["variant"], v)
                self.assertIn("parameters_read_from_fusion", j)
                self.assertIn("parameters_mm", j)

    def test_sparse_02_report_hashes_distinguish_input_and_stored_canonical_bytes(self):
        import hashlib
        sparse = json.dumps({"schema_version": "0.2", "module": "cabinet@1",
                             "variant": "tall", "profile_version": 1,
                             "parameters": {"width_mm": 600}}, separators=(",", ":"))
        out = run_scenario(spec_file=sparse)
        j = out["json"]
        canonical_stored = out["calls"][1][1]
        self.assertEqual(j["input_spec_raw_sha256"], hashlib.sha256(sparse.encode()).hexdigest())
        self.assertEqual(j["stored_spec_raw_sha256"], hashlib.sha256(canonical_stored.encode()).hexdigest())
        self.assertEqual(j["stored_spec_raw_sha256"], j["stored_spec"]["raw_sha256_after"])
        self.assertNotEqual(j["input_spec_raw_sha256"], j["stored_spec_raw_sha256"])

    def test_bad_specs_rejected_before_any_cad_mutation(self):
        bad = {
            "duplicate": '{"schema_version":"0.1","schema_version":"0.1","module":"base_cabinet@1","parameters":{}}',
            "range": '{"schema_version":"0.2","module":"cabinet@1","variant":"tall","profile_version":1,"parameters":{"height_mm":2300}}',
            "garbage": "not json",
            "bom": b"\xef\xbb\xbf{}",
            "oversize": " " * 70000 + "{}",
        }
        for name, text in bad.items():
            with self.subTest(case=name):
                out = run_scenario(spec_file=text)
                self.assertEqual(out["calls"], [])
                self.assertEqual(out["reports"], [])
                self.assertIn("rejected before anything was built", out["messages"][0])

    def test_failed_build_keeps_error_handling(self):
        out = run_scenario(compile_raises=True)
        self.assertEqual([c[0] for c in out["calls"]], ["compile"])  # never stored a half-built spec
        self.assertIn("Build failed part-way", out["messages"][0])
        self.assertEqual(out["reports"], [])


class MeasurePath(unittest.TestCase):
    G2_STORED = ('{"module":"base_cabinet@1","parameters":{"back_mm":6.0,"cabinet_id":"cabinet.001",'
                 '"dado_depth_mm":6.0,"depth_mm":550.0,"door_count":2,"end_clearance_mm":0.3,"gap_mm":3.0,'
                 '"height_mm":850.0,"material_ref":"ply_main","ply_mm":18.0,"shelf_count":1,'
                 '"slot_clearance_mm":0.5,"width_mm":1200.0},"schema_version":"0.1"}')

    def test_g2_stored_design_measures_read_only(self):
        out = run_scenario(stored=self.G2_STORED)
        self.assertEqual(out["calls"], [])  # no compile, no store
        j = out["json"]
        self.assertEqual(j["mode"], "measure")
        self.assertEqual(j["design_schema_version"], "0.1")
        self.assertEqual(j["design_spec_hash"], LEGACY_HASH)
        self.assertTrue(j["migrated_in_memory"])
        self.assertEqual(j["stored_spec"]["raw_sha256_before"], j["stored_spec"]["raw_sha256_after"])
        self.assertTrue(j["stored_spec"]["unchanged"])
        self.assertEqual(j["stored_spec_raw_sha256"], j["stored_spec"]["raw_sha256_before"])
        self.assertEqual(j["validation"]["verdict"], "PASS")

    def test_noncanonical_stored_01_distinguishes_raw_from_canonical(self):
        pretty = json.dumps(json.loads(self.G2_STORED), indent=2)  # same meaning, different bytes
        out = run_scenario(stored=pretty)
        j = out["json"]
        self.assertEqual(out["calls"], [])
        self.assertEqual(j["design_spec_hash"], LEGACY_HASH)             # canonical meaning
        self.assertNotEqual(j["stored_spec"]["raw_sha256_before"], LEGACY_HASH)  # raw bytes differ
        self.assertTrue(j["stored_spec"]["unchanged"])

    def test_stored_02_tall_measures_with_profile_checks_and_live_edit_fail(self):
        stored = read("tall.json")
        out = run_scenario(stored=stored)
        self.assertEqual(out["calls"], [])
        self.assertEqual(out["json"]["variant"], "tall")
        ids = [c["check_id"] for c in out["json"]["validation"]["checks"]]
        self.assertIn("profile.tall.height_range", ids)
        self.assertIn("entities.managed_ids", ids)
        out = run_scenario(stored=stored, overrides={"Cab_Height": 2300.0})
        st = {c["check_id"]: c["status"] for c in out["json"]["validation"]["checks"]}
        self.assertEqual(st["profile.tall.height_range"], "FAIL")
        self.assertEqual(out["json"]["validation"]["verdict"], "FAIL")
        self.assertEqual(out["calls"], [])  # still read-only, parameter not clamped

    def test_unreadable_stored_spec_changes_nothing(self):
        for text in ("{broken", '{"schema_version":"0.9"}'):
            out = run_scenario(stored=text)
            self.assertEqual(out["calls"], [])
            self.assertEqual(out["reports"], [])
            self.assertIn("cannot be read", out["messages"][0])

    def test_managed_components_without_spec_refuses(self):
        out = run_scenario(managed_no_spec=True)
        self.assertEqual(out["calls"], [])
        self.assertIn("no stored spec", out["messages"][0])

    def test_spec_file_ignored_when_design_already_has_spec(self):
        out = run_scenario(stored=self.G2_STORED, spec_file=read("tall.json"))
        self.assertEqual(out["json"]["variant"], "base")
        self.assertEqual(out["calls"], [])


if __name__ == "__main__":
    unittest.main()
