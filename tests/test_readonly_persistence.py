"""Offline only: distinguish affected bodies from configured participants."""
import copy
import importlib
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,patch
import test_composition_runner
from vandesign.modules.storage_box import phase_a_persistence_matches,build_storage_scene
from vandesign.modules.variants import get_profile

class ReadOnlyOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_composition_runner.CompositionRunnerTests()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        f=self.fixture
        self.m=importlib.import_module('vandesign.cad.fusion.test_envelope')
        p=patch.object(self.m,'adsk',f.fake);p.start();self.addCleanup(p.stop)
        p=patch.object(self.m,'FusionAdapter',return_value=NS(geometry_source=lambda:f.source))
        p.start();self.addCleanup(p.stop)
        p=patch.object(self.m,'validate',return_value=NS(checks=[NS(to_dict=lambda:dict(status='PASS'))]*59))
        p.start();self.addCleanup(p.stop)
        class ReadOnlyTimeline:
            count=37
            @property
            def markerPosition(self):return 37
            @markerPosition.setter
            def markerPosition(self,v):raise AssertionError('Timeline write forbidden')
        f.design.timeline=ReadOnlyTimeline()
        class NoParticipants(NS):
            @property
            def participantBodies(self):raise AssertionError('Participant read forbidden')
        for comp in f.design.allComponents.items:
            for i,feature in enumerate(comp.features.extrudeFeatures.items):
                body=feature.participantBodies[0];body.isValid=True
                attrs=dict(feature.__dict__);attrs.pop('participantBodies')
                attrs['bodies']=test_composition_runner.Collection([body])
                attrs['timelineObject']=NS(rollTo=Mock(side_effect=AssertionError('Timeline roll forbidden')))
                comp.features.extrudeFeatures.items[i]=NoParticipants(**attrs)
        self.features=[c.features.extrudeFeatures.item(0) for c in f.design.allComponents.items if c.features.extrudeFeatures.count]

    def measure(self):
        f=self.fixture
        return self.m.measure_test(f.design,f.assembly,f.guard,expected_panels=11,expected_timeline=37,
                                   base_profile=get_profile('base',1),read_only_ownership=True)

    def test_full_measurement_never_reads_participants_or_writes_timeline(self):
        r=self.measure();self.assertEqual(r['outcome'],'PASS')
        own=[c for c in r['checks'] if c.get('check_id','').endswith('.affected_body_ownership')]
        self.assertEqual(len(own),2)
        self.assertTrue(all('participants' not in c for c in own))
        for f in self.features:f.timelineObject.rollTo.assert_not_called()

    def test_wrong_extra_missing_invalid_bodies_parent_and_api_failure_refuse(self):
        feature=self.features[0];original=feature.bodies
        for values in ([],original.items*2,self.features[1].bodies.items):
            feature.bodies=test_composition_runner.Collection(values)
            self.assertEqual(self.measure()['outcome'],'FAIL')
        feature.bodies=original
        original.items[0].isValid=False
        with self.assertRaises(RuntimeError):self.measure()
        original.items[0].isValid=True
        feature.bodies=NS(count=1,item=Mock(side_effect=RuntimeError('API unavailable')))
        with self.assertRaises(RuntimeError):self.measure()
        feature.bodies=original
        parent=feature.parentComponent
        feature.parentComponent=self.features[1].parentComponent
        self.assertEqual(self.measure()['outcome'],'FAIL')
        feature.parentComponent=parent
        for key,value in (('isSuppressed',True),('healthState',1)):
            original_value=getattr(feature,key);setattr(feature,key,value)
            self.assertEqual(self.measure()['outcome'],'FAIL')
            setattr(feature,key,original_value)

    def test_nonfinite_measurement_and_rolled_back_timeline_fail(self):
        original=self.fixture.source.parameter_value
        self.fixture.source.parameter_value=lambda n:float('nan')
        with self.assertRaises(RuntimeError):self.measure()
        self.fixture.source.parameter_value=original
        self.fixture.design.timeline=NS(count=37,markerPosition=30)
        with self.assertRaises(RuntimeError):self.measure()

class PersistenceComparisonTests(unittest.TestCase):
    def setUp(self):
        a=build_storage_scene();env=a.parameters.resolve()
        self.before=dict(outcome='PASS',bodies={},checks=[])
        for p in a.panels:
            b=p.box.resolve(env);v=b.volume
            self.before['bodies'][p.stable_id]=dict(min=b.lo,max=b.hi,volume_mm3=v)
            self.before['checks'].append(dict(check_id=p.stable_id+'.volume',status='PASS',observed=v,
                expected=v,tolerance=1,unit='mm3',object_ids=[p.stable_id]))
        self.after=copy.deepcopy(self.before)
        for op in a.operations:
            self.before['checks'].append(dict(check_id=op.operation_id+'.ownership',status='PASS',participants=[op.target_panel_id]))
            self.after['checks'].append(dict(check_id=op.operation_id+'.affected_body_ownership',status='PASS',
                affected_bodies=[op.target_panel_id],feature_parent=op.target_panel_id))

    def test_comparison_preserves_reports_and_strict_volume_epsilon(self):
        original=copy.deepcopy((self.before,self.after))
        self.assertTrue(phase_a_persistence_matches(self.before,self.after))
        self.assertEqual((self.before,self.after),original)
        key=next(iter(self.after['bodies']))
        self.after['bodies'][key]['volume_mm3']+=2
        self.assertFalse(phase_a_persistence_matches(self.before,self.after))

    def test_ownership_missing_extra_wrong_duplicate_or_unknown_never_passes(self):
        for change in ('missing','duplicate','wrong','unknown','participants'):
            r=copy.deepcopy(self.after)
            if change=='missing':r['checks'].pop()
            if change=='duplicate':r['checks'].append(r['checks'][-1])
            if change=='wrong':r['checks'][-1]['affected_bodies']=['wrong']
            if change=='unknown':r['checks'][-1]['status']='UNKNOWN'
            if change=='participants':r['checks'][-1]['participants']=r['checks'][-1].pop('affected_bodies')
            self.assertFalse(phase_a_persistence_matches(self.before,r),change)
