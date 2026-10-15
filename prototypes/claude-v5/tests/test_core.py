import importlib.util
import os
import re
import sys
import types
import unittest

from core_path import ROOT  # noqa: F401
from vandesign.core.expr import ExprError, Mm, Param
from vandesign.core.params import ParamDef, ParameterError, ParameterSet
from vandesign.modules.cabinet import SPEC_TO_PARAM, build_cabinet
from vandesign.schemas.cabinet_spec import CabinetSpec, SpecError
from vandesign.components.model import ConstraintViolation

# Hand-calculated fixtures (mm): overrides applied on top of the default 1200/18/6/0.3 cabinet.
FIXTURES = {
    "A": ({}, 1175.4, 12.3, 5.7),
    "B": ({"Cab_Dado_Depth": 10}, 1183.4, 8.3, 9.7),
    "C": ({"Cab_Dado_Depth": 10, "Cab_Width": 1000}, 983.4, 8.3, 9.7),
    "D": ({"Cab_Dado_Depth": 10, "Cab_Ply": 15}, 1189.4, 5.3, 9.7),
}


def fusion_eval(text, env):
    """Evaluate a rendered Fusion expression with plain Python (test helper)."""
    py = re.sub(r"\s*mm\b", "", text)
    return eval(py, {"__builtins__": {}}, dict(env))


class ExprTests(unittest.TestCase):
    def test_render_and_eval_agree(self):
        e = Param("W") - 2 * Param("T") + 2 * Param("G") - 2 * Param("E")
        env = {"W": 1200, "T": 18, "G": 10, "E": 0.3}
        self.assertAlmostEqual(e.eval(env), 1183.4)
        self.assertAlmostEqual(fusion_eval(e.render(), env), 1183.4)

    def test_dimension_rules(self):
        with self.assertRaises(ExprError):
            Param("A") + 5
        with self.assertRaises(ExprError):
            Param("A") * Param("B")
        with self.assertRaises(ExprError):
            Param("A") / Param("B")
        with self.assertRaises(ExprError):
            Param("A") / 0
        self.assertEqual(Mm(0).render(), "0 mm")
        self.assertEqual(Mm(0.5).render(), "0.5 mm")

    def test_unknown_param(self):
        with self.assertRaises(ExprError):
            Param("Nope").eval({})

    def test_parameter_graph_rejects_forward_and_duplicate(self):
        with self.assertRaises(ParameterError):
            ParameterSet((ParamDef("B", expr=Param("A")), ParamDef("A", value_mm=1)))
        with self.assertRaises(ParameterError):
            ParameterSet((ParamDef("A", value_mm=1), ParamDef("A", value_mm=2)))
        with self.assertRaises(ParameterError):
            ParameterSet((ParamDef("A"),))


class CabinetFixtureTests(unittest.TestCase):
    def setUp(self):
        self.asm = build_cabinet(CabinetSpec())

    def test_fixtures_a_to_d(self):
        for name, (ov, length, shelf_x, insertion) in FIXTURES.items():
            with self.subTest(fixture=name):
                env = self.asm.parameters.resolve(ov)
                self.assertAlmostEqual(env["Cab_Shelf_Length"], length, places=6)
                self.assertAlmostEqual(env["Cab_Shelf_X"], shelf_x, places=6)
                self.assertAlmostEqual(env["Cab_Dado_Depth"] - env["Cab_End_Clearance"], insertion, places=6)

    def test_fixture_d_vertical_layout(self):
        env = self.asm.parameters.resolve(FIXTURES["D"][0])
        self.assertAlmostEqual(env["Cab_Compartment"], 402.5)
        self.assertAlmostEqual(env["Cab_Shelf1_Z"], 417.5)
        self.assertAlmostEqual(env["Cab_Slot1_Z"], 417.25)

    def test_rendered_expressions_match_python_evaluation(self):
        for name, (ov, *_rest) in FIXTURES.items():
            env = self.asm.parameters.resolve(ov)
            for p in self.asm.parameters.derived():
                with self.subTest(fixture=name, param=p.name):
                    self.assertAlmostEqual(fusion_eval(p.expr.render(), env), env[p.name], places=9)

    def test_v4_parameter_names_preserved(self):
        v4_base = {"Cab_Width", "Cab_Height", "Cab_Depth", "Cab_Ply", "Cab_Back", "Cab_Gap",
                   "Cab_Dado_Depth", "Cab_Slot_Clearance", "Cab_End_Clearance"}
        self.assertEqual(set(SPEC_TO_PARAM.values()), v4_base)
        names = set(self.asm.parameters.names())
        self.assertTrue({"Cab_Inner_Depth", "Cab_Slot_Height", "Cab_Shelf_X", "Cab_Shelf_Length",
                         "Cab_Compartment", "Cab_Shelf1_Z", "Cab_Slot1_Z"} <= names)

    def test_matches_archived_v4_derived_parameters(self):
        """V5 derived values must equal the tested V4 script's expressions."""
        for n in (0, 1, 2, 3, 4):
            v4 = _load_v4(n)
            asm = build_cabinet(CabinetSpec(shelf_count=n))
            for fname, (ov, *_r) in FIXTURES.items():
                env = asm.parameters.resolve(ov)
                v4env = {k: float(re.sub(r"\s*mm", "", e)) for k, e in v4.SETTINGS.items()}
                v4env.update({k: float(v) for k, v in ov.items()})
                for name, expr in v4.derived_settings():
                    v4env[name] = fusion_eval(expr, v4env)
                    with self.subTest(shelves=n, fixture=fname, param=name):
                        self.assertAlmostEqual(env[name], v4env[name], places=9)

    def test_shelf_and_cut_ownership(self):
        for op in self.asm.operations:
            self.assertIn(op.target_panel_id, ("panel.left.001", "panel.right.001"))
            self.assertTrue(op.mating_panel_id.startswith("panel.shelf."))

    def test_all_shelf_and_door_counts_build(self):
        for n in range(5):
            for d in (1, 2):
                asm = build_cabinet(CabinetSpec(shelf_count=n, door_count=d))
                self.assertEqual(len(asm.operations), 2 * n)


class SpecTests(unittest.TestCase):
    def test_roundtrip_and_hash(self):
        s = CabinetSpec(shelf_count=2)
        self.assertEqual(CabinetSpec.from_json(s.to_json()), s)
        self.assertEqual(s.spec_hash(), CabinetSpec.from_json(s.to_json()).spec_hash())
        self.assertNotEqual(s.spec_hash(), CabinetSpec().spec_hash())

    def test_rejections(self):
        with self.assertRaises(SpecError):
            CabinetSpec.from_dict({"schema_version": "9", "module": "base_cabinet@1", "parameters": {}})
        with self.assertRaises(SpecError):
            CabinetSpec.from_dict({"schema_version": "0.1", "module": "base_cabinet@1", "parameters": {"bogus": 1}})
        with self.assertRaises(SpecError):
            CabinetSpec(shelf_count=9)
        with self.assertRaises(SpecError):
            CabinetSpec(width_mm=float("nan"))

    def test_constraint_violations_fail_before_cad(self):
        for kw in ({"dado_depth_mm": 18.0}, {"dado_depth_mm": 20.0}, {"end_clearance_mm": 6.0},
                   {"height_mm": 50.0}, {"back_mm": 600.0}):
            with self.subTest(kw=kw), self.assertRaises(ConstraintViolation):
                build_cabinet(CabinetSpec(**kw))


def _load_v4(shelf_count):
    path = os.path.join(ROOT, "baseline", "VanCabinetJoinery_V4_rev2.py")
    stub_adsk = types.ModuleType("adsk")
    stub_adsk.core = types.ModuleType("adsk.core")
    stub_adsk.fusion = types.ModuleType("adsk.fusion")
    saved = {k: sys.modules.get(k) for k in ("adsk", "adsk.core", "adsk.fusion")}
    sys.modules.update({"adsk": stub_adsk, "adsk.core": stub_adsk.core, "adsk.fusion": stub_adsk.fusion})
    try:
        spec = importlib.util.spec_from_file_location("v4_baseline", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.SHELF_COUNT = shelf_count
        return mod
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


if __name__ == "__main__":
    unittest.main()
