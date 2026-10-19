"""Fixed storage qualification; never called outside the owned Runner fixture."""
import json
from pathlib import Path
import adsk.core
import adsk.fusion

from .test_envelope import measure_test, snapshot
from .adapter import FusionAdapter
from ...core.geometry import Box
from ...modules.storage_box import build_storage_scene, preview_storage, storage_contacts, preview_invalid_storage
from ...modules.test_envelope import furniture_rows, NOTICE
from ...modules.storage_box import restored_storage_measurements


def measure_storage(design, assembly, guard, width):
    report = measure_test(design,assembly,guard,expected_panels=21,expected_timeline=67)
    env = report['parameters_mm']
    boxes = {k:Box(tuple(v['min']),tuple(v['max'])) for k,v in report['bodies'].items()}
    gaps = preview_storage(assembly,env,boxes)
    contacts = storage_contacts(boxes)
    expected = assembly.parameters.resolve({'Storage_Width':width})
    checks = report['checks']
    checks.append(dict(check_id='storage.parameters',status='PASS' if set(env)==set(expected)
        and all(abs(env[k]-v)<0.001 for k,v in expected.items()) else 'FAIL'))
    for name,ok in contacts.items():
        checks.append(dict(check_id='storage.contact.'+name,status='PASS' if ok else 'FAIL'))
    target = dict(top_to_deck_mm=432,left_arch_gap_mm=396,right_arch_gap_mm=996-width)
    checks.append(dict(check_id='storage.clearances',status='PASS' if all(
        abs(gaps[k]-v)<0.01 for k,v in target.items()) else 'FAIL',observed=gaps))
    report['outcome']='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL'
    return report


def run_storage_box(app, output_dir, guard):
    path=Path(output_dir)/'storage_box.json'
    if path.exists():
        raise RuntimeError('Existing report; no retry')
    payload=dict(outcome='FAIL',notice=NOTICE,stages=[],refusal=None)
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        guard()
        design=adsk.fusion.Design.cast(app.activeProduct)
        doc=app.activeDocument
        if (doc.isSaved or doc.isModified or design.designType!=adsk.fusion.DesignTypes.ParametricDesignType
                or design.rootComponent.occurrences.count or design.rootComponent.bRepBodies.count
                or design.userParameters.count or design.timeline.count):
            raise RuntimeError('New empty unsaved parametric fixture required')
        assembly=build_storage_scene()
        guard()
        FusionAdapter(design).compile(assembly)
        payload.update(assembly_id=assembly.assembly_id,spec_hash=assembly.spec_hash,
                       furniture_cut_list=furniture_rows(assembly))
        original=design.userParameters.itemByName('Storage_Width').expression
        for width in (600,700,600):
            guard()
            if payload['stages']:
                # Validate proposed geometry before writing the one owned parameter.
                env=assembly.parameters.resolve({'Storage_Width':width})
                preview_storage(assembly,env)
                design.userParameters.itemByName('Storage_Width').expression=original if width==600 else '700 mm'
                adsk.doEvents()
                guard()
            stage=measure_storage(design,assembly,guard,width)
            payload['stages'].append(stage)
            if stage['outcome']!='PASS':
                raise RuntimeError('Storage measurement failed; no automatic restoration')
            if len(payload['stages'])==1:
                payload['baseline_state']=snapshot(design)
        payload['restored_state']=snapshot(design)
        if not restored_storage_measurements(payload['stages'][0],payload['stages'][-1]) or payload['baseline_state']!=payload['restored_state']:
            raise RuntimeError('Storage restoration differs')
        payload['before']=payload['stages'][-1]
        payload['state_before']=snapshot(design)
        guard()
        payload['refusal']=preview_invalid_storage(assembly,payload['before']['parameters_mm'])
        if payload['refusal']['outcome']!='REFUSED':
            raise RuntimeError('Unsafe storage placement not refused')
        payload['after']=measure_storage(design,assembly,guard,600)
        payload['state_after']=snapshot(design)
        if payload['before']!=payload['after'] or payload['state_before']!=payload['state_after']:
            raise RuntimeError('Refusal changed geometry or state')
        guard()
        app.activeViewport.fit()
        payload['outcome']='PASS'
    except Exception as exc:
        payload['error']=str(exc)
        raise
    finally:
        path.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    return str(path)
