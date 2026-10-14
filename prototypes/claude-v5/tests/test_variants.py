"""C2: data profiles, live range checks, hand-computed fixtures, fault injection."""
import json
import os
import unittest

import core_path  # noqa: F401
import g2_snapshot as snap
from sim_geometry import SimGeometry
from vandesign.modules import variants
from vandesign.modules.cabinet import build_cabinet
from vandesign.modules.variants import build_variant, get_profile, profile_limits
from vandesign.schemas.design_spec import load_design_spec
from vandesign.verification.validate import validate


def spec_of(variant, **params):
    doc = {"schema_version": "0.2", "module": "cabinet@1", "variant": variant, "profile_version": 1,
           "parameters": params}
    return load_design_spec(json.dumps(doc))


def run(variant, overrides=None, **sim):
    d = spec_of(variant)
    asm = build_variant(d.resolved_params, d.profile)
    prof = d.profile
    rep = validate(asm, SimGeometry(asm, overrides=overrides, **sim),
                   profile_limits=profile_limits(prof), profile_variant=variant)
    return asm, rep


def status(rep):
    return {c.check_id: c.status for c in rep.checks}


# Hand-computed (not produced by the generator): see handover section 5.
FIXTURES = {
    "base":     dict(shelf_len=1175.4, comp=398.0,  z=[416.0],                 dados=2, checks=58),
    "tall":     dict(shelf_len=575.4,  comp=452.5,  z=[470.5, 941.0, 1411.5],  dados=6, checks=108),
    "overhead": dict(shelf_len=975.4,  comp=173.0,  z=[191.0],                 dados=2, checks=58),
}


class HandComputedFixtures(unittest.TestCase):
    def test_values(self):
        for v, f in FIXTURES.items():
            with self.subTest(variant=v):
                asm, rep = run(v)
                env = asm.parameters.resolve()
                self.assertAlmostEqual(env["Cab_Shelf_Length"], f["shelf_len"], places=9)
                self.assertAlmostEqual(env["Cab_Shelf_X"], 12.3, places=9)
                self.assertAlmostEqual(env["Cab_Compartment"], f["comp"], places=9)
                for k, z in enumerate(f["z"], 1):
                    self.assertAlmostEqual(env["Cab_Shelf%d_Z" % k], z, places=9)
                self.assertEqual(len(asm.operations), f["dados"])
                self.assertEqual(rep.verdict, "PASS", rep.text(only_problems=True))

    def test_check_count_formula_and_snapshots(self):
        for v, f in FIXTURES.items():
            with self.subTest(variant=v):
                asm, rep = run(v)
                n = len([p for p in asm.panels if p.role == "shelf"])
                d = len([p for p in asm.panels if p.role == "door"])
                extra = len(profile_limits(get_profile(v, 1)))
                self.assertEqual(len(rep.checks) - extra, 28 + 26 * n + 2 * d)
                self.assertEqual(len(rep.checks) - extra, f["checks"])


class OneGenerator(unittest.TestCase):
    def test_variants_use_build_cabinet_output(self):
        for v in FIXTURES:
            d = spec_of(v)
            self.assertEqual(snap.assembly_snapshot(build_variant(d.resolved_params)),
                             snap.assembly_snapshot(build_cabinet(d.resolved_params)))

    def test_profiles_contain_no_geometry(self):
        with open(variants.__file__, encoding="utf-8") as fh:
            src = fh.read()
        for banned in ("Panel(", "BoxExpr", "DadoOperation", "Param(", "Mm(", "core.expr", "core.geometry"):
            self.assertNotIn(banned, src)

    def test_profiles_immutable(self):
        p = get_profile("tall", 1)
        with self.assertRaises(TypeError):
            p.defaults["height_mm"] = 1.0
        with self.assertRaises(Exception):
            p.variant = "x"

    def test_base_has_no_limits_and_no_profile_checks(self):
        _, rep = run("base")
        self.assertEqual(profile_limits(get_profile("base", 1)), {})
        self.assertFalse([c for c in rep.checks if c.check_id.startswith("profile.")])

    def test_original_base_check_ids_retained(self):
        with open(os.path.join(os.path.dirname(snap.__file__), "fixtures", "g2_golden.json"), encoding="utf-8") as fh:
            golden = json.load(fh)
        _, rep = run("base")
        self.assertEqual([c.check_id for c in rep.checks], golden["combos"]["s1_d2"]["sim_check_ids"])


class EditMatrix(unittest.TestCase):
    EDITS = {
        "base": [{"Cab_Dado_Depth": 5.0}, {"Cab_Width": 1000.0}, {"Cab_Ply": 16.0}, {"Cab_Height": 900.0}, {"Cab_Depth": 600.0}],
        "tall": [{"Cab_Dado_Depth": 5.0}, {"Cab_Width": 700.0}, {"Cab_Ply": 16.0}, {"Cab_Height": 2000.0}, {"Cab_Depth": 600.0}],
        "overhead": [{"Cab_Dado_Depth": 5.0}, {"Cab_Width": 1200.0}, {"Cab_Ply": 16.0}, {"Cab_Height": 500.0}, {"Cab_Depth": 400.0}],
    }

    def test_edits_pass_within_range(self):
        for v, edits in self.EDITS.items():
            for ov in edits:
                with self.subTest(variant=v, edit=ov):
                    _, rep = run(v, overrides=ov)
                    self.assertEqual(rep.verdict, "PASS", rep.text(only_problems=True))

    def test_tall_height_2000_redistributes_shelves(self):
        asm, rep = run("tall", {"Cab_Height": 2000.0})
        env = SimGeometry(asm, overrides={"Cab_Height": 2000.0}).env
        self.assertAlmostEqual(env["Cab_Compartment"], 477.5)
        self.assertAlmostEqual(env["Cab_Shelf1_Z"], 18 + 477.5)
        self.assertAlmostEqual(env["Cab_Shelf3_Z"], 18 + 3 * 477.5 + 36)
        self.assertEqual(rep.verdict, "PASS")


class RangeChecks(unittest.TestCase):
    def test_out_of_range_fails_by_name_without_clamping(self):
        cases = [("tall", "Cab_Height", 2300.0, "profile.tall.height_range"),
                 ("tall", "Cab_Width", 950.0, "profile.tall.width_range"),
                 ("tall", "Cab_Depth", 250.0, "profile.tall.depth_range"),
                 ("overhead", "Cab_Height", 800.0, "profile.overhead.height_range"),
                 ("overhead", "Cab_Width", 1600.0, "profile.overhead.width_range")]
        for v, name, val, cid in cases:
            with self.subTest(cid=cid):
                asm, rep = run(v, {name: val})
                st = status(rep)
                self.assertEqual(st[cid], "FAIL")
                self.assertEqual(rep.verdict, "FAIL")
                chk = [c for c in rep.checks if c.check_id == cid][0]
                self.assertEqual(chk.observed, val)  # actual live value, never clamped
                self.assertIn("OUT OF RANGE", chk.note)
                self.assertIsNotNone(chk.limit_min)
                self.assertIsNotNone(chk.limit_max)
                # Geometry checks themselves still pass: range failure is a distinct, named FAIL.
                self.assertEqual([k for k, s in st.items() if s == "FAIL"], [cid])

    def test_bounds_inclusive(self):
        for val in (1400.0, 2200.0):
            _, rep = run("tall", {"Cab_Height": val})
            self.assertEqual(status(rep)["profile.tall.height_range"], "PASS")

    def test_unreadable_parameter_is_unknown(self):
        _, rep = run("tall", unreadable_params=["Cab_Height"])
        self.assertEqual(status(rep)["profile.tall.height_range"], "UNKNOWN")
        self.assertNotEqual(rep.verdict, "PASS")

    def test_limit_metadata_layout(self):
        _, rep = run("tall")
        d = rep.to_dict()
        ranged = [c for c in d["checks"] if c["check_id"].startswith("profile.")]
        plain = [c for c in d["checks"] if not c["check_id"].startswith("profile.")]
        self.assertEqual(len(ranged), 3)
        for c in ranged:
            self.assertEqual(c["limit_min"] < c["limit_max"], True)
        for c in plain:
            self.assertNotIn("limit_min", c)
            self.assertNotIn("limit_max", c)
            self.assertEqual(set(c), {"check_id", "status", "observed", "expected", "tolerance", "unit", "object_ids", "note"})


class FaultInjection(unittest.TestCase):
    def test_cut_trimming_shelf_fails_for_every_variant(self):
        for v in FIXTURES:
            with self.subTest(variant=v):
                _, rep = run(v, bug_cut_all=True)
                self.assertEqual(rep.verdict, "FAIL")
                failed = [c.check_id for c in rep.checks if c.status == "FAIL"]
                self.assertTrue([i for i in failed if i.endswith(".mating_unmodified")], failed)

    def test_every_shelf_has_exactly_one_left_and_one_right_op(self):
        for v in FIXTURES:
            asm, _ = run(v)
            shelves = [p.stable_id for p in asm.panels if p.role == "shelf"]
            for sid in shelves:
                ops = [o for o in asm.operations if o.mating_panel_id == sid]
                self.assertEqual(sorted(o.target_panel_id for o in ops), ["panel.left.001", "panel.right.001"])
            self.assertNotIn(True, [o.target_panel_id.startswith("panel.shelf") for o in asm.operations])

    def test_missing_grooves_unreadable_and_no_containment_never_pass(self):
        for kw in ({"skip_cuts": True}, {"no_containment": True}, {"unmeasurable": ["panel.shelf.001"]},
                   {"unreadable_params": ["Cab_Width"]}, {"interference": None}):
            for v in FIXTURES:
                with self.subTest(variant=v, fault=kw):
                    _, rep = run(v, **kw)
                    self.assertNotEqual(rep.verdict, "PASS")


if __name__ == "__main__":
    unittest.main()
