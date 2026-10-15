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
        self.protected = NS(name='protected', isValid=True, isSaved=True, isModified=True, isActive=True, saveAs=Mock(), close=Mock())
        self.doc = NS(isSaved=False, isModified=False, isValid=True, isActive=False, saveAs=Mock(), close=Mock())
        root = NS(occurrences=Collection(), bRepBodies=Collection(), sketches=Collection())
        self.design = NS(rootComponent=root, userParameters=Collection(), timeline=Collection())
        self.folder = NS(id='folder-1', name='root', dataFiles=Collection(), dataFolders=Collection())
        project = NS(id='project-1', name='VanDesign', rootFolder=self.folder)
        self.app = NS(data=NS(personalUseLimits=NS(editableFileCount=3, maxEditableFileCount=10),
                              dataProjects=Collection([project])), activeProduct=self.design,
                      documents=NS(add=Mock(side_effect=self.create), count=1, item=lambda i: self.protected), activeViewport=NS(saveAsImageFile=Mock()))
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
