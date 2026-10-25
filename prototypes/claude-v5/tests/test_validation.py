import dataclasses
import unittest

import core_path  # noqa: F401
from sim_geometry import SimGeometry
from test_core import FIXTURES
from vandesign.components.model import ConstraintViolation, StructureError
from vandesign.cad.protocol import preflight
from vandesign.modules.cabinet import build_cabinet
from vandesign.schemas.cabinet_spec import CabinetSpec
from vandesign.verification.report import FAIL, PASS, UNKNOWN
from vandesign.verification.validate import validate


def failed_ids(rep):
    return [c.check_id for c in rep.checks if c.status == FAIL]


def unknown_ids(rep):
    return [c.check_id for c in rep.checks if c.status == UNKNOWN]


class ParametricEditTests(unittest.TestCase):
    """V5-01..V5-04: the same assembly, re-measured after parameter edits."""

    def test_fixtures_pass_after_edit_without_rebuild(self):
        asm = build_cabinet(CabinetSpec())
        for name, (ov, *_rest) in FIXTURES.items():
            with self.subTest(fixture=name):
                rep = validate(asm, SimGeometry(asm, ov))
                self.assertEqual(rep.verdict, PASS, rep.text(only_problems=True))

    def test_multiple_shelves_pass(self):
        for n in (0, 2, 4):
            asm = build_cabinet(CabinetSpec(shelf_count=n, height_mm=1800.0))
            rep = validate(asm, SimGeometry(asm, {"Cab_Dado_Depth": 8}))
            self.assertEqual(rep.verdict, PASS, rep.text(only_problems=True))

    def test_edit_that_violates_constraint_is_reported(self):
        asm = build_cabinet(CabinetSpec())
        rep = validate(asm, SimGeometry(asm, {"Cab_Dado_Depth": 20}))
        self.assertEqual(rep.verdict, FAIL)
        self.assertIn("constraint.dado_lt_ply", failed_ids(rep))


class FailureModeTests(unittest.TestCase):
    def setUp(self):
        self.asm = build_cabinet(CabinetSpec())

    def test_v4_bug_cut_trims_shelf_is_detected(self):
        """V5-06: grooves that also cut the shelf must FAIL."""
        rep = validate(self.asm, SimGeometry(self.asm, bug_cut_all=True))
        self.assertEqual(rep.verdict, FAIL)
        f = failed_ids(rep)
        self.assertIn("panel.shelf.001.bbox", f)
        self.assertIn("panel.shelf.001.volume", f)
        self.assertIn("dado.shelf1.left.penetration", f)
        self.assertIn("dado.shelf1.left.mating_unmodified", f)
        # The original V4 report still showed 'no interference' - confirm that signal alone is insufficient.
        self.assertNotIn("interference.joined", f)

    def test_missing_grooves_detected(self):
        rep = validate(self.asm, SimGeometry(self.asm, skip_cuts=True))
        self.assertEqual(rep.verdict, FAIL)
        self.assertIn("panel.left.001.volume", failed_ids(rep))
        self.assertIn("dado.shelf1.left.probe.centre_empty", failed_ids(rep))
        self.assertIn("interference.joined", failed_ids(rep))

    def test_shelf_misplaced_vertically(self):
        rep = validate(self.asm, SimGeometry(self.asm, shelf_dz=1.0))
        self.assertEqual(rep.verdict, FAIL)
        self.assertIn("dado.shelf1.left.gap_below", failed_ids(rep))

    def test_unavailable_evidence_is_unknown_never_pass(self):
        """V5-08."""
        for kw in ({"interference": None}, {"no_containment": True}, {"unmeasurable": ["panel.shelf.001"]},
                   {"unreadable_params": ["Cab_Width"]}):
            with self.subTest(kw=kw):
                rep = validate(self.asm, SimGeometry(self.asm, **kw))
                self.assertEqual(rep.verdict, UNKNOWN)
                self.assertNotIn("PASS -", rep.headline())
                self.assertTrue(unknown_ids(rep))

    def test_interference_detected(self):
        rep = validate(self.asm, SimGeometry(self.asm, interference=2))
        self.assertEqual(rep.verdict, FAIL)

    def test_report_serialises(self):
        d = validate(self.asm, SimGeometry(self.asm)).to_dict()
        self.assertEqual(d["verdict"], PASS)
        self.assertTrue(all("check_id" in c for c in d["checks"]))


class StructureTests(unittest.TestCase):
    """V5-07: bad targets fail before any geometry is created."""

    def setUp(self):
        self.asm = build_cabinet(CabinetSpec())

    def _with_op(self, **changes):
        ops = (dataclasses.replace(self.asm.operations[0], **changes),) + self.asm.operations[1:]
        return dataclasses.replace(self.asm, operations=ops)

    def test_missing_empty_and_self_targets(self):
        for changes in ({"target_panel_id": "panel.nope.001"}, {"target_panel_id": ""},
                        {"target_panel_id": "panel.shelf.001"}, {"mating_panel_id": "panel.nope.001"}):
            with self.subTest(changes=changes), self.assertRaises(StructureError):
                self._with_op(**changes).validate_structure()

    def test_preflight_rejects_before_adapter_work(self):
        calls = []

        class RecordingAdapter:
            def compile(self, assembly):
                preflight(assembly)
                calls.append("created")

        with self.assertRaises(StructureError):
            RecordingAdapter().compile(self._with_op(target_panel_id="panel.nope.001"))
        self.assertEqual(calls, [])

    def test_preflight_rejects_constraint_violation(self):
        bad = dataclasses.replace(self.asm, parameters=_with_base(self.asm.parameters, "Cab_Dado_Depth", 18.0))
        with self.assertRaises(ConstraintViolation):
            preflight(bad)

    def test_duplicate_ids_rejected(self):
        dup = dataclasses.replace(self.asm, panels=self.asm.panels + (self.asm.panels[0],))
        with self.assertRaises(StructureError):
            dup.validate_structure()


def _with_base(pset, name, value):
    from vandesign.core.params import ParamDef, ParameterSet
    return ParameterSet(tuple(
        ParamDef(p.name, value_mm=value, comment=p.comment) if p.name == name else p for p in pset.params))


if __name__ == "__main__":
    unittest.main()
