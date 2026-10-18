"""Fixed Issue #51 Runner entry; only its guarded new unsaved fixture is used."""
import json
import math
from pathlib import Path
import adsk.core
import adsk.fusion

from .adapter import FusionAdapter, ATTR_GROUP, ATTR_ID
from .runner import _design_counts
from ...modules.test_envelope import (build_test_envelope, preview_fit, preview_invalid_arch,
                                      furniture_rows, NOTICE, REFERENCE, ARCHES)
from ...verification.validate import validate


def snapshot(design):
    return dict(parameters={p.name:[p.expression,p.value] for p in
                (design.userParameters.item(i) for i in range(design.userParameters.count))},
                timeline=[design.timeline.count,design.timeline.markerPosition], counts=_design_counts(design))


def measure_test(design, assembly, guard):
    guard()
    source = FusionAdapter(design).geometry_source()
    env = {p.name:source.parameter_value(p.name) for p in assembly.parameters.params}
    if any(v is None or not math.isfinite(v) for v in env.values()):
        raise RuntimeError("Incomplete finite parameter measurements")
    bodies = {p.stable_id:source.body(p.stable_id) for p in assembly.panels}
    if any(b is None or not all(math.isfinite(v) for v in b.box.lo+b.box.hi+(b.volume_mm3,))
           for b in bodies.values()):
        raise RuntimeError("Incomplete finite body measurements")
    report = validate(assembly, source)
    checks = [c.to_dict() for c in report.checks]
    def check(name, ok, **data):
        checks.append(dict(check_id=name,status="PASS" if ok else "FAIL",**data))
    clearance = preview_fit(assembly, env, {k:b.box for k,b in bodies.items()})
    check('test_clearances', abs(clearance['deck_to_arch_mm']-382)<0.01
          and abs(clearance['nominal_right_strip_mm']-634)<0.01, observed=clearance)
    ids = [p.stable_id for p in assembly.panels if not p.stable_id.startswith(REFERENCE)]
    count = source.interference_count(ids)
    check('furniture_interference', count==0, observed=count)
    for arch in ARCHES:
        count = source.interference_count(ids+[arch])
        check(arch+'.interference', count==0, observed=count)
    components = [design.allComponents.item(i) for i in range(design.allComponents.count)]
    cuts = [f for c in components for f in
            (c.features.extrudeFeatures.item(i) for i in range(c.features.extrudeFeatures.count))
            if f.operation==adsk.fusion.FeatureOperations.CutFeatureOperation]
    counts = _design_counts(design)
    check('inventory', sum(c.bRepBodies.count for c in components)==16
          and design.rootComponent.bRepBodies.count==0
          and counts['root_occurrences']==16 and counts['all_components']==17
          and counts['timeline_items']==52 and counts['user_parameters']==len(assembly.parameters.params)
          and all(c.bRepBodies.item(i).isSolid for c in components for i in range(c.bRepBodies.count))
          and all(f.healthState==adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState
                  and not f.isSuppressed for c in components for f in
                  (c.features.extrudeFeatures.item(i) for i in range(c.features.extrudeFeatures.count)))
          and sorted(f.name for f in cuts)==sorted(o.operation_id for o in assembly.operations), observed=counts)
    marker=design.timeline.markerPosition
    if marker!=design.timeline.count:
        raise RuntimeError("Unexpected rolled-back timeline")
    for op in assembly.operations:
        found=[f for f in cuts if f.name==op.operation_id]
        if len(found)!=1: raise RuntimeError("Ambiguous cut ownership")
        feature=found[0]
        try:
            guard()
            if not feature.timelineObject.rollTo(True): raise RuntimeError("Cut readback failed")
            owners=[]
            for body in feature.participantBodies:
                attr=body.parentComponent.attributes.itemByName(ATTR_GROUP,ATTR_ID)
                owners.append(attr.value if attr else None)
            attr=feature.parentComponent.attributes.itemByName(ATTR_GROUP,ATTR_ID)
            check(op.operation_id+'.ownership', owners==[op.target_panel_id]
                  and attr is not None and attr.value==op.target_panel_id, participants=owners)
        finally:
            guard(); design.timeline.markerPosition=marker
            if design.timeline.markerPosition!=marker or design.timeline.count!=marker:
                raise RuntimeError("Timeline restoration failed")
    guard()
    return dict(outcome="PASS" if checks and all(c['status']=='PASS' for c in checks) else "FAIL",
                checks=checks, parameters_mm=env, counts=counts,
                bodies={k:dict(min=b.box.lo,max=b.box.hi,volume_mm3=b.volume_mm3) for k,b in bodies.items()})


def run_test_envelope(app, output_dir, guard):
    payload=dict(outcome="FAIL", notice=NOTICE, before=None, after=None, refusal=None)
    path=Path(output_dir)/'test_envelope.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        guard()
        design=adsk.fusion.Design.cast(app.activeProduct)
        doc=app.activeDocument
        if (doc.isSaved or doc.isModified or design.rootComponent.occurrences.count
                or design.rootComponent.bRepBodies.count or design.userParameters.count or design.timeline.count):
            raise RuntimeError("New empty unsaved parametric fixture required")
        assembly=build_test_envelope()  # pure preflight before geometry
        preview_fit(assembly,assembly.parameters.resolve())
        guard()
        FusionAdapter(design).compile(assembly)
        payload.update(assembly_id=assembly.assembly_id,spec_hash=assembly.spec_hash,
                       furniture_cut_list=furniture_rows(assembly))
        payload['before']=measure_test(design,assembly,guard)
        if payload['before']['outcome']!='PASS': raise RuntimeError("Baseline measurement failed")
        payload['state_before']=snapshot(design)
        guard()
        payload['refusal']=preview_invalid_arch(assembly,payload['before']['parameters_mm'])
        if payload['refusal']['outcome']!='REFUSED': raise RuntimeError("Unsafe placement not refused")
        payload['after']=measure_test(design,assembly,guard)
        payload['state_after']=snapshot(design)
        if payload['after']!=payload['before'] or payload['state_after']!=payload['state_before']:
            raise RuntimeError("Refusal changed geometry or parameters/timeline")
        guard()
        app.activeViewport.fit()
        payload['outcome']='PASS'
    except Exception as exc:
        payload['error']=str(exc)
        raise
    finally:
        path.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    return str(path)
