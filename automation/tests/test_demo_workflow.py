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
