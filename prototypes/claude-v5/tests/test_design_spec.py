"""C1: strict versioned loader - migration matrix M1-M14 and malformed corpus."""
import json
import unittest

import core_path  # noqa: F401
import g2_snapshot as snap
from vandesign.modules.cabinet import build_cabinet
from vandesign.modules.variants import build_variant
from vandesign.schemas.cabinet_spec import CabinetSpec, SpecError
from vandesign.schemas.design_spec import (
    HASH_SCHEME_LEGACY, HASH_SCHEME_V02, MAX_SPEC_BYTES, default_design_spec, load_design_spec)

LEGACY_HASH = "a0a43e005535b33f069dd786dc847682734819a09bd0803650688bb5e4b0a750"


def v02(variant, params=None, pv=1, **extra):
    d = {"schema_version": "0.2", "module": "cabinet@1", "variant": variant, "profile_version": pv}
    if params is not None:
        d["parameters"] = params
    d.update(extra)
    return json.dumps(d)


class MigrationMatrix(unittest.TestCase):
    def test_M1_g2_default_roundtrip(self):
        text = CabinetSpec().to_json()
        d = load_design_spec(text)
        self.assertEqual((d.variant, d.profile_version, d.original_schema), ("base", 1, "0.1"))
        self.assertEqual(d.design_spec_hash, LEGACY_HASH)
        self.assertEqual(d.assembly_legacy_spec_hash, LEGACY_HASH)
        self.assertEqual(d.canonical_stored_spec_json, text)
        self.assertEqual(d.hash_scheme, HASH_SCHEME_LEGACY)
        self.assertEqual(default_design_spec().canonical_stored_spec_json, text)

    def test_M2_all_combos_equal_g2_golden(self):
        with open(snap.os.path.join(snap.os.path.dirname(snap.__file__), "fixtures", "g2_golden.json"), encoding="utf-8") as fh:
            golden = json.load(fh)["combos"]
        for n in range(5):
            for dr in (1, 2):
                with self.subTest(n=n, doors=dr):
                    g = golden["s%d_d%d" % (n, dr)]
                    d = load_design_spec(g["legacy_spec_json"])
                    self.assertEqual(d.canonical_stored_spec_json, g["legacy_spec_json"])
                    self.assertEqual(d.design_spec_hash, g["legacy_spec_hash"])
                    asm = build_variant(d.resolved_params)
                    self.assertEqual(snap.assembly_snapshot(asm), {k: g[k] for k in snap.assembly_snapshot(asm)})

    def test_M3_sparse_01_uses_frozen_defaults(self):
        d = load_design_spec('{"schema_version":"0.1","module":"base_cabinet@1","parameters":{}}')
        self.assertEqual(d.design_spec_hash, LEGACY_HASH)
        d2 = load_design_spec('{"schema_version":"0.1","module":"base_cabinet@1","parameters":{"shelf_count":2}}')
        self.assertEqual(d2.resolved_params, CabinetSpec(shelf_count=2))
        self.assertEqual(d2.canonical_stored_spec_json, CabinetSpec(shelf_count=2).to_json())

    def test_M4_int_vs_float_preserved_like_g2(self):
        as_int = '{"schema_version":"0.1","module":"base_cabinet@1","parameters":{"width_mm":1200}}'
        as_float = '{"schema_version":"0.1","module":"base_cabinet@1","parameters":{"width_mm":1200.0}}'
        di, df = load_design_spec(as_int), load_design_spec(as_float)
        self.assertEqual(di.canonical_stored_spec_json, CabinetSpec(width_mm=1200).to_json())
        self.assertEqual(df.design_spec_hash, LEGACY_HASH)
        self.assertNotEqual(di.design_spec_hash, df.design_spec_hash)
        self.assertNotEqual(di.raw_sha256, df.raw_sha256)

    def test_M5_unknown_parameter_rejected(self):
        with self.assertRaises(SpecError):
            load_design_spec('{"schema_version":"0.1","module":"base_cabinet@1","parameters":{"widht_mm":5}}')

    def test_M6_unknown_toplevel_and_duplicate_keys_rejected(self):
        with self.assertRaises(SpecError):
            load_design_spec('{"schema_version":"0.1","module":"base_cabinet@1","parameters":{},"extra":1}')
        with self.assertRaises(SpecError):
            load_design_spec('{"schema_version":"0.1","schema_version":"0.1","module":"base_cabinet@1","parameters":{}}')
        with self.assertRaises(SpecError):
            load_design_spec('{"schema_version":"0.1","module":"base_cabinet@1","parameters":{"shelf_count":1,"shelf_count":2}}')

    def test_M7_01_with_variant_or_wrong_module_rejected(self):
        with self.assertRaises(SpecError):
            load_design_spec('{"schema_version":"0.1","module":"base_cabinet@1","variant":"tall","parameters":{}}')
        with self.assertRaises(SpecError):
            load_design_spec('{"schema_version":"0.1","module":"cabinet@1","parameters":{}}')

    def test_M8_full_02_all_variants_roundtrip_and_build(self):
        for variant in ("base", "tall", "overhead"):
            with self.subTest(variant=variant):
                d = load_design_spec(v02(variant))
                full = load_design_spec(d.canonical_stored_spec_json)
                self.assertEqual(full.canonical_stored_spec_json, d.canonical_stored_spec_json)
                self.assertEqual(full.design_spec_hash, d.design_spec_hash)
                self.assertEqual(d.hash_scheme, HASH_SCHEME_V02)
                self.assertFalse(d.migrated_in_memory)
                build_variant(d.resolved_params)

    def test_M9_sparse_02_resolved_from_profile(self):
        t = load_design_spec(v02("tall", {"height_mm": 2000}))
        self.assertEqual((t.resolved_params.width_mm, t.resolved_params.height_mm, t.resolved_params.shelf_count,
                          t.resolved_params.door_count), (600.0, 2000.0, 3, 1))
        stored = json.loads(t.canonical_stored_spec_json)
        self.assertEqual(len(stored["parameters"]), 13)
        self.assertIsInstance(stored["parameters"]["height_mm"], float)
        o = load_design_spec(v02("overhead"))
        self.assertEqual((o.resolved_params.width_mm, o.resolved_params.height_mm, o.resolved_params.depth_mm), (1000.0, 400.0, 350.0))

    def test_M10_02_base_vs_01_default(self):
        d1, d2 = default_design_spec(), load_design_spec(v02("base"))
        a1, a2 = build_cabinet(d1.resolved_params), build_cabinet(d2.resolved_params)
        self.assertEqual(snap.assembly_snapshot(a1), snap.assembly_snapshot(a2))
        self.assertEqual(d2.assembly_legacy_spec_hash, LEGACY_HASH)
        self.assertNotEqual(d2.design_spec_hash, LEGACY_HASH)
        self.assertNotEqual(d2.design_spec_hash, d1.design_spec_hash)

    def test_M11_bad_module_variant_profile_schema(self):
        bad = [
            v02("base").replace("cabinet@1", "base_cabinet@1"),
            v02("sideboard"), v02("tall", pv=2), v02("tall", pv=0), v02("tall", pv=True),
            v02("tall").replace('"profile_version": 1', '"profile_version": 1.0'),
            v02("tall").replace(', "profile_version": 1', ""),
            v02("tall").replace('"variant": "tall", ', ""),
            v02("tall").replace('"0.2"', '"0.3"'), v02("tall").replace('"0.2"', "0.2"),
            v02("tall").replace('"schema_version": "0.2", ', ""),
            v02("tall", extra_field=1),
        ]
        for text in bad:
            with self.subTest(text=text):
                with self.assertRaises(SpecError):
                    load_design_spec(text)

    def test_M12_01_reemits_01_never_02(self):
        d = load_design_spec(CabinetSpec(shelf_count=3).to_json())
        self.assertEqual(json.loads(d.canonical_stored_spec_json)["schema_version"], "0.1")
        self.assertEqual(d.original_schema, "0.1")

    def test_M13_loader_is_pure(self):
        # The loader takes text only: it has no adapter/CAD handle at all.
        import inspect
        self.assertEqual(list(inspect.signature(load_design_spec).parameters), ["text"])

    def test_M14_initial_profile_range_rejected(self):
        for variant, params in (("tall", {"height_mm": 2300}), ("tall", {"width_mm": 1000}),
                                ("overhead", {"depth_mm": 500}), ("overhead", {"shelf_count": 3}),
                                ("tall", {"shelf_count": 0})):
            with self.subTest(variant=variant, params=params):
                with self.assertRaises(SpecError):
                    load_design_spec(v02(variant, params))
        load_design_spec(v02("tall", {"height_mm": 2200}))  # inclusive upper bound
        load_design_spec(v02("tall", {"height_mm": 1400}))


class MalformedCorpus(unittest.TestCase):
    BASE01 = '{"schema_version":"0.1","module":"base_cabinet@1","parameters":%s}'

    def test_rejected_inputs(self):
        cases = {
            "nan": self.BASE01 % '{"width_mm":NaN}',
            "inf": self.BASE01 % '{"width_mm":Infinity}',
            "overflow": self.BASE01 % '{"width_mm":1e999}',
            "huge": self.BASE01 % '{"width_mm":1e308}',
            "bool_mm": self.BASE01 % '{"width_mm":true}',
            "string_mm": self.BASE01 % '{"width_mm":"1200"}',
            "null_param": self.BASE01 % '{"width_mm":null}',
            "negative": self.BASE01 % '{"width_mm":-1200}',
            "zero_ply": self.BASE01 % '{"ply_mm":0}',
            "float_count": self.BASE01 % '{"shelf_count":2.0}',
            "bool_count": self.BASE01 % '{"shelf_count":true}',
            "huge_count": self.BASE01 % '{"shelf_count":1000000}',
            "bad_doors": self.BASE01 % '{"door_count":3}',
            "bad_id": self.BASE01 % '{"cabinet_id":"../etc"}',
            "empty_id": self.BASE01 % '{"cabinet_id":""}',
            "int_id": self.BASE01 % '{"cabinet_id":5}',
            "params_list": self.BASE01 % "[]",
            "params_null": self.BASE01 % "null",
            "dado_ge_ply": self.BASE01 % '{"dado_depth_mm":18}',
            "not_object": "[]",
            "empty": "",
            "garbage": "{not json",
            "numeric_schema": '{"schema_version":0.1,"module":"base_cabinet@1","parameters":{}}',
            "missing_parameters": '{"schema_version":"0.1","module":"base_cabinet@1"}',
            "bom": "﻿" + self.BASE01 % "{}",
            "deep": "[" * 100000 + "]" * 100000,
            "huge_int_literal": self.BASE01 % '{"width_mm":' + "9" * 6000 + "}",
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(SpecError):
                    load_design_spec(text)

    def test_oversize_and_bad_types(self):
        with self.assertRaises(SpecError):
            load_design_spec(" " * (MAX_SPEC_BYTES + 1) + "{}")
        with self.assertRaises(SpecError):
            load_design_spec(b"\xff\xfe{}")
        with self.assertRaises(SpecError):
            load_design_spec(None)

    def test_02_specific_rejections(self):
        for params in ({"width_mm": True}, {"width_mm": "600"}, {"width_mm": None}, {"cabinet_id": "a b"},
                       {"shelf_count": 2.5}, {"bogus": 1}, {"width_mm": float("nan")} ):
            with self.subTest(params=params):
                text = v02("tall", params).replace("NaN", "NaN")
                with self.assertRaises(SpecError):
                    load_design_spec(text)

    def test_bytes_input_accepted(self):
        d = load_design_spec(CabinetSpec().to_json().encode("utf-8"))
        self.assertEqual(d.design_spec_hash, LEGACY_HASH)

    def test_errors_are_actionable(self):
        with self.assertRaises(SpecError) as cm:
            load_design_spec(v02("tall", {"height_mm": 2300}))
        self.assertIn("Cab_Height", str(cm.exception))
        self.assertIn("1400", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
