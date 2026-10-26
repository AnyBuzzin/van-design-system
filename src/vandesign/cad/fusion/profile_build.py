"""One allowlisted profile fixture through the existing owned Runner session."""
import json
from pathlib import Path

import adsk.core
import adsk.fusion

from .profile_panel import ProfileAdapter, measure_profile_design
from .test_envelope import snapshot
from ...modules.profile_fixture import PARAMETER, request_valid, resolve_profiles, spec_hash, inventory
from ...verification.readback import same_except_readback_noise
from ...manufacturing.dxf import export_profiles


def run_profile_fixture(app,output_dir,guard,request):
    request_valid(request)
    path=Path(output_dir)/'arrangement.json'
    if path.exists():raise RuntimeError('Existing report; no retry')
    payload=dict(outcome='FAIL',stages=[],edits=[],construction_cuts=[])
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        guard();doc=app.activeDocument;design=adsk.fusion.Design.cast(app.activeProduct)
        if doc.isSaved or doc.isModified or design.designType!=adsk.fusion.DesignTypes.ParametricDesignType:
            raise RuntimeError('Fresh empty unsaved parametric fixture required')
        panels=resolve_profiles()
        payload.update(spec_hash=spec_hash(),instances=[p.profile.panel_id for p in panels],inventory=inventory(panels),
                       scope='Fixed XY profiles; thickness only. Geometric 20 mm test, not material qualification.',
                       planned_edits=[dict(parameter=PARAMETER,value_mm=20,expect='pass'),
                                      dict(parameter=PARAMETER,value_mm=5,expect='refused')])
        # Preview every supported edit before geometry creation.
        resolve_profiles({PARAMETER:20})
        try:resolve_profiles({PARAMETER:5})
        except ValueError:pass
        else:raise RuntimeError('Invalid blind-depth preview did not refuse')
        ProfileAdapter(design).compile_profiles(panels,guard,payload['construction_cuts'])
        parameter=design.userParameters.itemByName(PARAMETER);original=parameter.expression
        for label,t in [('baseline',18),('edit_'+PARAMETER,20),('restore_'+PARAMETER,18)]:
            if payload['stages']:
                guard();parameter.expression='20 mm' if t==20 else original;adsk.doEvents()
            stage=measure_profile_design(design,resolve_profiles({PARAMETER:t}),guard,t)
            payload['stages'].append(dict(label=label,**stage))
            if stage['outcome']!='PASS':raise RuntimeError('Profile stage failed; no automatic restoration')
            if label=='baseline':payload['baseline_state']=snapshot(design)
        baseline,restored=payload['stages'][0],payload['stages'][-1]
        comparable=lambda s:{k:v for k,v in s.items() if k!='label'}
        if not same_except_readback_noise(comparable(baseline),comparable(restored)) or snapshot(design)!=payload['baseline_state']:
            raise RuntimeError('Profile restoration differs')
        payload['edits'].append(dict(parameter=PARAMETER,value_mm=20,expect='pass',outcome='PASS'))
        guard()
        try:resolve_profiles({PARAMETER:5})
        except ValueError as exc:refusal=dict(outcome='REFUSED',reason=str(exc))
        else:raise RuntimeError('Invalid depth was not refused')
        stage=measure_profile_design(design,panels,guard,18)
        payload['stages'].append(dict(label='after_refusal_'+PARAMETER,**stage))
        if not same_except_readback_noise(comparable(restored),stage):raise RuntimeError('Refusal changed geometry')
        payload['final_state']=snapshot(design)
        if payload['final_state']!=payload['baseline_state']:raise RuntimeError('Refusal changed state')
        payload['edits'].append(dict(parameter=PARAMETER,value_mm=5,expect='refused',outcome='PASS',preview=refusal))
        # Exactly the same resolved profiles used for CAD expectations; no relief regeneration.
        files=export_profiles([p.profile for p in panels],str(Path(output_dir)/'dxf'))
        payload['dxf']=dict(files=[Path(f).name for f in files],panels=len(panels))
        guard();app.activeViewport.fit();payload['outcome']='PASS'
    except Exception as exc:
        payload['error']=str(exc);raise
    finally:path.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    return str(path)
