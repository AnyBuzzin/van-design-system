"""Offline tests of the G3 cut-audit logic against a fake Fusion object graph (NOT real Fusion)."""
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(os.path.dirname(HERE), "tools", "VanDesignCutAuditG3", "VanDesignCutAuditG3.py")
spec = importlib.util.spec_from_file_location("cut_audit_g3", PATH)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

CUT = object()


class Attr:
    def __init__(self, v): self.value = v


class Attrs:
    def __init__(self, d=None): self.d = dict(d or {})
    def itemByName(self, group, name): return Attr(self.d[(group, name)]) if (group, name) in self.d else None


class Comp:
    def __init__(self, sid=None, name="c"):
        self.name = name
        self.attributes = Attrs({("VanDesign", "stable_id"): sid} if sid else {})
        self.extrude_list = []
        self.features = type("F", (), {})()
        self.features.extrudeFeatures = type("E", (), {"count": property(lambda s: len(self.extrude_list)),
                                                       "item": lambda s, i: self.extrude_list[i]})()
        self.entityToken = "tok-" + (sid or name)


class Body:
    def __init__(self, comp): self.parentComponent = comp; self.name = comp.name


class Timeline:
    def __init__(self, count, marker=None, fail_restore=False):
        self.count = count
        self._marker = count if marker is None else marker
        self.fail_restore = fail_restore
        self.restoring = False
    @property
    def markerPosition(self): return self._marker
    @markerPosition.setter
    def markerPosition(self, v):
        if self.fail_restore and v == self.start:
            raise RuntimeError("cannot move marker")
        self._marker = v
    def moveToEnd(self): self._marker = self.count; return True


class Feature:
    def __init__(self, name, owner, participants, op=CUT, tl=None, roll_fails=False):
        self.name, self.parentComponent, self.participantBodies, self.operation = name, owner, participants, op
        self.timelineObject = type("TO", (), {"rollTo": lambda s, before: self._roll(before)})()
        self.tl, self.roll_fails = tl, roll_fails
    def _roll(self, before):
        if self.roll_fails:
            raise RuntimeError("rollTo failed")
        self.tl._marker = 3


class Design:
    def __init__(self, shelves=1, stored=True, **kw):
        self.left, self.right = Comp("panel.left.001", "01 Left Side"), Comp("panel.right.001", "02 Right Side")
        self.shelves = [Comp("panel.shelf.%03d" % k, "Shelf %d" % k) for k in range(1, shelves + 1)]
        self.timeline = Timeline(40, fail_restore=kw.get("fail_restore", False))
        self.timeline.start = 40
        root = Comp(name="root")
        spec = json.dumps({"schema_version": "0.1", "module": "base_cabinet@1", "parameters": {"shelf_count": shelves}})
        if stored:
            root.attributes = Attrs({("VanDesign", "spec_json"): spec})
        occs = [self.left, self.right] + self.shelves
        root.occurrences = type("O", (), {"count": len(occs), "item": lambda s, i: type("Oc", (), {"component": occs[i]})()})()
        self.rootComponent = root
        self.userParameters = type("U", (), {"count": 9})()
        for k in range(1, shelves + 1):
            for side, comp in (("left", self.left), ("right", self.right)):
                comp.extrude_list.append(Feature("dado.shelf%d.%s" % (k, side), comp, [Body(comp)], tl=self.timeline))


def run(d): return audit.run_audit(d, CUT)


class AuditTests(unittest.TestCase):
    def test_tall_six_of_six_pass_and_timeline_restored(self):
        d = Design(shelves=3)
        r = run(d)
        self.assertEqual(r["overall"], "PASS")
        self.assertEqual(len(r["results"]), 6)
        self.assertTrue(r["timeline_restored"])
        self.assertEqual(d.timeline.markerPosition, 40)
        self.assertIn("Features passed: 6/6", audit.render_text("doc", r))

    def test_shelf_as_participant_fails(self):
        d = Design(shelves=1)
        f = d.left.extrude_list[0]
        f.participantBodies = [Body(d.shelves[0])]
        self.assertEqual(run(d)["overall"], "FAIL")

    def test_extra_participant_fails(self):
        d = Design(shelves=1)
        f = d.left.extrude_list[0]
        f.participantBodies = [Body(d.left), Body(d.shelves[0])]
        self.assertEqual(run(d)["overall"], "FAIL")

    def test_no_explicit_participants_fails(self):
        d = Design(shelves=1)
        d.right.extrude_list[0].participantBodies = []
        self.assertEqual(run(d)["overall"], "FAIL")

    def test_wrong_side_participant_fails(self):
        d = Design(shelves=1)
        d.left.extrude_list[0].participantBodies = [Body(d.right)]
        self.assertEqual(run(d)["overall"], "FAIL")

    def test_not_a_cut_fails(self):
        d = Design(shelves=1)
        d.left.extrude_list[0].operation = object()
        self.assertEqual(run(d)["overall"], "FAIL")

    def test_missing_feature_fails(self):
        d = Design(shelves=2)
        d.right.extrude_list.pop()
        self.assertEqual(run(d)["overall"], "FAIL")

    def test_duplicate_feature_name_fails(self):
        d = Design(shelves=1)
        d.left.extrude_list.append(Feature("dado.shelf1.left", d.left, [Body(d.left)], tl=d.timeline))
        self.assertEqual(run(d)["overall"], "FAIL")

    def test_unexpected_dado_feature_fails(self):
        d = Design(shelves=1)
        d.left.extrude_list.append(Feature("dado.shelf7.left", d.left, [Body(d.left)], tl=d.timeline))
        self.assertEqual(run(d)["overall"], "FAIL")

    def test_api_error_is_unknown_not_pass(self):
        d = Design(shelves=1)
        d.left.extrude_list[0].roll_fails = True
        r = run(d)
        self.assertEqual(r["overall"], "UNKNOWN")
        self.assertTrue(r["timeline_restored"])

    def test_restore_failure_is_fail_with_warning(self):
        d = Design(shelves=1, fail_restore=True)
        r = run(d)
        self.assertEqual(r["overall"], "FAIL")
        self.assertFalse(r["timeline_restored"])
        self.assertIn("DO NOT EDIT", audit.render_text("doc", r))

    def test_no_stored_spec_unknown(self):
        self.assertEqual(run(Design(stored=False))["overall"], "UNKNOWN")

    def test_zero_shelves_audits_nothing_so_unknown(self):
        self.assertEqual(run(Design(shelves=0))["overall"], "UNKNOWN")

    def test_expected_operations_for_0_2_spec(self):
        txt = json.dumps({"schema_version": "0.2", "module": "cabinet@1", "variant": "tall",
                          "profile_version": 1, "parameters": {"shelf_count": 3}})
        ops = audit.expected_operations(txt)
        self.assertEqual(len(ops), 6)
        self.assertEqual(set(ops.values()), {"panel.left.001", "panel.right.001"})

    def test_script_never_mutates_design(self):
        with open(PATH, encoding="utf-8") as fh:
            src = fh.read()
        for banned in (".deleteMe", "extrudeFeatures.add", ".participantBodies =", "attributes.add",
                       "userParameters.add", "expression ="):
            self.assertNotIn(banned, src)


if __name__ == "__main__":
    unittest.main()
