"""Multi-instance arrangements: namespaces, quarter-turns, collisions, fit, verification."""
import json
import unittest
from dataclasses import replace

from vandesign.arrangement import (SCHEMA, ArrangementError, Instance, build_arrangement,
                                   load_arrangement)
from vandesign.schemas.envelope_spec import EnvelopeSpec
from vandesign.verification.geometry_source import MeasuredBody
from vandesign.verification.validate import validate

CABINET = {"schema_version": "0.2", "module": "cabinet@1", "variant": "base",
           "profile_version": 1, "parameters": {"width_mm": 1100}}
BED = {"module": "bed-platform@1", "schema_version": "vandesign.bed-platform/1",
       "parameters": {"height_mm": 700.0, "length_mm": 1900.0, "ply_mm": 18.0, "width_mm": 1400.0}}
STORAGE = {"module": "storage-box@1", "schema_version": "vandesign.storage-box/1",
           "parameters": {"height_mm": 250.0, "length_mm": 800.0, "ply_mm": 18.0, "width_mm": 600.0}}
# Test-only envelope from published Crafter CR35 LWB figures; arch values ASSUMED.
CRAFTER = EnvelopeSpec(bare_width_mm=1832, bare_length_mm=4606, bare_height_mm=1961, lining_mm=18,
                       tolerance_mm=5, bare_between_arches_mm=1380, arch_length_mm=800,
                       arch_height_mm=300, arch_y_mm=2000,
                       provenance="TEST ONLY: published Crafter CR35 LWB; arches ASSUMED")


def cab(iid, prefix, pos, k):
    return Instance(iid, "cabinet", prefix, CABINET, pos, k)


def layout():
    # Finished interior 1796 x 4570; arches X 0..208 / 1588..1796, Y 1982..2782.
    return (Instance("bed.rear", "bed", "Bed1", BED, (213, 5, 5), 0),
            Instance("storage.under", "storage_box", "Box1", STORAGE, (600, 400, 5), 0),
            cab("kitchen.left", "K1", (5, 2800, 5), 1),        # back on left wall, faces aisle (+X)
            cab("kitchen.right", "K2", (1223, 2800, 5), 3))    # back on right wall, faces aisle (-X)


def boxes_of(arr, prefix, env=None):
    env = env or arr.assembly.parameters.resolve()
    return {p.stable_id: p.box.resolve(env) for p in arr.assembly.panels
            if p.stable_id.startswith(prefix + ".")}


class IdealSource:
    """Ideal solids derived from the model: box minus its own cuts."""
    def __init__(self, assembly):
        self.diagnostics = []
        self.env = assembly.parameters.resolve()
        self.boxes = {p.stable_id: p.box.resolve(self.env) for p in assembly.panels}
        self.cuts = {}
        for o in assembly.operations:
            self.cuts.setdefault(o.target_panel_id, []).append(o.cut.resolve(self.env))
        self.ids = {p.stable_id: 1 for p in assembly.panels}

    def parameter_value(self, name):
        return self.env.get(name)

    def body(self, pid):
        b = self.boxes[pid]
        return MeasuredBody(b, b.volume - sum(b.overlap_volume(c) for c in self.cuts.get(pid, ())))

    def point_in_material(self, pid, p):
        inside = lambda b: all(b.lo[i] < p[i] < b.hi[i] for i in range(3))  # noqa: E731
        return inside(self.boxes[pid]) and not any(inside(c) for c in self.cuts.get(pid, ()))

    def interference_count(self, ids):
        return 0

    def managed_ids(self):
        return dict(self.ids)


class Arrangements(unittest.TestCase):
    def test_full_layout_fits_crafter_envelope(self):
        arr = build_arrangement(layout(), CRAFTER)
        self.assertEqual(arr.fit["outcome"], "PASS")
        names = arr.assembly.parameters.names()
        for p in ("K1_Cab_Width", "K2_Cab_Width", "Bed1_Bed_Width", "Box1_Storage_Width", "K1_Pos_X"):
            self.assertIn(p, names)
        ids = [p.stable_id for p in arr.assembly.panels]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("kitchen.left.panel.door.001", ids)

    def test_instance_edit_moves_only_that_instance(self):
        arr = build_arrangement(layout(), CRAFTER)
        before = arr.assembly.parameters.resolve()
        after = arr.assembly.parameters.resolve({"K1_Cab_Width": 900})
        for pid, b in boxes_of(arr, "kitchen.right").items():
            self.assertEqual(b, boxes_of(arr, "kitchen.right", after)[pid])
        k1 = boxes_of(arr, "kitchen.left", after)
        self.assertAlmostEqual(max(b.hi[1] for b in k1.values()) - 2800, 900, places=9)
        self.assertNotEqual(before["K1_Cab_Shelf_Length"], after["K1_Cab_Shelf_Length"])

    def test_quarter_turns_face_the_aisle_and_stay_in_footprint(self):
        arr = build_arrangement(layout())
        left, right = boxes_of(arr, "kitchen.left"), boxes_of(arr, "kitchen.right")
        for boxes, (x0, y0), door_side in ((left, (5, 2800), "max"), (right, (1223, 2800), "min")):
            self.assertAlmostEqual(min(b.lo[0] for b in boxes.values()), x0, places=9)
            self.assertAlmostEqual(min(b.lo[1] for b in boxes.values()), y0, places=9)
            self.assertAlmostEqual(max(b.hi[0] for b in boxes.values()) - x0, 568, places=9)   # depth on X
            self.assertAlmostEqual(max(b.hi[1] for b in boxes.values()) - y0, 1100, places=9)  # width on Y
            doors = [b for pid, b in boxes.items() if ".door." in pid]
            back = [b for pid, b in boxes.items() if ".back." in pid][0]
            if door_side == "max":
                self.assertTrue(all(d.lo[0] > back.hi[0] for d in doors))   # doors toward +X
            else:
                self.assertTrue(all(d.hi[0] < back.lo[0] for d in doors))   # doors toward -X

    def test_every_turn_keeps_panel_sizes_and_anchor(self):
        sizes0 = None
        for k in range(4):
            arr = build_arrangement((cab("c", "C", (1000, 1000, 0), k),))
            boxes = boxes_of(arr, "c")
            self.assertAlmostEqual(min(b.lo[0] for b in boxes.values()), 1000, places=9)
            self.assertAlmostEqual(min(b.lo[1] for b in boxes.values()), 1000, places=9)
            sizes = sorted(tuple(sorted(b.size)) for b in boxes.values())
            sizes0 = sizes0 or sizes
            self.assertEqual(sizes, sizes0)

    def test_shared_material_and_misfit_refused(self):
        with self.assertRaisesRegex(ArrangementError, "share material"):
            build_arrangement((cab("a", "A", (0, 0, 0), 0), cab("b", "B", (500, 0, 0), 0)))
        touching = build_arrangement((cab("a", "A", (0, 0, 0), 0), cab("b", "B", (1100, 0, 0), 0)))
        self.assertEqual(len(touching.instances), 2)
        moved = list(layout())
        moved[2] = cab("kitchen.left", "K1", (5, 2100, 5), 1)               # into the left arch
        with self.assertRaisesRegex(ArrangementError, "Envelope fit refused"):
            build_arrangement(moved, CRAFTER)
        moved[2] = cab("kitchen.left", "K1", (5, 4000, 5), 1)               # beyond the front
        with self.assertRaisesRegex(ArrangementError, "Envelope fit refused"):
            build_arrangement(moved, CRAFTER)

    def test_duplicates_and_bad_records_refused(self):
        with self.assertRaises(ArrangementError):
            build_arrangement((cab("a", "A", (0, 0, 0), 0), cab("a", "B", (2000, 0, 0), 0)))
        with self.assertRaises(ArrangementError):
            build_arrangement((cab("a", "A", (0, 0, 0), 0), cab("b", "A", (2000, 0, 0), 0)))
        for bad in (dict(quarter_turns=4), dict(param_prefix="k1"), dict(position_mm=(0, 0)),
                    dict(module="wardrobe"), dict(instance_id="Kitchen")):
            fields = dict(instance_id="a", module="cabinet", param_prefix="A", spec=CABINET,
                          position_mm=(0, 0, 0), quarter_turns=0)
            fields.update(bad)
            with self.assertRaises(ArrangementError):
                Instance(**fields)

    def test_json_loading_is_strict(self):
        doc = {"schema_version": SCHEMA, "instances": [
            dict(instance_id=i.instance_id, module=i.module, param_prefix=i.param_prefix, spec=i.spec,
                 position_mm=list(i.position_mm), quarter_turns=i.quarter_turns) for i in layout()]}
        self.assertEqual(load_arrangement(json.dumps(doc)), layout())
        doc["instances"][0]["colour"] = "oak"
        with self.assertRaises(ArrangementError):
            load_arrangement(json.dumps(doc))
        with self.assertRaises(ArrangementError):
            load_arrangement(json.dumps({"schema_version": "x", "instances": []}))

    def test_verification_passes_for_rotated_cabinets_on_ideal_solids(self):
        arr = build_arrangement(layout(), CRAFTER)
        report = validate(arr.assembly, IdealSource(arr.assembly))
        bad = [(c.check_id, c.status, c.note) for c in report.checks if c.status != "PASS"]
        self.assertEqual(bad, [])
        self.assertTrue(any(".dado." in c.check_id and ".probe." in c.check_id for c in report.checks))

    def test_dado_checks_need_the_module_frame(self):
        arr = build_arrangement((cab("c", "C", (1000, 1000, 0), 1),))
        naive = replace(arr.assembly, operations=tuple(replace(o, quarter_turns=0)
                                                       for o in arr.assembly.operations))
        report = validate(naive, IdealSource(arr.assembly))
        self.assertTrue(any(c.status == "FAIL" and ".dado." in c.check_id for c in report.checks))


if __name__ == "__main__":
    unittest.main()
