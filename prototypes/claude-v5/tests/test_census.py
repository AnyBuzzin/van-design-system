"""C3: read-only managed-ID census (entities.managed_ids) by multiplicity."""
import unittest

import core_path  # noqa: F401
from sim_geometry import SimGeometry
from vandesign.modules.cabinet import build_cabinet
from vandesign.schemas.cabinet_spec import CabinetSpec
from vandesign.verification.validate import validate

CID = "entities.managed_ids"


def run(**kw):
    asm = build_cabinet(CabinetSpec(shelf_count=3, door_count=1))
    rep = validate(asm, SimGeometry(asm, **kw))
    chk = [c for c in rep.checks if c.check_id == CID]
    assert len(chk) == 1
    return rep, chk[0]


class CensusTests(unittest.TestCase):
    def test_exact_match_passes(self):
        rep, c = run()
        self.assertEqual(c.status, "PASS")
        self.assertEqual(rep.verdict, "PASS")
        self.assertEqual(c.observed, c.expected)

    def test_missing_id_fails(self):
        rep, c = run(managed_missing=["panel.shelf.002"])
        self.assertEqual(c.status, "FAIL")
        self.assertIn("missing: panel.shelf.002", c.note)
        self.assertEqual(rep.verdict, "FAIL")

    def test_duplicate_detected_by_multiplicity_even_when_set_matches(self):
        # Same SET of ids, one id twice: a unique-set comparison would pass this.
        rep, c = run(managed_duplicates=["panel.left.001"])
        self.assertEqual(c.status, "FAIL")
        self.assertIn("duplicate: panel.left.001 x2", c.note)
        self.assertEqual(c.observed, c.expected + 1)

    def test_missing_plus_duplicate_same_total_still_fails(self):
        rep, c = run(managed_missing=["panel.top.001"], managed_duplicates=["panel.left.001"])
        self.assertEqual(c.observed, c.expected)  # totals equal; multiplicities differ
        self.assertEqual(c.status, "FAIL")

    def test_unexpected_id_fails(self):
        rep, c = run(managed_extra=["panel.shelf.009"])
        self.assertEqual(c.status, "FAIL")
        self.assertIn("unexpected: panel.shelf.009", c.note)

    def test_unavailable_enumeration_is_unknown(self):
        rep, c = run(managed_unavailable=True)
        self.assertEqual(c.status, "UNKNOWN")
        self.assertEqual(rep.verdict, "UNKNOWN")

    def test_raising_enumeration_is_unknown_and_recorded(self):
        rep, c = run(managed_raises=True)
        self.assertEqual(c.status, "UNKNOWN")
        self.assertTrue([d for d in rep.diagnostics if "census failed" in d])

    def test_source_without_method_is_unknown(self):
        class Legacy(SimGeometry):
            managed_ids = None
        asm = build_cabinet(CabinetSpec())
        rep = validate(asm, Legacy(asm))
        self.assertEqual([c.status for c in rep.checks if c.check_id == CID], ["UNKNOWN"])

    def test_census_check_is_last_original_checks_unchanged(self):
        rep, _ = run()
        self.assertEqual(rep.checks[-1].check_id, CID)


if __name__ == "__main__":
    unittest.main()
