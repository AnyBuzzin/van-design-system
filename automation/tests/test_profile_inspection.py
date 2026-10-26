"""Read-only inspection diagnostics; no fake result establishes live CAD success."""
import copy
import importlib.util
import json
import os
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from _helpers import AUTOMATION
from test_demo_workflow import Collection, workflow


class Frozen:
    def __init__(self, **values):
        self.__dict__.update(values)
    def __setattr__(self, name, value):
        raise AssertionError('Unexpected Fusion property write: ' + name)


class ProfileInspection(unittest.TestCase):
    def setUp(self):
        fake = NS(core=NS(), fusion=NS(FeatureHealthStates=NS(HealthyFeatureHealthState=0),
                                      Design=NS(cast=lambda x:x), DesignTypes=NS(ParametricDesignType=1)))
        spec = importlib.util.spec_from_file_location('profile_inspection_backend',
            os.path.join(AUTOMATION, 'VanDesignRunner', 'fusion_backend.py'))
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'adsk':fake, 'adsk.core':fake.core, 'adsk.fusion':fake.fusion}):
            spec.loader.exec_module(module)
        self.doc = Frozen(name='Untitled', isSaved=False, isModified=True, isValid=True, isActive=True)
        self.protected = Frozen(name='protected', isSaved=False, isModified=True, isValid=True, isActive=False)
        self.app = Frozen(activeDocument=self.doc, documents=Collection([self.protected, self.doc]))
        self.backend = module.FusionBackend(self.app, dict(g3_script_dir='unused', audit_script='unused'))
        self.design = Frozen(rootComponent=Frozen(bRepBodies=Collection(), sketches=Collection()))
        self.occ = {}
        for pid, count in [('profile.rounded.001',1), ('profile.relieved.001',4)]:
            comp = Frozen(bRepBodies=Collection([Frozen(isValid=True,isSolid=True)]),
                features=Frozen(count=count,extrudeFeatures=Collection([
                    Frozen(healthState=0,isSuppressed=False,operation=0 if i==0 else 1) for i in range(count)])),
                sketches=Collection([Frozen(profiles=Collection([1]),healthState=0,isFullyConstrained=True)
                                     for _ in range(count)]))
            self.occ[pid] = [Frozen(component=comp)]
        self.adapter = NS(_find_occurrences=Mock(return_value=self.occ))
        self.inspection = dict(identity=dict(is_saved=False),design_type='parametric',
            managed_ids={k:1 for k in self.occ},
            design_counts=dict(user_parameters=1,root_occurrences=2,all_components=3,timeline_items=12),
            timeline=dict(count=12,marker_position=12),
            user_parameters=[dict(name='Profile_Thickness',unit='mm',value_mm=18.0)])

    def run_diagnostic(self):
        with patch.dict(sys.modules, {'demo_workflow':workflow}):
            return self.backend._profile_diagnostics(self.design,self.inspection,self.adapter)

    def test_recognition_readonly_observations_and_no_receipt_adoption(self):
        sessions=dict(workflow.SESSIONS);baseline=workflow.BASELINE
        before=copy.deepcopy(self.inspection)
        r=json.loads(json.dumps(self.run_diagnostic()))
        self.assertEqual(r['outcome'],'OBSERVED');self.assertEqual(r['errors'],[])
        self.assertEqual(len(r['components']),2)
        self.assertEqual(len(r['components'][0]['extrusions']),4)
        self.assertEqual(r['components'][0]['sketches'][0]['fully_constrained'],True)
        self.assertEqual(self.inspection,before)
        self.assertEqual(workflow.SESSIONS,sessions);self.assertIs(workflow.BASELINE,baseline)

    def test_signature_mismatches_never_read_features(self):
        changes=[('managed_ids',{}),('design_counts',{}),('timeline',dict(count=12,marker_position=0)),
                 ('user_parameters',[]),('identity',dict(is_saved=True)),('design_type','direct'),
                 ('user_parameters',[dict(name='Profile_Thickness',unit='mm',value_mm=20.0)])]
        for key,value in changes:
            with self.subTest(key=key):
                before=self.inspection[key];self.inspection[key]=value
                self.assertEqual(self.run_diagnostic()['outcome'],'NOT_RUN')
                self.inspection[key]=before
        self.adapter._find_occurrences.assert_not_called()

    def test_existing_inspect_fields_are_preserved(self):
        design=Frozen(rootComponent=self.design.rootComponent,designType=1,
            timeline=Frozen(count=12,markerPosition=12),
            userParameters=Collection([Frozen(name='Profile_Thickness',expression='18 mm',unit='mm',value=1.8)]))
        wrapper=NS(stored_spec_json=lambda:None,has_managed_assembly=lambda:False,
            geometry_source=lambda:NS(managed_ids=lambda:dict(self.inspection['managed_ids'])))
        self.adapter.FusionAdapter=lambda d:wrapper
        g3=dict(adapter=self.adapter,runner=NS(_design_counts=lambda d:dict(self.inspection['design_counts'])))
        with patch.object(self.backend,'_design',return_value=design),patch.object(self.backend,'_g3',return_value=g3), \
             patch.object(self.backend,'identity',return_value=dict(is_saved=False)), \
             patch.object(workflow,'destinations',return_value=['unchanged destination']), \
             patch.object(workflow,'inventory',return_value={'unchanged':'inventory'}), \
             patch.dict(sys.modules,{'demo_workflow':workflow}):
            r=self.backend.inspect()
        self.assertEqual(r['profile_diagnostics']['outcome'],'OBSERVED')
        self.assertEqual(r['cloud_destinations'],['unchanged destination'])
        self.assertEqual(r['session'],{'unchanged':'inventory'})
        self.assertEqual(r['user_parameters'][0]['expression'],'18 mm')
        self.assertEqual(set(r),{'cloud_destinations','identity','design_type','has_managed_assembly',
            'stored_spec_sha256','design_counts','timeline','managed_ids','user_parameters','session','profile_diagnostics'})

    def test_failed_or_missing_properties_are_unknown_but_other_observations_retained(self):
        comp=self.occ['profile.rounded.001'][0].component
        class Broken:
            profiles=Collection([1]);healthState=0
            @property
            def isFullyConstrained(self):raise RuntimeError('API unavailable')
        for sketch in (Broken(),Frozen(profiles=Collection([1]),healthState=0,isFullyConstrained=None)):
            comp.sketches.values[0]=sketch
            r=self.run_diagnostic();self.assertEqual(r['outcome'],'UNKNOWN')
            self.assertTrue(r['errors']);self.assertEqual(len(r['components']),2)
            self.assertIsNone(r['components'][1]['sketches'][0]['fully_constrained'])

    def test_negative_properties_are_reported_without_geometry_qualification(self):
        comp=self.occ['profile.rounded.001'][0].component
        comp.sketches.values[0]=Frozen(profiles=Collection(),healthState=1,isFullyConstrained=False)
        r=self.run_diagnostic()
        # Complete reads retain raw negatives; no model PASS is claimed.
        self.assertEqual(r['outcome'],'OBSERVED')
        self.assertEqual(r['components'][1]['sketches'][0],
            dict(index=0,profile_count=0,health_state=1,fully_constrained=False))

    def test_ambiguous_identity_or_document_change_returns_unknown(self):
        original=self.occ['profile.rounded.001']
        self.occ['profile.rounded.001']=original*2
        self.assertEqual(self.run_diagnostic()['outcome'],'UNKNOWN')
        self.occ['profile.rounded.001']=original
        with patch.object(workflow,'unchanged',side_effect=RuntimeError('Document changed')):
            self.assertEqual(self.run_diagnostic()['outcome'],'UNKNOWN')
