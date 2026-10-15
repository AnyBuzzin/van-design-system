"""C0 golden protection: the verified G2 generator and sources must not change in G3."""
import json
import os
import unittest

import g2_snapshot as snap

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
LEGACY_DEFAULT_HASH = "a0a43e005535b33f069dd786dc847682734819a09bd0803650688bb5e4b0a750"


def _load(name):
    with open(os.path.join(FIX, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


class GoldenAssemblyTests(unittest.TestCase):
    def test_all_shelf_door_combinations_match_frozen_snapshot(self):
        golden = _load("g2_golden.json")["combos"]
        self.assertEqual(len(golden), 10)
        for key, expected in golden.items():
            n, d = int(key.split("_")[0][1:]), int(key.split("_")[1][1:])
            with self.subTest(combo=key):
                got, exp = snap.combo_snapshot(n, d), dict(expected)
                ids, sts = got.pop("sim_check_ids"), got.pop("sim_check_statuses")
                exp_ids, exp_sts = exp.pop("sim_check_ids"), exp.pop("sim_check_statuses")
                self.assertEqual(got, exp)  # assembly, params, panels, ops, hashes: identical
                # G3 adds exactly one check (entities.managed_ids); every original check
                # is retained, in order, with the same status.  Frozen fixture NOT edited.
                census = "entities.managed_ids"
                self.assertEqual(ids.count(census), 1)
                self.assertEqual([i for i in ids if i != census], exp_ids)
                self.assertEqual([s for i, s in zip(ids, sts) if i != census], exp_sts)
                self.assertEqual(sts[ids.index(census)], "PASS")

    def test_default_legacy_hash_is_frozen(self):
        self.assertEqual(snap.combo_snapshot(1, 2)["legacy_spec_hash"], LEGACY_DEFAULT_HASH)

    def test_default_base_has_58_named_checks(self):
        c = _load("g2_golden.json")["combos"]["s1_d2"]
        self.assertEqual(len(c["sim_check_ids"]), 58)
        self.assertEqual(set(c["sim_check_statuses"]), {"PASS"})


class ProtectedSourceTests(unittest.TestCase):
    def test_protected_files_byte_identical(self):
        expected = _load("protected_sources.json")
        current = snap.protected_manifest()
        self.assertEqual(current["files"], expected["files"])
        self.assertEqual(current["baseline_files"], expected["baseline_files"])

    def test_adapter_geometry_methods_unchanged(self):
        expected = _load("protected_sources.json")["adapter_methods"]
        self.assertEqual(set(expected), set(snap.PROTECTED_ADAPTER_METHODS))
        self.assertEqual(snap.protected_manifest()["adapter_methods"], expected)


if __name__ == "__main__":
    unittest.main()
