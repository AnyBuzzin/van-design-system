import copy
from dataclasses import replace
import json
import unittest

from vandesign.components.model import Panel
from vandesign.core.expr import Mm
from vandesign.core.geometry import Box, BoxExpr
from vandesign.modules.test_envelope import (
    ARCHES, build_lined_envelope, furniture_rows, preview_lined_fit)
from vandesign.modules.storage_box import build_storage_scene
from vandesign.schemas.envelope_spec import EnvelopeSpec, KeepOut, MountingPoint, load_envelope_spec


class LinedEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.spec = EnvelopeSpec()
        self.a = build_lined_envelope(self.spec)
        self.env = self.a.parameters.resolve()

    def probe(self, box, spec=None):
        """Isolate the fit predicate from the accepted cabinet/bed geometry."""
        spec = spec or self.spec
        a = build_lined_envelope(spec)
        p = Panel("probe.001", "probe", "bottom", "ply_18_nominal",
                  BoxExpr(tuple(Mm(v) for v in box.lo), tuple(Mm(v) for v in box.size)))
        a = replace(a, panels=tuple(p for p in a.panels if p.stable_id.startswith("reference."))+(p,),
                    operations=())
        return preview_lined_fit(a, spec, a.parameters.resolve())

    def test_default_datums_and_published_gap(self):
        self.assertEqual(self.spec.finished_size, (1748, 3008, 1989))
        boxes = {p.stable_id: p.box.resolve(self.env) for p in self.a.panels}
        self.assertEqual(boxes[ARCHES[0]], Box((0, 582, 0), (178, 1382, 282)))
        self.assertEqual(boxes[ARCHES[1]], Box((1570, 582, 0), (1748, 1382, 282)))
        self.assertEqual(boxes[ARCHES[1]].lo[0]-boxes[ARCHES[0]].hi[0], 1392)
        self.assertEqual(boxes["bed.001.bed.deck.001"].lo[2], 687)
        self.assertEqual(len(self.a.panels), 22)
        self.assertEqual(build_lined_envelope(self.spec), self.a)
        self.assertEqual(preview_lined_fit(self.a, self.spec, self.env)["outcome"], "PASS")
        self.assertEqual(furniture_rows(self.a), furniture_rows(build_storage_scene()))
        self.assertEqual(len(furniture_rows(self.a)), 16)

    def test_spec_roundtrip_and_strict_inputs(self):
        s = replace(self.spec, mounting_points=(MountingPoint((0, 100, 100), (1, 0, 0), "rail"),))
        self.assertEqual(load_envelope_spec(s.to_json()), s)
        for field in ("bare_width_mm", "lining_mm", "tolerance_mm", "arch_y_mm"):
            for value in (None, True, "18", float("nan"), float("inf"), -1):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    replace(s, **{field: value})
        for changes in (dict(lining_mm=400), dict(tolerance_mm=1000),
                        dict(bare_between_arches_mm=1800), dict(arch_y_mm=0),
                        dict(ceiling_split_mm=100), dict(second_bare_height_mm=2000),
                        dict(ceiling_split_mm=4000, second_bare_height_mm=2000),
                        dict(ceiling_split_mm=1500, second_bare_height_mm=0)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(s, **changes)
        data = json.loads(s.to_json())
        for change in ("unknown", "missing", "version"):
            bad = copy.deepcopy(data)
            if change == "unknown": bad["parameters"]["mystery"] = 1
            if change == "missing": del bad["parameters"]["lining_mm"]
            if change == "version": bad["schema_version"] = "future"
            with self.assertRaises(ValueError): load_envelope_spec(json.dumps(bad))
        with self.assertRaises(ValueError):
            load_envelope_spec(s.to_json().replace('"schema_version":', '"schema_version":0,"schema_version":'))
        for normal in ((0, 0, 0), (float("nan"), 0, 0), (True, 0, 0)):
            with self.assertRaises(ValueError): MountingPoint((0, 100, 100), normal, "rail")
        with self.assertRaises(ValueError): MountingPoint((0, 0, 0), (1, 0, 0), "rail", "rated")

    def test_planes_and_floor_margin_no_hidden_exception(self):
        for box in (Box((5, 5, 5), (20, 20, 20)),
                    Box((1720, 2980, 1970), (1743, 3003, 1984))):
            self.assertEqual(self.probe(box)["outcome"], "PASS")
        for axis in range(3):
            lo = [5, 5, 5]; lo[axis] -= 1e-7
            with self.assertRaisesRegex(ValueError, "inset"):
                self.probe(Box(tuple(lo), (20, 20, 20)))
        with self.assertRaisesRegex(ValueError, "inset"):
            self.probe(Box((10, 10, 0), (20, 20, 10)))

    def test_arch_spanning_corners_outside_and_expansion(self):
        # All corners miss the arch in Y, but the panel passes through its centre.
        with self.assertRaisesRegex(ValueError, "keep-out"):
            self.probe(Box((5, 500, 100), (20, 1500, 118)))
        self.assertEqual(self.probe(Box((183, 600, 5), (201, 700, 20)))["outcome"], "PASS")
        with self.assertRaisesRegex(ValueError, "keep-out"):
            self.probe(Box((183-1e-10, 600, 5), (201, 700, 20)))

    def test_zero_margin_and_exact_segment_boundary(self):
        s=replace(self.spec,tolerance_mm=0, bare_height_mm=1036,
                  ceiling_split_mm=1500, second_bare_height_mm=2036)
        self.assertEqual(self.probe(Box((500,1500,0),(510,1600,1500)),s)["outcome"],"PASS")
        with self.assertRaisesRegex(ValueError,"ceiling"):
            self.probe(Box((500,1499.999,0),(510,1600,1500)),s)
        with self.assertRaises(ValueError):
            replace(s,second_bare_height_mm=1036)

    def test_door_depth_obstructions_and_metadata(self):
        door = KeepOut("rear_door", "door", (10, 10, 0), (1700, 20, 1900))
        s = replace(self.spec, keepouts=(door,))
        self.assertEqual(self.probe(Box((100, 35, 5), (200, 45, 100)), s)["outcome"], "PASS")
        with self.assertRaisesRegex(ValueError, "keep-out"):
            self.probe(Box((100, 34.9, 5), (200, 45, 100)), s)
        for changes in (dict(keepouts=(door, door)),
                        dict(keepouts=(KeepOut("outside", "obstruction", (1700, 0, 0), (100, 10, 10)),)),
                        dict(mounting_points=(MountingPoint((2000, 0, 0), (1, 0, 0), "rail"),))):
            with self.assertRaises(ValueError): replace(s, **changes)

    def test_stepped_ceiling_both_orders_and_riser_margin(self):
        for reverse in (False, True):
            s = replace(self.spec, bare_height_mm=2036 if reverse else 1036,
                        ceiling_split_mm=1500, second_bare_height_mm=1036 if reverse else 2036)
            # Lowest usable ceiling is 995; high region supports a 1500-high box.
            low_y, high_y = (1600, 1400) if reverse else (1400, 1600)
            self.assertEqual(self.probe(Box((500, low_y, 5), (510, low_y+10, 995)), s)["outcome"], "PASS")
            self.assertEqual(self.probe(Box((500, high_y, 5), (510, high_y+10, 1500)), s)["outcome"], "PASS")
            with self.assertRaisesRegex(ValueError, "ceiling"):
                self.probe(Box((500, 1400, 5), (510, 1600, 1500)), s)
            # Touch the inset riser, then intrude by 0.001 mm.
            lo, hi = (1400, 1495) if reverse else (1505, 1600)
            self.assertEqual(self.probe(Box((500, lo, 5), (510, hi, 1500)), s)["outcome"], "PASS")
            lo, hi = (lo, hi+.001) if reverse else (lo-.001, hi)
            with self.assertRaisesRegex(ValueError, "step"):
                self.probe(Box((500, lo, 5), (510, hi, 1500)), s)
            self.assertEqual(self.probe(Box((500, 1490, 5), (510, 1510, 995)), s)["outcome"], "PASS")

    def test_parameter_edits_retarget_data_only(self):
        env = self.a.parameters.resolve({"Env_Bare_Width": 1800, "Env_Lining": 20})
        r = preview_lined_fit(self.a, self.spec, env)
        self.assertEqual(r["finished_size_mm"], (1760, 3004, 1985))
        right = self.a.panel("reference.right").box.resolve(env)
        self.assertEqual(right.lo[0], 1760)
        left = self.a.panel(ARCHES[0]).box.resolve(env)
        right = self.a.panel(ARCHES[1]).box.resolve(env)
        self.assertEqual(right.lo[0]-left.hi[0], 1392)
        self.assertEqual(left.lo[1], 580)
        self.assertEqual(left.hi[2], 280)
        retargeted = replace(self.spec, bare_width_mm=1800, lining_mm=20, provenance="UNMEASURED alternate data")
        b = build_lined_envelope(retargeted)
        self.assertNotEqual(self.a.spec_hash, b.spec_hash)
        self.assertEqual({p.stable_id for p in self.a.panels}, {p.stable_id for p in b.panels})
        self.assertEqual(self.a.panel("reference.right").box, b.panel("reference.right").box)

    def test_missing_contradictory_or_nonfinite_observations_refused_unchanged(self):
        before = copy.deepcopy((self.a, self.env, self.spec))
        for env in ({}, dict(self.env, Env_Width=1700), dict(self.env, Env_Lining=None),
                    dict(self.env, Env_Bare_Width=float("nan"))):
            with self.assertRaises(ValueError): preview_lined_fit(self.a, self.spec, env)
        boxes = {p.stable_id: p.box.resolve(self.env) for p in self.a.panels}
        for bad in (None, Box((0, 0, 0), (float("inf"), 1, 1)),
                    Box((0, 0, 0), (1, 1, 1))):
            changed = dict(boxes); changed[ARCHES[0]] = bad
            with self.assertRaises(ValueError): preview_lined_fit(self.a, self.spec, self.env, changed)
        changed = dict(boxes); changed.pop(ARCHES[0])
        with self.assertRaises(ValueError): preview_lined_fit(self.a, self.spec, self.env, changed)
        self.assertEqual((self.a, self.env, self.spec), before)
