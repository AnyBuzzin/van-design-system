"""Exercise lifecycle guards against fake Fusion documents and cloud metadata."""
import copy
import importlib.util
import json
import os
import sys
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from _helpers import AUTOMATION, TmpDirCase, job, cfg
from vdrunner.executor import Executor
from vdrunner.policy import PolicyError
from vdrunner.schema import JobSchemaError, validate_job

fake_adsk = NS(core=NS(DocumentTypes=NS(FusionDesignDocumentType=1)),
               fusion=NS(Design=NS(cast=lambda x: x)), doEvents=lambda: None)
spec = importlib.util.spec_from_file_location('tested_demo_workflow', os.path.join(AUTOMATION, 'VanDesignRunner', 'demo_workflow.py'))
workflow = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'adsk': fake_adsk, 'adsk.core': fake_adsk.core, 'adsk.fusion': fake_adsk.fusion}):
    spec.loader.exec_module(workflow)


class Collection:
    def __init__(self, values=()):
        self.values = list(values)
    @property
    def count(self):
        return len(self.values)
    def item(self, i):
        return self.values[i]


class DemoTests(TmpDirCase):
    def setUp(self):
        super().setUp()
        workflow.SESSIONS.clear()
        workflow.BASELINE = None
        self.protected = NS(name='protected', isValid=True, isSaved=True, isModified=True, isActive=True, saveAs=Mock(), close=Mock())
        self.protected.dataFile = NS(id='protected-id', versionNumber=1)
        self.doc = NS(name='new-demo', isSaved=False, isModified=False, isValid=True, isActive=False, saveAs=Mock(), close=Mock())
        root = NS(occurrences=Collection(), bRepBodies=Collection(), sketches=Collection())
        self.design = NS(rootComponent=root, userParameters=Collection(), timeline=Collection())
        self.folder = NS(id='folder-1', name='root', dataFiles=Collection(), dataFolders=Collection())
        project = NS(id='project-1', name='VanDesign', rootFolder=self.folder)
        self.app = NS(data=NS(personalUseLimits=NS(editableFileCount=3, maxEditableFileCount=10),
                              dataProjects=Collection([project])), activeProduct=self.design,
                      documents=NS(add=Mock(side_effect=self.create), count=1, item=lambda i: self.protected), activeViewport=NS(saveAsImageFile=Mock()))
        self.app.documents = Collection([self.protected])
        self.app.documents.add = Mock(side_effect=self.create)
        workflow.inventory(self.app)
        self.backend = NS(app=self.app, cfg={}, identity=lambda: {'is_saved': self.doc.isSaved})
        path = os.path.join(AUTOMATION, '..', 'demos', 'evidence', 'interior_20261015_005947.json')
        with open(path, encoding='utf-8') as fh:
            self.report = json.load(fh)
        self.report_path = os.path.join(self.tmp, 'report.json')
        with open(self.report_path, 'w') as fh:
            json.dump(self.report, fh)
        self.module = NS(run_demo=Mock(return_value=self.report_path), build_interior=Mock(), check_layout=Mock(),
                         measure=Mock(return_value=copy.deepcopy(self.report['stages'][0])))
        self.args = dict(demo_id='demo-001', name='New demo', project_id='project-1', folder_id='folder-1')

    def create(self, kind):
        self.protected.isActive = False
        self.doc.isActive = True
        if self.doc not in self.app.documents.values:
            self.app.documents.values.append(self.doc)
        return self.doc

    def run_cmd(self, cmd, args=None):
        return workflow.execute(self.backend, cmd, args or {}, self.tmp, 'demo-001')

    def build(self):
        self.run_cmd('create_demo_design')
        with patch.object(workflow, 'modules', return_value=self.module):
            self.run_cmd('run_approved_demo', dict(demo_id='demo-001', entry_point='FirstInteriorDemo'))

    def test_dimensioned_cutaway_is_owned_fixed_unsaved_and_no_retry(self):
        args=dict(demo_id='demo-001',entry_point='DimensionedCutaway')
        validate_job(job('run_approved_demo',args,target=None))
        with self.assertRaises(JobSchemaError):
            validate_job(job('run_approved_demo',dict(args,name='not allowed'),target=None))
        self.run_cmd('create_demo_design')
        module=NS(run_dimensioned_cutaway=Mock(return_value={'outcome':'PASS'}))
        with patch.object(workflow,'modules',return_value=module):
            self.assertEqual(self.run_cmd('run_approved_demo',args)['outcome'],'PASS')
            with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
            with self.assertRaises(PolicyError):self.run_cmd('save_demo_design',self.args)
        self.doc.saveAs.assert_not_called();self.protected.close.assert_not_called()
        self.protected.saveAs.assert_not_called()

    def test_lined_envelope_fixed_owned_unsaved_only_and_no_retry(self):
        args=dict(demo_id='demo-001',entry_point='LinedInteriorEnvelope')
        validate_job(job('run_approved_demo',args,target=None))
        with self.assertRaises(JobSchemaError):
            validate_job(job('run_approved_demo',dict(args,layout_mm={}),target=None))
        with self.assertRaises(PolicyError):
            self.run_cmd('run_approved_demo',args)
        self.run_cmd('create_demo_design')
        with open(self.report_path,'w') as fh:json.dump({'outcome':'PASS'},fh)
        module=NS(run_lined_envelope=Mock(return_value=self.report_path))
        with patch.object(workflow,'modules',return_value=module):
            self.assertEqual(self.run_cmd('run_approved_demo',args)['outcome'],'PASS')
            with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
            with self.assertRaises(PolicyError):self.run_cmd('save_demo_design',self.args)
        module.run_lined_envelope.assert_called_once()
        self.doc.saveAs.assert_not_called()
        self.protected.close.assert_not_called()
        self.protected.saveAs.assert_not_called()

    def test_create_preserves_existing_documents_and_checks_capacity(self):
        result = self.run_cmd('create_demo_design')
        self.assertEqual(result['capacity']['editable'], 3)
        self.assertEqual(result['destinations'][0]['project_name'], 'VanDesign')
        self.protected.saveAs.assert_not_called(); self.protected.close.assert_not_called()
        self.assertTrue(self.protected.isModified)
        self.app.data.personalUseLimits.editableFileCount = 10
        with self.assertRaises(PolicyError):
            self.run_cmd('create_demo_design')
        self.assertEqual(self.app.documents.add.call_count, 1)

    def test_rounded_panel_fixed_owned_unsaved_and_fail_stop(self):
        args=dict(demo_id='demo-001',entry_point='RoundedPanel')
        validate_job(job('run_approved_demo',args,target=None))
        for extra in ({'radius_mm':75},{'layout_mm':{}},{'script':'arbitrary.py'}):
            with self.assertRaises(JobSchemaError):
                validate_job(job('run_approved_demo',dict(args,**extra),target=None))
        with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
        self.run_cmd('create_demo_design')
        module=NS(run_rounded_panel=Mock(return_value=self.report_path))
        with open(self.report_path,'w') as fh:json.dump({'outcome':'FAIL'},fh)
        with patch.object(workflow,'modules',return_value=module):
            with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
            with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
            with self.assertRaises(PolicyError):self.run_cmd('save_demo_design',self.args)
        module.run_rounded_panel.assert_called_once()
        self.doc.saveAs.assert_not_called();self.protected.close.assert_not_called()
        self.protected.saveAs.assert_not_called()

    def test_rounded_panel_success_cannot_save_or_repeat(self):
        args=dict(demo_id='demo-001',entry_point='RoundedPanel')
        self.run_cmd('create_demo_design')
        with open(self.report_path,'w') as fh:json.dump({'outcome':'PASS'},fh)
        module=NS(run_rounded_panel=Mock(return_value=self.report_path))
        with patch.object(workflow,'modules',return_value=module):
            self.assertEqual(self.run_cmd('run_approved_demo',args)['outcome'],'PASS')
            with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
            with self.assertRaises(PolicyError):self.run_cmd('save_demo_design',self.args)
        self.doc.saveAs.assert_not_called();self.protected.close.assert_not_called()

    # ------------------------------------------------ BuildArrangement (generic)
    @staticmethod
    def arrangement_case():
        """Expected evidence for the shipped example request, plus a complete report."""
        from vandesign.arrangement_job import expected_evidence, plan_request
        path = os.path.join(AUTOMATION, 'jobs', 'requests', 'arrangement_request_crafter.json')
        with open(path, encoding='utf-8') as fh:
            request = json.load(fh)
        expected = json.loads(json.dumps(expected_evidence(plan_request(request))))
        stages = []
        for plan in expected['stages']:
            # Coherent: volumes and numeric observations are the model's own values.
            stages.append(dict(
                label=plan['label'], outcome='PASS', parameters_mm=dict(plan['parameters_mm']),
                bodies={pid: dict(min=list(lo), max=list(hi), volume_mm3=plan['volumes'][pid])
                        for pid, (lo, hi) in plan['boxes'].items()},
                counts=dict(expected['inventory']),
                checks=[dict(check_id=c, status='PASS',
                             observed=plan['numeric'][c][0] if c in plan['numeric'] else None)
                        for c in expected['required_checks']]))
        edits = [dict(e, outcome='PASS', preview=dict(outcome='REFUSED' if e['expect'] == 'refused' else 'PASS'))
                 for e in expected['edits']]
        report = dict(outcome='PASS', spec_hash=expected['spec_hash'], instances=list(expected['instances']),
                      stages=stages, planned_edits=[dict(e) for e in expected['edits']], edits=edits,
                      baseline_state={'s': 0}, final_state={'s': 0})
        return request, expected, report

    def test_build_arrangement_schema_owned_unsaved_and_no_retry(self):
        request, expected, report = self.arrangement_case()
        args = dict(demo_id='demo-001', entry_point='BuildArrangement', request=request)
        validate_job(job('run_approved_demo', args, target=None))
        req = dict(arrangement={'schema_version': 'x', 'instances': []}, envelope={}, edits=[])
        for bad in (dict(demo_id='demo-001', entry_point='BuildArrangement'),
                    dict(args, layout_mm={}), dict(args, script='x.py'),
                    dict(args, request=dict(req, extra=1)), dict(args, request=dict(req, edits=[{}] * 7)),
                    dict(args, request=dict(req, arrangement=[])), dict(args, request='{}'),
                    dict(args, request=dict(req, tool_diameter_mm=float('nan')))):
            with self.assertRaises(JobSchemaError, msg=str(bad)[:100]):
                validate_job(job('run_approved_demo', bad, target=None))
        with self.assertRaises(PolicyError):
            self.run_cmd('run_approved_demo', args)                      # no owned session yet
        self.run_cmd('create_demo_design')
        with open(self.report_path, 'w') as fh:
            json.dump(report, fh)
        module = NS(run_arrangement=Mock(return_value=self.report_path),
                    arrangement_evidence=Mock(return_value=expected))
        with patch.object(workflow, 'modules', return_value=module):
            self.assertEqual(self.run_cmd('run_approved_demo', args)['outcome'], 'PASS')
            with self.assertRaises(PolicyError):
                self.run_cmd('run_approved_demo', args)
            with self.assertRaises(PolicyError):
                self.run_cmd('save_demo_design', self.args)
        module.run_arrangement.assert_called_once()
        self.assertEqual(module.run_arrangement.call_args[0][3], request)
        module.arrangement_evidence.assert_called_once_with(request)       # bound to the same request
        self.doc.saveAs.assert_not_called(); self.protected.close.assert_not_called()

    def test_profile_fixture_uses_existing_owned_workflow_and_complete_evidence(self):
        from vandesign.verification.profile_panel import expected_evidence
        request={'fixture':'profile-panels/1'}
        expected=json.loads(json.dumps(expected_evidence()))
        args=dict(demo_id='demo-001',entry_point='BuildArrangement',request=request)
        validate_job(job('run_approved_demo',args,target=None))
        for bad in ({'fixture':'unknown'},dict(request,code='x'),dict(request,thickness=20)):
            with self.assertRaises(JobSchemaError):
                validate_job(job('run_approved_demo',dict(args,request=bad),target=None))
        stages=[]
        for plan in expected['stages']:
            stages.append(dict(label=plan['label'],outcome='PASS',parameters_mm=plan['parameters_mm'],
                counts=expected['inventory'],bodies={pid:dict(min=box[0],max=box[1],volume_mm3=plan['volumes'][pid])
                    for pid,box in plan['boxes'].items()},checks=[dict(check_id=cid,status='PASS',
                    observed=plan['numeric'][cid][0] if cid in plan['numeric'] else None) for cid in expected['required_checks']]))
        report=dict(outcome='PASS',spec_hash=expected['spec_hash'],instances=expected['instances'],stages=stages,
                    planned_edits=expected['edits'],edits=[dict(e,outcome='PASS',preview={'outcome':'REFUSED' if e['expect']=='refused' else 'PASS'}) for e in expected['edits']],
                    baseline_state={'s':0},final_state={'s':0})
        report['construction_cuts']=[]
        for c in expected['construction_cuts']:
            before=dict.fromkeys(expected['body_ids'],10000000.0);after=dict(before);after[c['owner']]-=c['removed_mm3']
            report['construction_cuts'].append(dict(cut_id=c['cut_id'],owner=c['owner'],outcome='PASS',
                before_mm3=before,after_mm3=after,ownership=dict(status='PASS',affected_bodies=[c['owner']],feature_parent=c['owner'])))
        self.assertTrue(workflow.verified_arrangement(report,expected))
        bad=copy.deepcopy(report);bad['construction_cuts']=[]
        self.assertFalse(workflow.verified_arrangement(bad,expected))
        bad=copy.deepcopy(report);c=bad['construction_cuts'][0]
        mate=next(pid for pid in expected['body_ids'] if pid!=c['owner']);c['after_mm3'][mate]-=0.01
        self.assertFalse(workflow.verified_arrangement(bad,expected))
        for cid in expected['required_checks']:
            bad=copy.deepcopy(report);bad['stages'][0]['checks']=[c for c in bad['stages'][0]['checks'] if c['check_id']!=cid]
            self.assertFalse(workflow.verified_arrangement(bad,expected),cid)
        bad=copy.deepcopy(report);bad['stages'][0]['bodies'][expected['body_ids'][0]]['volume_mm3']=123
        self.assertFalse(workflow.verified_arrangement(bad,expected))
        with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
        self.run_cmd('create_demo_design')
        with open(self.report_path,'w') as fh:json.dump(report,fh)
        module=NS(run_arrangement=Mock(return_value=self.report_path),arrangement_evidence=Mock(return_value=expected))
        with patch.object(workflow,'modules',return_value=module):
            self.assertEqual(self.run_cmd('run_approved_demo',args)['outcome'],'PASS')
            with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
            with self.assertRaises(PolicyError):self.run_cmd('save_demo_design',self.args)
        module.run_arrangement.assert_called_once();self.doc.saveAs.assert_not_called();self.protected.close.assert_not_called()

    def test_build_arrangement_acceptance_requires_complete_request_bound_evidence(self):
        _, expected, report = self.arrangement_case()
        verify = workflow.verified_arrangement
        self.assertTrue(verify(report, expected))
        noisy = copy.deepcopy(report)                                      # readback noise is fine
        for stage in noisy['stages']:
            checks = {c['check_id']: c for c in stage['checks']}
            for pid, body in stage['bodies'].items():
                body['min'][0] += 1e-7; body['volume_mm3'] += 1e-8
                checks[pid + '.volume']['observed'] = body['volume_mm3']
        self.assertTrue(verify(noisy, expected))
        # Review regression: every body volume 1 mm3 (volume checks kept consistent with it).
        tiny = copy.deepcopy(report)
        for stage in tiny['stages']:
            checks = {c['check_id']: c for c in stage['checks']}
            for pid, body in stage['bodies'].items():
                body['volume_mm3'] = 1.0
                checks[pid + '.volume']['observed'] = 1.0
        self.assertFalse(verify(tiny, expected))
        # Every numeric observation 0 (the previous fixture) is contradictory evidence.
        zeros = copy.deepcopy(report)
        for stage in zeros['stages']:
            for c in stage['checks']:
                if c['observed'] is not None:
                    c['observed'] = 0.0
        self.assertFalse(verify(zeros, expected))
        vol_id = expected['body_ids'][0] + '.volume'
        num = next(c for c in expected['numeric_checks'] if '.dado.' in c and c.endswith('.penetration'))
        def check(r, stage, cid):
            return next(c for c in r['stages'][stage]['checks'] if c['check_id'] == cid)
        numeric_cases = {
            'volume check observing zero': lambda r: check(r, 0, vol_id).__setitem__('observed', 0.0),
            'volume check not matching its body': lambda r: check(r, 1, vol_id).__setitem__(
                'observed', check(r, 1, vol_id)['observed'] + 0.5),
            'one body volume 5 mm3 off the model': lambda r: (
                r['stages'][0]['bodies'][expected['body_ids'][0]].__setitem__(
                    'volume_mm3', r['stages'][0]['bodies'][expected['body_ids'][0]]['volume_mm3'] + 5e6),
                check(r, 0, vol_id).__setitem__('observed', r['stages'][0]['bodies'][expected['body_ids'][0]]['volume_mm3'])),
            'finite penetration 1 mm out of tolerance': lambda r: check(r, 0, num).__setitem__(
                'observed', check(r, 0, num)['observed'] + 1.0),
            'report-supplied tolerance cannot widen acceptance': lambda r: check(r, 0, num).update(
                observed=check(r, 0, num)['observed'] + 1.0, expected=check(r, 0, num)['observed'] + 1.0,
                tolerance=1e9),
            'bbox deviation beyond model epsilon': lambda r: check(r, 2, expected['body_ids'][0] + '.bbox').__setitem__(
                'observed', 0.5),
        }
        for name, mutate in numeric_cases.items():
            bad = copy.deepcopy(report)
            mutate(bad)
            self.assertFalse(verify(bad, expected), name)
        # Boolean probes stay status-based (no numeric observation needed).
        self.assertTrue(any('.probe.' in c for c in expected['required_checks']))
        self.assertFalse(any('.probe.' in c for c in expected['numeric_checks']))
        jack = {'outcome': 'PASS', 'stages': [{'label': 'baseline', 'outcome': 'PASS',
                'checks': [{'check_id': 'anything', 'status': 'PASS'}]}],
                'planned_edits': [], 'edits': [], 'baseline_state': {}, 'final_state': {}}
        self.assertFalse(verify(jack, expected))
        required = expected['required_checks']
        numeric = expected['numeric_checks'][0]
        body = expected['body_ids'][0]
        label = next(p['label'] for p in expected['stages'] if p['label'].startswith('after_refusal_'))
        def every(fn):
            def apply(r):
                for s in r['stages']:
                    fn(s)
            return apply
        cases = {
            'required check removed from every stage': every(lambda s: s.__setitem__(
                'checks', [c for c in s['checks'] if c['check_id'] != required[0]])),
            'interference evidence removed from every stage': every(lambda s: s.__setitem__(
                'checks', [c for c in s['checks'] if c['check_id'] != 'furniture_interference'])),
            'body removed from every stage': every(lambda s: s['bodies'].pop(body)),
            'parameter removed from every stage': every(lambda s: s['parameters_mm'].pop(
                expected['parameter_names'][0])),
            'counts removed from every stage': every(lambda s: s.pop('counts')),
            'nonfinite numeric observation': lambda r: next(c for c in r['stages'][1]['checks']
                                                          if c['check_id'] == numeric).__setitem__('observed', float('nan')),
            'missing numeric observation': every(lambda s: next(c for c in s['checks']
                                                                if c['check_id'] == numeric).__setitem__('observed', None)),
            'nonfinite body bound': lambda r: r['stages'][0]['bodies'][body]['max'].__setitem__(0, float('inf')),
            'body 1 mm from the model': every(lambda s: s['bodies'][body]['max'].__setitem__(
                1, s['bodies'][body]['max'][1] + 1)),
            'edit not reflected in parameters': lambda r: r['stages'][1]['parameters_mm'].__setitem__(
                expected['edits'][0]['parameter'], r['stages'][0]['parameters_mm'][expected['edits'][0]['parameter']]),
            'missing refusal stage': lambda r: r.__setitem__('stages', [s for s in r['stages'] if s['label'] != label]),
            'stages out of order': lambda r: r['stages'].insert(1, r['stages'].pop(2)),
            'mismatched edit value': lambda r: r['edits'][0].__setitem__('value_mm', r['edits'][0]['value_mm'] + 1),
            'mismatched planned edit': lambda r: r['planned_edits'][1].__setitem__('expect', 'pass'),
            'refusal without refused preview': lambda r: r['edits'][1]['preview'].__setitem__('outcome', 'PASS'),
            'other request (spec hash)': lambda r: r.__setitem__('spec_hash', '0' * 64),
            'timeline count differs': every(lambda s: s['counts'].__setitem__('timeline_items', 1)),
            'duplicate check id': lambda r: r['stages'][0]['checks'].append(dict(r['stages'][0]['checks'][0])),
            'failing check': lambda r: r['stages'][2]['checks'][0].__setitem__('status', 'FAIL'),
            'state not restored': lambda r: r.__setitem__('final_state', {'s': 1}),
        }
        for name, mutate in cases.items():
            bad = copy.deepcopy(report)
            mutate(bad)
            self.assertFalse(verify(bad, expected), name)

    def test_build_arrangement_incomplete_report_is_refused_and_not_retried(self):
        request, expected, report = self.arrangement_case()
        for s in report['stages']:
            s['checks'] = [c for c in s['checks'] if c['check_id'] != 'inventory']
        with open(self.report_path, 'w') as fh:
            json.dump(report, fh)
        self.run_cmd('create_demo_design')
        module = NS(run_arrangement=Mock(return_value=self.report_path),
                    arrangement_evidence=Mock(return_value=expected))
        args = dict(demo_id='demo-001', entry_point='BuildArrangement', request=request)
        with patch.object(workflow, 'modules', return_value=module):
            with self.assertRaises(PolicyError):
                self.run_cmd('run_approved_demo', args)
            with self.assertRaises(PolicyError):
                self.run_cmd('run_approved_demo', args)                      # no retry after failure
        module.run_arrangement.assert_called_once()

    def test_tab_slot_fixed_owned_candidate_no_retry_or_save(self):
        args=dict(demo_id='demo-001',entry_point='TabSlotCoupon')
        validate_job(job('run_approved_demo',args,target=None))
        for extra in ({'tool_diameter_mm':8},{'layout_mm':{}},{'script':'arbitrary.py'}):
            with self.assertRaises(JobSchemaError):validate_job(job('run_approved_demo',dict(args,**extra),target=None))
        with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
        self.run_cmd('create_demo_design')
        with open(self.report_path,'w') as fh:json.dump({'outcome':'PASS'},fh)
        module=NS(run_tab_slot=Mock(return_value=self.report_path))
        with patch.object(workflow,'modules',return_value=module):
            self.assertEqual(self.run_cmd('run_approved_demo',args)['outcome'],'PASS')
            with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
            with self.assertRaises(PolicyError):self.run_cmd('save_demo_design',self.args)
        module.run_tab_slot.assert_called_once()
        self.doc.saveAs.assert_not_called();self.protected.close.assert_not_called();self.protected.saveAs.assert_not_called()

    def test_tab_slot_failed_build_cannot_retry(self):
        self.run_cmd('create_demo_design');args=dict(demo_id='demo-001',entry_point='TabSlotCoupon')
        module=NS(run_tab_slot=Mock(side_effect=RuntimeError('failed cut')))
        with patch.object(workflow,'modules',return_value=module):
            with self.assertRaisesRegex(RuntimeError,'failed cut'):self.run_cmd('run_approved_demo',args)
            with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
        module.run_tab_slot.assert_called_once();self.protected.close.assert_not_called()

    def test_build_refuses_nonempty_saved_wrong_tab_and_unknown_entry(self):
        self.run_cmd('create_demo_design')
        for attr, value in [('isSaved', True), ('isModified', True), ('isActive', False)]:
            old = getattr(self.doc, attr); setattr(self.doc, attr, value)
            with self.assertRaises(PolicyError):
                self.run_cmd('run_approved_demo', dict(demo_id='demo-001', entry_point='FirstInteriorDemo'))
            setattr(self.doc, attr, old)
        self.design.rootComponent.occurrences.values.append(object())
        with self.assertRaises(PolicyError):
            self.run_cmd('run_approved_demo', dict(demo_id='demo-001', entry_point='FirstInteriorDemo'))
        with self.assertRaises(PolicyError):
            self.run_cmd('run_approved_demo', dict(demo_id='demo-001', entry_point='evil'))

    def test_failed_build_and_missing_evidence_block_save(self):
        self.run_cmd('create_demo_design')
        self.module.run_demo.side_effect = RuntimeError('build failed')
        with patch.object(workflow, 'modules', return_value=self.module), self.assertRaises(RuntimeError):
            self.run_cmd('run_approved_demo', dict(demo_id='demo-001', entry_point='FirstInteriorDemo'))
        with self.assertRaises(PolicyError): self.run_cmd('save_demo_design', self.args)
        self.doc.saveAs.assert_not_called()
        bad = copy.deepcopy(self.report); bad['stages'][0]['checks'][0]['status'] = 'UNKNOWN'
        self.assertFalse(workflow.verified(bad)); self.assertFalse(workflow.verified({'outcome':'PASS'}))

    def test_save_collision_wrong_folder_and_changed_geometry_refused(self):
        self.build()
        self.folder.dataFiles.values.append(NS(name='NEW DEMO'))
        with self.assertRaises(PolicyError): self.run_cmd('save_demo_design', self.args)
        self.folder.dataFiles.values.clear()
        with self.assertRaises(PolicyError): self.run_cmd('save_demo_design', dict(self.args, project_id='wrong'))
        self.module.measure.return_value['outcome'] = 'FAIL'
        with patch.object(workflow, 'modules', return_value=self.module), self.assertRaises(PolicyError):
            self.run_cmd('save_demo_design', self.args)
        self.doc.saveAs.assert_not_called()

    def test_verified_save_once_and_no_existing_document_save(self):
        self.build()
        def save(*args):
            self.doc.isSaved = True
            self.doc.dataFile = NS(id='new-lineage', name='New demo', parentFolder=self.folder, isComplete=True)
            return True
        self.doc.saveAs.side_effect = save
        with patch.object(workflow, 'modules', return_value=self.module):
            result = self.run_cmd('save_demo_design', self.args)
        self.assertTrue(result['cloud_complete'])
        with self.assertRaises(PolicyError): self.run_cmd('save_demo_design', self.args)
        self.assertEqual(self.doc.saveAs.call_count, 1)
        self.protected.saveAs.assert_not_called(); self.protected.close.assert_not_called()

    def test_restart_unknown_session_refused(self):
        self.build(); workflow.SESSIONS.clear()
        with self.assertRaises(PolicyError): self.run_cmd('save_demo_design', self.args)
        self.doc.saveAs.assert_not_called()

    def test_uncertain_verification_and_save_are_not_retried(self):
        self.build()
        self.module.measure.side_effect = RuntimeError('measurement unavailable')
        with patch.object(workflow, 'modules', return_value=self.module), self.assertRaises(RuntimeError):
            self.run_cmd('save_demo_design', self.args)
        with self.assertRaises(PolicyError): self.run_cmd('save_demo_design', self.args)
        self.doc.saveAs.assert_not_called()
        workflow.SESSIONS.clear(); self.doc.isActive = False
        self.app.documents.values = [self.protected]
        self.module.measure.side_effect = None
        self.build(); self.doc.saveAs.return_value = False
        with patch.object(workflow, 'modules', return_value=self.module), self.assertRaises(PolicyError):
            self.run_cmd('save_demo_design', self.args)
        with self.assertRaises(PolicyError): self.run_cmd('save_demo_design', self.args)
        self.assertEqual(self.doc.saveAs.call_count, 1)

    def test_changed_existing_document_stops_workflow(self):
        self.run_cmd('create_demo_design')
        self.protected.isModified = False
        with self.assertRaises(PolicyError):
            self.run_cmd('run_approved_demo', dict(demo_id='demo-001', entry_point='FirstInteriorDemo'))
        self.doc.saveAs.assert_not_called()

    def test_layout_refusal_happens_before_build_and_blocks_save(self):
        self.run_cmd('create_demo_design')
        self.module.check_layout.side_effect = ValueError('Kitchen/storage overlaps rear bed')
        with patch.object(workflow, 'modules', return_value=self.module), self.assertRaises(PolicyError):
            self.run_cmd('run_approved_demo', dict(demo_id='demo-001', entry_point='FirstInteriorDemo', layout_mm={'Kitchen_Y':3000}))
        self.module.run_demo.assert_not_called()
        self.assertEqual(self.design.rootComponent.occurrences.count, 0)
        with self.assertRaises(PolicyError): self.run_cmd('save_demo_design', self.args)
        self.doc.saveAs.assert_not_called()

    def test_layout_schema_accepts_only_explicit_finite_mm_inputs(self):
        validate_job(job('run_approved_demo', dict(demo_id='demo-001', entry_point='FirstInteriorDemo',
                                                  layout_mm={'Bed_Width':1500, 'Kitchen_X':200}), target=None))
        for layout in ({'Kitchen_X':True}, {'Bed_Width':'1500'}, {'Kitchen_Y':float('inf')}, {'unit':'in'}):
            with self.assertRaises(JobSchemaError):
                validate_job(job('run_approved_demo', dict(demo_id='demo-001', entry_point='FirstInteriorDemo', layout_mm=layout), target=None))

    def test_vehicle_schema_and_extra_evidence_fail_closed(self):
        args=dict(demo_id='demo-001',entry_point='FirstInteriorDemo',vehicle_mm={'Van_Width':2100,'Min_Aisle':600})
        validate_job(job('run_approved_demo',args,target=None))
        for vehicle in ({'Arch_Width':True},{'Van_Length':'4600'},{'command':'x'},{'Min_Aisle':float('nan')}):
            with self.assertRaises(JobSchemaError):
                validate_job(job('run_approved_demo',dict(args,vehicle_mm=vehicle),target=None))
        missing=copy.deepcopy(self.report); missing['vehicle_mm']={}
        self.assertFalse(workflow.verified(missing))
        missing=copy.deepcopy(self.report); missing['layout_mm']={}
        self.assertFalse(workflow.verified(missing))

    def test_schema_rejects_python_paths_targets_and_bad_names(self):
        validate_job(job('create_demo_design', target=None))
        validate_job(job('save_demo_design', self.args, target=None))
        for args in (dict(demo_id='demo-001', entry_point='../x.py'),
                     dict(demo_id='demo-001', entry_point='FirstInteriorDemo', code='print(1)')):
            with self.assertRaises(JobSchemaError): validate_job(job('run_approved_demo', args, target=None))
        with self.assertRaises(JobSchemaError): validate_job(job('save_demo_design', dict(self.args, name='../overwrite'), target=None))
        with self.assertRaises(JobSchemaError): validate_job(job('create_demo_design'))

    def test_executor_does_not_infer_pass(self):
        backend = NS(identity=lambda: {}, demo_command=lambda *a: {'outcome':'UNKNOWN'})
        result = Executor(backend, cfg(), self.tmp).run(job('create_demo_design', target=None), self.tmp)
        self.assertEqual(result['outcome'], 'FAIL')

    def test_persistence_requires_explicit_clean_unprotected_demo(self):
        self.app.activeDocument = self.doc
        self.backend.identity = lambda: {'design_id':'saved-demo', 'is_saved':True, 'is_modified':False}
        self.backend.cfg['demo_persistence_design_ids'] = ['saved-demo']
        self.doc.isSaved = True; self.doc.isModified = True
        with self.assertRaises(PolicyError):
            workflow.persistence(self.backend, 'saved-demo', self.tmp)
        self.doc.close.assert_not_called()
        self.doc.isModified = False
        self.backend.cfg['protected_design_ids'] = ['saved-demo']
        with self.assertRaises(PolicyError): workflow.persistence(self.backend, 'saved-demo', self.tmp)
        self.doc.close.assert_not_called()

    def test_persistence_closes_only_clean_approved_demo_and_compares_geometry(self):
        self.app.activeDocument = self.doc
        self.doc.isSaved = True; self.doc.isModified = False
        self.doc.isActive = True; self.protected.isActive = False
        self.doc.dataFile = NS(isComplete=True)
        self.backend.identity = lambda: {'design_id':'saved-demo', 'is_saved':True, 'is_modified':False}
        self.backend.cfg['demo_persistence_design_ids'] = ['saved-demo']
        self.design.rootComponent.attributes = NS(itemByName=lambda *a: NS(value='interior.demo.001'))
        self.app.documents.open = Mock(return_value=self.doc)
        with patch.object(workflow, 'modules', return_value=self.module):
            result = workflow.persistence(self.backend, 'saved-demo', self.tmp)
        self.assertEqual(result['outcome'], 'PASS')
        self.doc.close.assert_called_once_with(False)
        self.app.documents.open.assert_called_once_with(self.doc.dataFile, True)
        self.protected.close.assert_not_called(); self.protected.saveAs.assert_not_called()
        after = copy.deepcopy(self.report['stages'][0]); after['counts']['all_components'] += 1
        self.module.measure.side_effect = [copy.deepcopy(self.report['stages'][0]), after]
        with patch.object(workflow, 'modules', return_value=self.module), self.assertRaises(PolicyError):
            workflow.persistence(self.backend, 'saved-demo', self.tmp)

    def test_capacity_invalid_missing_and_threshold_refuse_before_creation(self):
        for count in (None, True, -1, 9, 10, 11, float('nan')):
            with self.subTest(count=count):
                self.app.data.personalUseLimits.editableFileCount = count
                with self.assertRaises(PolicyError): self.run_cmd('create_demo_design')
        self.app.data.personalUseLimits = None
        with self.assertRaises(PolicyError): self.run_cmd('create_demo_design')
        self.app.documents.add.assert_not_called()

    def test_inventory_missing_metadata_or_new_tab_refuses(self):
        self.protected.dataFile.versionNumber = None
        with self.assertRaises(PolicyError): workflow.inventory(self.app)
        self.protected.dataFile.versionNumber = 1
        self.app.documents.values.append(NS(name='unexpected'))
        with self.assertRaises(PolicyError): self.run_cmd('create_demo_design')
        self.app.documents.add.assert_not_called()

    def test_no_baseline_no_creation(self):
        workflow.BASELINE = None
        with self.assertRaises(PolicyError): self.run_cmd('create_demo_design')
        self.app.documents.add.assert_not_called()

    def test_close_owned_unsaved_only_and_verify_baseline(self):
        self.run_cmd('create_demo_design')
        def close(save):
            self.assertIs(save, False)
            self.app.documents.values.remove(self.doc)
            self.doc.isValid = False
            return True
        self.doc.close.side_effect = close
        result = self.run_cmd('close_demo_design', {'demo_id':'demo-001'})
        self.assertEqual(result['outcome'], 'PASS')
        self.assertEqual(result['open_documents'], [workflow.document_state(self.protected)])
        self.protected.close.assert_not_called(); self.protected.saveAs.assert_not_called()
        with self.assertRaises(PolicyError): self.run_cmd('close_demo_design', {'demo_id':'demo-001'})
        self.doc.close.assert_called_once_with(False)

    def test_close_refuses_saved_unknown_and_changed_inventory(self):
        with self.assertRaises(PolicyError): self.run_cmd('close_demo_design', {'demo_id':'owner-title'})
        self.run_cmd('create_demo_design')
        self.doc.isSaved = True
        with self.assertRaises(PolicyError): self.run_cmd('close_demo_design', {'demo_id':'demo-001'})
        self.doc.isSaved = False
        self.app.documents.values.remove(self.protected)
        with self.assertRaises(PolicyError): self.run_cmd('close_demo_design', {'demo_id':'demo-001'})
        self.doc.close.assert_not_called()

    def test_close_failure_not_retried_and_wrong_inventory_not_pass(self):
        self.run_cmd('create_demo_design')
        self.doc.close.return_value = False
        with self.assertRaises(PolicyError): self.run_cmd('close_demo_design', {'demo_id':'demo-001'})
        with self.assertRaises(PolicyError): self.run_cmd('close_demo_design', {'demo_id':'demo-001'})
        self.doc.close.assert_called_once_with(False)

    def test_close_api_success_without_document_removal_is_not_pass(self):
        self.run_cmd('create_demo_design')
        self.doc.close.return_value = True
        with self.assertRaises(PolicyError): self.run_cmd('close_demo_design', {'demo_id':'demo-001'})
        self.doc.close.assert_called_once_with(False)
        self.protected.close.assert_not_called()

    def test_inventory_can_read_owned_doc_but_not_adopt_new_owner_doc(self):
        self.run_cmd('create_demo_design')
        self.doc.isModified = True
        result = workflow.inventory(self.app)
        self.assertEqual(len(result['open_documents']), 2)
        self.assertTrue(result['open_documents'][1]['is_modified'])
        extra = NS(name='other', isSaved=False, isModified=False, isValid=True)
        self.app.documents.values.append(extra)
        with self.assertRaises(PolicyError): workflow.inventory(self.app)
        self.assertEqual(len(workflow.BASELINE['existing']), 1)

    def test_composition_schema_fixed_entry_and_close_no_target(self):
        validate_job(job('run_approved_demo', dict(demo_id='demo-001',entry_point='BedCabinetComposition'), target=None))
        validate_job(job('close_demo_design',dict(demo_id='demo-001'),target=None))
        with self.assertRaises(JobSchemaError):
            validate_job(job('run_approved_demo',dict(demo_id='demo-001',entry_point='BedCabinetComposition',layout_mm={}),target=None))
        with self.assertRaises(JobSchemaError): validate_job(job('close_demo_design',dict(demo_id='demo-001')))

    def test_composition_dispatch_single_attempt_and_save_refusal(self):
        self.run_cmd('create_demo_design')
        report = copy.deepcopy(self.report)
        for stage in report['stages']:
            stage['label'] = stage['label'].replace('Bed_Length','Bed_Width')
            stage['checks'].append(dict(id='translated_joinery',status='PASS'))
        moved = [dict(copy.deepcopy(report['stages'][-1]), label=label)
                 for label in ('edit_cabinet_position','restore_cabinet_position')]
        report['placement'] = dict(stages=moved,refusal=dict(outcome='PASS',preview={'outcome':'REFUSED'},
            before=report['stages'][-1],after=report['stages'][-1],state_before={'timeline':37},state_after={'timeline':37}))
        self.assertTrue(workflow.verified(report,composition=True))
        for mutation in (lambda r:r.pop('placement'),
                         lambda r:r['placement']['refusal'].update(outcome='UNKNOWN'),
                         lambda r:r['placement']['refusal'].update(state_after={'timeline':38}),
                         lambda r:r['placement']['stages'][0]['checks'][0].update(status='FAIL')):
            bad=copy.deepcopy(report);mutation(bad)
            self.assertFalse(workflow.verified(bad,composition=True))
        with open(self.report_path,'w') as fh: json.dump(report,fh)
        self.module.run_composition_demo = Mock(return_value=self.report_path)
        with patch.object(workflow,'modules',return_value=self.module):
            self.run_cmd('run_approved_demo',dict(demo_id='demo-001',entry_point='BedCabinetComposition'))
            with self.assertRaises(PolicyError):
                self.run_cmd('run_approved_demo',dict(demo_id='demo-001',entry_point='BedCabinetComposition'))
            with self.assertRaises(PolicyError): self.run_cmd('save_demo_design',self.args)
        self.module.run_composition_demo.assert_called_once()
        self.doc.saveAs.assert_not_called()

    def test_test_envelope_fixed_entry_and_fail_closed_report(self):
        self.run_cmd('create_demo_design',{})
        required=['test_clearances','furniture_interference','inventory',
                  'reference.arch.left.interference','reference.arch.right.interference',
                  'cabinet.001.dado.shelf1.left.ownership','cabinet.001.dado.shelf1.right.ownership',
                  'entities.managed_ids']
        bodies={'panel.'+str(i):{} for i in range(16)}
        required += [sid+suffix for sid in bodies for suffix in ('.bbox','.volume')]
        measured=dict(outcome='PASS',bodies=bodies,checks=[dict(check_id=k,status='PASS') for k in required])
        report=dict(outcome='PASS',furniture_cut_list=[{}]*11,before=measured,after=copy.deepcopy(measured),
                    refusal={'outcome':'REFUSED'},state_before={'timeline':52},state_after={'timeline':52})
        self.assertTrue(workflow.verified_envelope(report))
        for mutation in (lambda r:r['before']['checks'].pop(),
                         lambda r:r.update(furniture_cut_list=[]),
                         lambda r:r['after'].update(outcome='UNKNOWN'),
                         lambda r:r['refusal'].update(outcome='PASS'),
                         lambda r:r['state_after'].update(timeline=53)):
            bad=copy.deepcopy(report);mutation(bad)
            self.assertFalse(workflow.verified_envelope(bad))
        with open(self.report_path,'w') as fh: json.dump(report,fh)
        self.module.run_test_envelope=Mock(return_value=self.report_path)
        with patch.object(workflow,'modules',return_value=self.module):
            self.run_cmd('run_approved_demo',dict(demo_id='demo-001',entry_point='TestTransitEnvelope'))
            with self.assertRaises(PolicyError): self.run_cmd('save_demo_design',self.args)
            with self.assertRaises(PolicyError):
                self.run_cmd('run_approved_demo',dict(demo_id='demo-001',entry_point='TestTransitEnvelope'))
        self.doc.saveAs.assert_not_called()


    def test_storage_fixed_entry_measurement_gates_and_no_save_retry(self):
        args=dict(demo_id='demo-001',entry_point='TestStorageBox')
        validate_job(job('run_approved_demo',args,target=None))
        for extras in ({'layout_mm':{}},{'script':'arbitrary.py'},{'width_mm':700}):
            with self.assertRaises(JobSchemaError):
                validate_job(job('run_approved_demo',dict(args,**extras),target=None))
        self.run_cmd('create_demo_design',{})
        required=['test_clearances','furniture_interference','inventory',
                  'reference.arch.left.interference','reference.arch.right.interference',
                  'cabinet.001.dado.shelf1.left.ownership','cabinet.001.dado.shelf1.right.ownership',
                  'entities.managed_ids','storage.parameters','storage.clearances']
        required += ['storage.contact.bottom.'+n for n in ('left','right','front','rear')]
        required += ['storage.contact.'+a+'.'+b for a,b in (
            ('left','front'),('left','rear'),('front','right'),('rear','right'))]
        bodies={'panel.'+str(i):{} for i in range(21)}
        required += [sid+suffix for sid in bodies for suffix in ('.bbox','.volume')]
        stages=[dict(outcome='PASS',bodies=copy.deepcopy(bodies),counts={'timeline_items':67},
                     parameters_mm={'Storage_Width':w},
                     checks=[dict(check_id=k,status='PASS') for k in required]) for w in (600,700,600)]
        for stage in stages:
            for sid in stage['bodies']:
                stage['bodies'][sid]['volume_mm3']=100.0
                check=next(c for c in stage['checks'] if c['check_id']==sid+'.volume')
                check.update(observed=100.0,expected=100.0,tolerance=1.0,unit='mm3',object_ids=[sid])
        report=dict(outcome='PASS',furniture_cut_list=[{}]*16,before=copy.deepcopy(stages[0]),
                    after=copy.deepcopy(stages[0]),stages=stages,refusal={'outcome':'REFUSED'},
                    state_before={'timeline':67},state_after={'timeline':67},
                    baseline_state={'timeline':67},restored_state={'timeline':67})
        self.assertTrue(workflow.verified_storage(report))
        noisy=copy.deepcopy(report)
        for stage in (noisy['stages'][-1],noisy['before'],noisy['after']):
            stage['bodies']['panel.0']['volume_mm3']+=3e-8
            next(c for c in stage['checks'] if c['check_id']=='panel.0.volume')['observed']+=3e-8
        self.assertTrue(workflow.verified_storage(noisy))
        for value in (100.001,None,float('nan'),float('inf')):
            bad=copy.deepcopy(noisy)
            for stage in (bad['stages'][-1],bad['before'],bad['after']):
                stage['bodies']['panel.0']['volume_mm3']=value
                next(c for c in stage['checks'] if c['check_id']=='panel.0.volume')['observed']=value
            self.assertFalse(workflow.verified_storage(bad))

        for mutation in (lambda r:r['stages'][1]['checks'].pop(),
                         lambda r:r['stages'][1]['parameters_mm'].update(Storage_Width=float('nan')),
                         lambda r:r['stages'][1]['parameters_mm'].update(Storage_Width=600),
                         lambda r:r['stages'][1]['bodies'].pop('panel.0'),
                         lambda r:r['stages'][1]['checks'][0].update(status='FAIL'),
                         lambda r:r['restored_state'].update(timeline=68),
                         lambda r:r['state_after'].update(timeline=68)):
            bad=copy.deepcopy(report);mutation(bad)
            self.assertFalse(workflow.verified_storage(bad))
        with open(self.report_path,'w') as fh: json.dump(report,fh)
        self.module.run_storage_box=Mock(return_value=self.report_path)
        with patch.object(workflow,'modules',return_value=self.module):
            self.run_cmd('run_approved_demo',args)
            with self.assertRaises(PolicyError): self.run_cmd('save_demo_design',self.args)
            with self.assertRaises(PolicyError): self.run_cmd('run_approved_demo',args)
        self.module.run_storage_box.assert_called_once()
        self.doc.saveAs.assert_not_called(); self.protected.close.assert_not_called()


    def phase_a_setup(self):
        # Fresh empty session only; production inventory never resets a baseline.
        workflow.BASELINE=None;self.app.documents.values=[];self.app.activeDocument=None
        workflow.inventory(self.app);self.run_cmd('create_demo_design');self.app.activeDocument=self.doc
        measured=dict(outcome='PASS',parameters_mm={'Storage_Width':600},counts={'timeline':67},
            bodies={'panel':dict(min=[0,0,0],max=[1,1,1],volume_mm3=1)},
            checks=[dict(check_id='panel.volume',status='PASS',observed=1,expected=1,tolerance=1e-6,
                         unit='mm3',object_ids=['panel'])])
        from vandesign.modules.storage_box import build_storage_scene
        for op in build_storage_scene().operations:
            measured['checks'].append(dict(check_id=op.operation_id+'.ownership',status='PASS',participants=[op.target_panel_id]))
        reopened_measure=copy.deepcopy(measured)
        for c in reopened_measure['checks']:
            if c['check_id'].endswith('.ownership'):
                target=c.pop('participants')[0]
                c.update(check_id=c['check_id'].replace('.ownership','.affected_body_ownership'),
                         affected_bodies=[target],feature_parent=target)
        state={'parameters':{'width':['600 mm',60]},'timeline':[67,67]}
        self.module.measure_phase_a_reopened=Mock(return_value=(reopened_measure,state))
        self.module.run_phase_a=Mock(return_value=dict(outcome='PASS',stages=[copy.deepcopy(measured)]))
        self.module.measure_phase_a_combined=Mock(return_value=(measured,state))
        def save(name,folder,*unused):
            self.doc.name=name;self.doc.isSaved=True
            self.doc.dataFile=NS(id='fresh-saved-id',versionNumber=1,isComplete=True,name=name,parentFolder=folder)
            return True
        self.doc.saveAs.side_effect=save
        def close(save):
            self.assertIs(save,False);self.app.documents.values=[];self.app.activeDocument=None;self.doc.isValid=False
            return True
        self.doc.close.side_effect=close
        def reopen(df,active):
            self.reopened=NS(name=df.name,isSaved=True,isModified=False,isValid=True,isActive=True,dataFile=df)
            self.app.documents.values=[self.reopened];self.app.activeDocument=self.reopened
            return self.reopened
        self.app.documents.open=Mock(side_effect=reopen)
        return dict(self.args,entry_point='PhaseACombinedPersistence')

    def test_phase_a_sole_owned_save_reopen_and_no_repeat(self):
        args=self.phase_a_setup()
        validate_job(job('run_approved_demo',args,target=None))
        with patch.object(workflow,'modules',return_value=self.module):
            r=self.run_cmd('run_approved_demo',args)
            self.assertEqual(r['outcome'],'PASS');self.assertEqual(r['identity_before'],r['identity_after'])
            self.assertEqual(r['participant_list_persistence'],'UNKNOWN')
            self.assertEqual(r['owner_read_only_action'],args['name'])
            with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
            with self.assertRaises(PolicyError):self.run_cmd('close_demo_design',{'demo_id':'demo-001'})
        self.doc.saveAs.assert_called_once();self.doc.close.assert_called_once_with(False)
        self.app.documents.open.assert_called_once();self.protected.close.assert_not_called()

    def test_phase_a_readonly_measure_dirty_or_identity_change_cannot_pass(self):
        args=self.phase_a_setup()
        def dirty(app,guard):
            self.reopened.isModified=True
            guard()
            self.fail('Guard must refuse')
        self.module.measure_phase_a_reopened.side_effect=dirty
        with patch.object(workflow,'modules',return_value=self.module),self.assertRaises(PolicyError):
            self.run_cmd('run_approved_demo',args)
        self.doc.saveAs.assert_called_once();self.doc.close.assert_called_once()
        with open(os.path.join(self.tmp,'phase_a_persistence.json'),encoding='utf-8') as f:r=json.load(f)
        self.assertEqual(r['outcome'],'FAIL');self.assertEqual(r['participant_list_persistence'],'UNKNOWN')

    def test_phase_a_other_document_refuses_before_geometry_or_save(self):
        self.run_cmd('create_demo_design');self.app.activeDocument=self.doc
        with patch.object(workflow,'modules') as module,self.assertRaises(PolicyError):
            self.run_cmd('run_approved_demo',dict(self.args,entry_point='PhaseACombinedPersistence'))
        module.assert_not_called();self.doc.saveAs.assert_not_called();self.protected.close.assert_not_called()

    def test_phase_a_duplicate_name_and_capacity_refuse_before_save(self):
        args=self.phase_a_setup();self.folder.dataFiles.values=[NS(name=args['name'])]
        with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
        self.doc.saveAs.assert_not_called()
        self.folder.dataFiles.values=[];self.app.data.personalUseLimits.editableFileCount=8
        with self.assertRaises(PolicyError):self.run_cmd('run_approved_demo',args)
        self.doc.saveAs.assert_not_called()

    def test_phase_a_unexpected_tab_after_close_blocks_reopen(self):
        args=self.phase_a_setup()
        def close(save):self.app.documents.values=[self.protected];return True
        self.doc.close.side_effect=close
        with patch.object(workflow,'modules',return_value=self.module),self.assertRaises(PolicyError):
            self.run_cmd('run_approved_demo',args)
        self.app.documents.open.assert_not_called();self.protected.close.assert_not_called()

    def test_phase_a_dirty_save_blocks_close_and_different_version_blocks_measure(self):
        args=self.phase_a_setup();save=self.doc.saveAs.side_effect
        def dirty(*a):save(*a);self.doc.isModified=True;return True
        self.doc.saveAs.side_effect=dirty
        with patch.object(workflow,'modules',return_value=self.module),self.assertRaises(PolicyError):
            self.run_cmd('run_approved_demo',args)
        self.doc.close.assert_not_called()

    def test_zero_document_inspect_is_explicit_and_never_rebases(self):
        spec=importlib.util.spec_from_file_location('phase_a_backend',os.path.join(AUTOMATION,'VanDesignRunner','fusion_backend.py'))
        backend_module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'adsk':fake_adsk,'adsk.core':fake_adsk.core,'adsk.fusion':fake_adsk.fusion}):
            spec.loader.exec_module(backend_module)
        backend=backend_module.FusionBackend(self.app,{'g3_script_dir':'unused','audit_script':'unused'})
        self.app.activeDocument=None;self.app.documents.values=[]
        with patch.dict(sys.modules,{'demo_workflow':workflow}),self.assertRaises(PolicyError):backend.inspect()
        workflow.BASELINE=None
        with patch.dict(sys.modules,{'demo_workflow':workflow}):r=backend.inspect()
        self.assertTrue(r['no_active_design']);self.assertEqual(r['session']['open_documents'],[])
        self.assertNotIn('design_counts',r)
        self.app.documents.values=[self.protected]
        with patch.dict(sys.modules,{'demo_workflow':workflow}),self.assertRaises(backend_module.BackendError):backend.inspect()
        self.app.documents.values=[];self.app.data.personalUseLimits=None
        with patch.dict(sys.modules,{'demo_workflow':workflow}),self.assertRaises(PolicyError):backend.inspect()


    def test_phase_a_reopen_wrong_version_fails_before_post_measurement(self):
        args=self.phase_a_setup();reopen=self.app.documents.open.side_effect
        def wrong(df,active):
            result=reopen(df,active);result.dataFile.versionNumber=2;return result
        self.app.documents.open.side_effect=wrong
        with patch.object(workflow,'modules',return_value=self.module),self.assertRaises(PolicyError):
            self.run_cmd('run_approved_demo',args)
        self.module.measure_phase_a_combined.assert_called_once()
        self.doc.saveAs.assert_called_once();self.doc.close.assert_called_once()

    def test_phase_a_unapproved_arguments_and_existing_unsaved_contract(self):
        validate_job(job('run_approved_demo',dict(demo_id='demo-001',entry_point='PhaseABaseCheckpoint'),target=None))
        for entry in ('TestStorageBox','PhaseABaseCheckpoint'):
            with self.assertRaises(JobSchemaError):
                validate_job(job('run_approved_demo',dict(self.args,entry_point=entry),target=None))
        with self.assertRaises(JobSchemaError):
            validate_job(job('run_approved_demo',dict(demo_id='demo-001',entry_point='PhaseACombinedPersistence'),target=None))
