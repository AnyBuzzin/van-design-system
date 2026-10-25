"""One owner-approved live fault, using the installed Executor and per-design journal.
No save/close, class-wide patch, persistent fault flag or queue Python command.
"""
import adsk.core
import sys
import json
import pathlib
from fusion_backend import FusionBackend
from vdrunner.executor import Executor
from vdrunner.journal import RestoreJournal
from vdrunner.shelf_change import equivalent


def run(context):
    app = adsk.core.Application.get()
    st = sys.modules['_vandesign_g4_qualification_20261017']
    assert not getattr(st, 'controlled_attempted', False), 'One attempt only'
    assert app.activeDocument == st.document and st.document.dataFile.id == st.design_id
    assert st.document.dataFile.versionNumber == 1
    assert [st.info(d) for d in st.protected] == st.before
    out = pathlib.Path(r'C:\Users\Buzz\Documents\VanDesign-Runner\issue20-live-20261017T212117Z')
    root = pathlib.Path(r'C:\Users\Buzz\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\VanDesignRunner')
    cfg = json.loads((root / 'config.json').read_text())
    assert [i['design_id'] for i in cfg['allowed_design_ids']] == [st.design_id]
    q = pathlib.Path(cfg['queue_root'])
    assert not list((q/'inbox').iterdir()) and not list((q/'claimed').iterdir())
    journal = RestoreJournal(str(q/'journal'), st.design_id)
    assert not journal.load()['entries']
    backend = FusionBackend(app, cfg)
    assert equivalent(backend.shelf_state()['inventory'], st.baseline)
    original_begin = backend.begin_shelf_regeneration
    handles = []
    fired = []

    def begin(text):
        operation = original_begin(text)
        original_panel = operation.adapter._make_panel
        handles.append(operation)

        def one_shot(panel):
            component = original_panel(panel)
            if not fired:
                assert operation.adapter._structural_created
                assert operation.adapter._structural_created[-1].component == component
                fired.append(panel.stable_id)
                raise RuntimeError('G4_APPROVED_ONE_SHOT_AFTER_CAPTURED_PANEL')
            return component

        operation.adapter._make_panel = one_shot
        return operation

    st.controlled_attempted = True
    backend.begin_shelf_regeneration = begin
    try:
        job = {'schema': 'vandesign.runner.job/1', 'job_id': 'g4-live-20261017-controlled-recovery',
               'command': 'update_shelf_count', 'args': {'new_shelf_count': 2},
               'target': {'design_id': st.design_id, 'document_name': st.name}}
        result = Executor(backend, cfg, str(q/'journal')).run(job, str(out/'controlled-recovery'))
        (out/'controlled-recovery-result.private.json').write_text(json.dumps(result, indent=2))
    finally:
        del backend.__dict__['begin_shelf_regeneration']
        for operation in handles:
            operation.adapter.__dict__.pop('_make_panel', None)
        (out/'controlled-hook-removal.json').write_text(json.dumps({'removed': True, 'injections': fired}))
    assert len(fired) == 1
    assert result['outcome'] == 'FAIL'
    step = result['steps'][0]
    assert 'G4_APPROVED_ONE_SHOT_AFTER_CAPTURED_PANEL' in step['error']
    assert step['recovery']['verified'] is True
    assert not journal.load()['entries']
    assert equivalent(backend.shelf_state()['inventory'], st.baseline)
    assert [st.info(d) for d in st.protected] == st.before
    assert app.documents.count == len(st.protected) + 1
    assert st.document.dataFile.versionNumber == 1
    print(json.dumps({'expected_job_outcome': 'FAIL', 'recovery_verified': True,
                      'baseline_inventory_equal': True, 'journal_clear': True,
                      'injections': len(fired), 'hook_removed': True,
                      'existing_documents_unchanged': True, 'fixture_version': 1}))
