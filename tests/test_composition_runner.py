"""Offline control-flow/readback tests; these do not establish Fusion correctness."""
import copy
import importlib
import json
import sys
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from vandesign.core.geometry import Box
from vandesign.verification.geometry_source import MeasuredBody


class Collection:
    def __init__(self, items=()):
        self.items = list(items)

    @property
    def count(self):
        return len(self.items)

    def item(self, i):
        return self.items[i]


class CompositionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.fake = NS(core=NS(), fusion=NS(
            FeatureOperations=NS(CutFeatureOperation=1),
            FeatureHealthStates=NS(HealthyFeatureHealthState=0),
            DesignTypes=NS(ParametricDesignType=1), Design=NS(cast=lambda d: d)), doEvents=Mock())
        self.modules = patch.dict(sys.modules, {'adsk': self.fake, 'adsk.core': self.fake.core,
                                              'adsk.fusion': self.fake.fusion})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.module = importlib.import_module('vandesign.cad.fusion.interior_demo')
        self.adsk = patch.object(self.module, 'adsk', self.fake)
        self.adsk.start(); self.addCleanup(self.adsk.stop)
        self.assembly = self.module.composition_assembly()
        self.env = self.assembly.parameters.resolve()
        self.timeline = NS(count=37, markerPosition=37)
        self.features = []
        components = []
        self.bodies = {}
        for panel in self.assembly.panels:
            comp = NS(attributes=NS(itemByName=lambda *a, sid=panel.stable_id: NS(value=sid)))
            body = NS(parentComponent=comp, isSolid=True)
            comp.bRepBodies = Collection([body])
            feats = []
            for op in self.assembly.operations:
                if op.target_panel_id == panel.stable_id:
                    def roll(before):
                        self.timeline.markerPosition = 30
                        return True
                    feat = NS(name=op.operation_id, operation=1, parentComponent=comp,
                              participantBodies=[body], timelineObject=NS(rollTo=Mock(side_effect=roll)),
                              healthState=0, isSuppressed=False)
                    feats.append(feat); self.features.append(feat)
            comp.features = NS(extrudeFeatures=Collection(feats))
            components.append(comp)
            box = panel.box.resolve(self.env)
            volume = box.volume-sum(o.cut.resolve(self.env).volume for o in self.assembly.operations
                                   if o.target_panel_id == panel.stable_id)
            self.bodies[panel.stable_id] = MeasuredBody(box, volume)
        root = NS(bRepBodies=Collection(), occurrences=Collection(components),
                  features=NS(extrudeFeatures=Collection()))
        self.design = NS(rootComponent=root, allComponents=Collection([root]+components),
                         timeline=self.timeline, userParameters=Collection(self.assembly.parameters.params))
        self.source = NS(parameter_value=lambda n: self.env[n], body=lambda sid: self.bodies.get(sid),
                         managed_ids=lambda: {p.stable_id: 1 for p in self.assembly.panels},
                         point_in_material=Mock(return_value=False), interference_count=Mock(return_value=0))
        self.adapter = patch.object(self.module, 'FusionAdapter', return_value=NS(geometry_source=lambda: self.source, compile=Mock()))
        self.adapter.start(); self.addCleanup(self.adapter.stop)
        self.guard = Mock()

    def measure(self):
        return self.module.measure_composition(self.design, self.assembly, self.guard)

    def test_measured_nets_ids_gap_and_two_exact_cuts(self):
        report = self.measure()
        self.assertEqual(report['outcome'], 'PASS')
        self.assertEqual(len(report['checks']), 19)
        self.assertEqual(report['checks'][-1]['measured_mm'], 100)
        self.assertEqual(self.timeline.markerPosition, 37)
        for feature in self.features:
            feature.timelineObject.rollTo.assert_called_once_with(True)

    def test_wrong_or_missing_participants_fail_and_restore_timeline(self):
        for parts in ([], self.features[1].participantBodies, self.features[0].participantBodies*2):
            with self.subTest(parts=len(parts)):
                self.features[0].participantBodies = parts
                self.assertEqual(self.measure()['outcome'], 'FAIL')
                self.assertEqual(self.timeline.markerPosition, 37)

    def test_missing_nonfinite_volume_wrong_geometry_and_material_never_pass(self):
        sid = self.assembly.panels[0].stable_id
        original = self.bodies[sid]
        for body in (None, MeasuredBody(original.box, float('nan')),
                     MeasuredBody(original.box, original.volume_mm3+10000),
                     MeasuredBody(Box((1, 1, 1), (2, 2, 2)), original.volume_mm3)):
            with self.subTest(body=body):
                self.bodies[sid] = body
                self.assertEqual(self.measure()['outcome'], 'FAIL')
        self.bodies[sid] = original
        for material in (None, True):
            self.source.point_in_material.return_value = material
            self.assertEqual(self.measure()['outcome'], 'FAIL')

    def test_unavailable_interference_extra_cut_and_extra_body_refuse(self):
        self.source.interference_count.return_value = None
        self.assertEqual(self.measure()['outcome'], 'FAIL')
        self.source.interference_count.return_value = 0
        self.design.rootComponent.bRepBodies.items.append(object())
        self.assertEqual(self.measure()['outcome'], 'FAIL')
        self.design.rootComponent.bRepBodies.items.clear()
        self.design.rootComponent.features.extrudeFeatures.items.append(self.features[0])
        self.assertEqual(self.measure()['outcome'], 'FAIL')

    def test_participant_api_failure_restores_timeline_but_not_pass(self):
        self.features[0].timelineObject.rollTo.side_effect = RuntimeError('unavailable')
        self.assertEqual(self.measure()['outcome'], 'FAIL')
        self.assertEqual(self.timeline.markerPosition, 37)

    def test_resized_geometry_uses_stage_specific_gap_and_net_volumes(self):
        for overrides, gap in (({'Bed_Width':1300}, 200), ({'Cab_Width':1100}, 100), ({}, 100)):
            with self.subTest(overrides=overrides):
                self.env = self.assembly.parameters.resolve(overrides)
                for panel in self.assembly.panels:
                    box = panel.box.resolve(self.env)
                    volume = box.volume-sum(o.cut.resolve(self.env).volume for o in self.assembly.operations
                                           if o.target_panel_id == panel.stable_id)
                    self.bodies[panel.stable_id] = MeasuredBody(box, volume)
                report = self.measure()
                self.assertEqual(report['outcome'], 'PASS')
                self.assertEqual(report['checks'][-1]['measured_mm'], gap)
                self.assertEqual(report['checks'][-1]['expected_mm'], gap)

    def test_document_guard_failure_stops_before_readback(self):
        self.guard.side_effect = RuntimeError('unexpected document')
        with self.assertRaises(RuntimeError): self.measure()
        self.features[0].timelineObject.rollTo.assert_not_called()

    def test_width_sequence_and_failure_stop_without_automatic_restore(self):
        # Real measurement judging is tested above; isolate only sequence control here.
        baseline = self.measure()
        stages = []
        for name, value in [(None, None), ('Bed_Width', 1300), ('Bed_Width', None),
                            ('Cab_Width', 1100), ('Cab_Width', None)]:
            stage = copy.deepcopy(baseline)
            stage['parameters_mm'] = self.assembly.parameters.resolve({name:value} if value else {})
            stages.append(stage)
        params = {n:NS(expression='%s mm' % self.env[n]) for n in ('Bed_Width','Cab_Width')}
        self.design.userParameters.itemByName = params.get
        self.design.designType = 1
        app = NS(activeDocument=NS(isSaved=False,isModified=False), activeProduct=self.design,
                 version='fake', activeViewport=NS(fit=Mock()))
        module = importlib.import_module('vandesign.cad.fusion.shelf_regeneration')
        with tempfile.TemporaryDirectory() as out, patch.object(module,'require_empty'), \
                patch.object(self.module,'measure_composition', side_effect=stages):
            path = self.module.run_composition_demo(app,out,self.guard)
            with open(path) as fh: report = json.load(fh)
            self.assertEqual(report['outcome'],'PASS')
            self.assertEqual([s['label'] for s in report['stages']],
                ['baseline','edit_Bed_Width','restore_Bed_Width','edit_Cab_Width','restore_Cab_Width'])
            self.assertEqual(params['Bed_Width'].expression, '1400.0 mm')
        stages[1]['outcome'] = 'FAIL'
        with tempfile.TemporaryDirectory() as out, patch.object(module,'require_empty'), \
                patch.object(self.module,'measure_composition', side_effect=stages) as measurement:
            with self.assertRaises(RuntimeError): self.module.run_composition_demo(app,out,self.guard)
            self.assertEqual(measurement.call_count, 2)
            self.assertEqual(params['Bed_Width'].expression, '1300 mm')
            with open(out+'/composition.json') as fh: report=json.load(fh)
            self.assertEqual(report['outcome'],'FAIL')

