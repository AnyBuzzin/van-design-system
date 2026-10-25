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

    def enable_placement(self):
        self.assembly = self.module.composition_assembly(editable_placement=True)
        self.env = self.assembly.parameters.resolve()
        self.parameter_writes = []
        outer = self
        class Parameter:
            def __init__(self, definition):
                self.name = definition.name
                self._expression = ('%s mm' % definition.value_mm if definition.is_base else definition.expr.render())
            @property
            def value(self):
                return outer.env[self.name]/10
            @property
            def expression(self):
                return self._expression
            @expression.setter
            def expression(self, expression):
                outer.parameter_writes.append((self.name, expression))
                self._expression = expression
                base = {p.name:outer.env[p.name] for p in outer.assembly.parameters.base()}
                base[self.name] = float(expression.removesuffix(' mm'))
                outer.env = outer.assembly.parameters.resolve(base)
                for panel in outer.assembly.panels:
                    box = panel.box.resolve(outer.env)
                    volume = box.volume-sum(o.cut.resolve(outer.env).volume for o in outer.assembly.operations
                                           if o.target_panel_id == panel.stable_id)
                    outer.bodies[panel.stable_id] = MeasuredBody(box,volume)
        params = [Parameter(p) for p in self.assembly.parameters.params]
        lookup = {p.name:p for p in params}
        self.design.userParameters = Collection(params)
        self.design.userParameters.itemByName = lookup.get
        def material(sid, point):
            return self.bodies[sid].box.contains_point(point) and not any(
                o.cut.resolve(self.env).contains_point(point) for o in self.assembly.operations if o.target_panel_id == sid)
        self.source.point_in_material.side_effect = material

    def test_guarded_position_sequence_measures_restores_and_refuses_without_writes(self):
        self.enable_placement()
        initial = dict(self.env)
        report = self.module.composition_placement_sequence(self.design,self.assembly,self.guard)
        self.assertEqual(report['refusal']['outcome'],'PASS')
        self.assertEqual(report['refusal']['preview']['outcome'],'REFUSED')
        self.assertEqual(report['refusal']['before'],report['refusal']['after'])
        self.assertEqual(report['refusal']['state_before'],report['refusal']['state_after'])
        self.assertEqual(len(self.parameter_writes),4)  # Two edit setters + two restores; none for refusal.
        self.assertEqual(self.env,initial)
        for stage, gap in zip(report['stages'],(200,100)):
            self.assertEqual(stage['outcome'],'PASS')
            self.assertEqual(len(stage['checks']),20)
            self.assertEqual(next(c for c in stage['checks'] if c['id']=='composition_gap')['measured_mm'],gap)
            joinery=next(c for c in stage['checks'] if c['id']=='translated_joinery')
            self.assertEqual(joinery['status'],'PASS')
            self.assertEqual(sum('.probe.' in c['check_id'] for c in joinery['checks']),12)

    def test_refused_invalid_and_intermediate_overlap_never_use_setter(self):
        self.enable_placement()
        for x,y in ((100,100),(0,2000)):
            result=self.module.move_composition(self.design,self.assembly,x,y,self.guard)
            self.assertEqual(result['outcome'],'REFUSED')
        for x in (None,True,float('inf'),10001):
            with self.assertRaises(ValueError): self.module.move_composition(self.design,self.assembly,x,0,self.guard)
        self.assertEqual(self.parameter_writes,[])
        self.fake.doEvents.assert_not_called()

    def test_placement_measurement_failure_keeps_partial_evidence_and_stops(self):
        self.enable_placement()
        report = dict(stages=[],refusal=None)
        real = self.module.measure_composition
        calls = []
        def failed(*args):
            calls.append(1)
            result=real(*args)
            if len(calls)==2: result['outcome']='FAIL'
            return result
        with patch.object(self.module,'measure_composition',side_effect=failed):
            with self.assertRaises(RuntimeError):
                self.module.composition_placement_sequence(self.design,self.assembly,self.guard,report)
        self.assertEqual(len(self.parameter_writes),2)
        self.assertEqual(len(report['stages']),1)
        self.assertEqual(report['stages'][0]['outcome'],'FAIL')
        self.assertIsNone(report['refusal'])

    def test_full_composition_job_keeps_width_sequence_and_records_placement_evidence(self):
        self.enable_placement()
        self.design.designType = 1
        app = NS(activeDocument=NS(isSaved=False,isModified=False), activeProduct=self.design,
                 version='fake', activeViewport=NS(fit=Mock()))
        module = importlib.import_module('vandesign.cad.fusion.shelf_regeneration')
        with tempfile.TemporaryDirectory() as out, patch.object(module,'require_empty'):
            path = self.module.run_composition_demo(app,out,self.guard)
            with open(path) as fh: report=json.load(fh)
        self.assertEqual(report['outcome'],'PASS')
        self.assertEqual(len(report['stages']),5)
        self.assertEqual(len(report['placement']['stages']),2)
        self.assertEqual(report['placement']['refusal']['outcome'],'PASS')
        self.assertEqual(report['stages'][0]['parameters_mm'],report['placement']['stages'][-1]['parameters_mm'])

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
                patch.object(self.module,'composition_assembly', return_value=self.assembly), \
                patch.object(self.module,'composition_placement_sequence') as placement, \
                patch.object(self.module,'measure_composition', side_effect=stages):
            path = self.module.run_composition_demo(app,out,self.guard)
            with open(path) as fh: report = json.load(fh)
            self.assertEqual(report['outcome'],'PASS')
            self.assertEqual([s['label'] for s in report['stages']],
                ['baseline','edit_Bed_Width','restore_Bed_Width','edit_Cab_Width','restore_Cab_Width'])
            self.assertEqual(params['Bed_Width'].expression, '1400.0 mm')
        stages[1]['outcome'] = 'FAIL'
        with tempfile.TemporaryDirectory() as out, patch.object(module,'require_empty'), \
                patch.object(self.module,'composition_assembly', return_value=self.assembly), \
                patch.object(self.module,'measure_composition', side_effect=stages) as measurement:
            with self.assertRaises(RuntimeError): self.module.run_composition_demo(app,out,self.guard)
            self.assertEqual(measurement.call_count, 2)
            self.assertEqual(params['Bed_Width'].expression, '1300 mm')
            with open(out+'/composition.json') as fh: report=json.load(fh)
            self.assertEqual(report['outcome'],'FAIL')
