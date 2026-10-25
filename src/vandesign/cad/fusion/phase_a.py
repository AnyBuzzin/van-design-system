"""Bounded Phase A measurements; only the owning Runner can invoke lifecycle."""
import json
from pathlib import Path
import adsk.core
import adsk.fusion
from .adapter import FusionAdapter
from .test_envelope import measure_test, snapshot
from .storage_box import measure_storage
from ...modules.variants import get_profile, profile_defaults_spec, build_variant
from ...modules.storage_box import build_storage_scene, restored_storage_measurements


def phase_a_measure(app, guard, combined):
    guard()
    design=adsk.fusion.Design.cast(app.activeProduct)
    if combined:
        return measure_storage(design,build_storage_scene(),guard,600)
    profile=get_profile('base',1)
    return measure_test(design,build_variant(profile_defaults_spec(profile)),guard,
                        expected_panels=8,expected_timeline=28,base_profile=profile)


def run_phase_a(app, output_dir, guard, combined=False):
    path=Path(output_dir)/'phase_a.json'
    if path.exists(): raise RuntimeError('No repeated Phase A execution')
    result=dict(outcome='FAIL',stages=[])
    try:
        guard()
        design=adsk.fusion.Design.cast(app.activeProduct)
        doc=app.activeDocument
        if (doc.isSaved or doc.isModified or design.designType!=adsk.fusion.DesignTypes.ParametricDesignType
                or design.rootComponent.occurrences.count or design.rootComponent.bRepBodies.count
                or design.userParameters.count or design.timeline.count):
            raise RuntimeError('New empty unsaved parametric design required')
        profile=get_profile('base',1)
        assembly=build_storage_scene() if combined else build_variant(profile_defaults_spec(profile))
        FusionAdapter(design).compile(assembly)
        original=None if combined else design.userParameters.itemByName('Cab_Width').expression
        for width in ((None,) if combined else (1200,1210,1200)):
            guard()
            if result['stages']:
                design.userParameters.itemByName('Cab_Width').expression=original if width==1200 else '1210 mm'
                adsk.doEvents();guard()
            stage=phase_a_measure(app,guard,combined)
            result['stages'].append(stage)
            if stage['outcome']!='PASS': raise RuntimeError('Phase A measurement failed; no automatic restore')
            expected=assembly.parameters.resolve({} if combined else {'Cab_Width':width})
            if any(abs(stage['parameters_mm'][k]-v)>1e-6 for k,v in expected.items()):
                raise RuntimeError('Parameter readback mismatch')
            if len(result['stages'])==1:result['state_before']=snapshot(design)
        result['state_after']=snapshot(design)
        if result['state_before']!=result['state_after'] or not restored_storage_measurements(result['stages'][0],result['stages'][-1]):
            raise RuntimeError('Phase A restoration mismatch')
        guard();result['outcome']='PASS'
    except Exception as exc:
        result['error']=str(exc);raise
    finally:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
