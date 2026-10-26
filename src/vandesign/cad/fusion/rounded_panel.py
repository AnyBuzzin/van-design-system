"""Fixed E1.1 qualification; invoked only by an owned existing Runner session.

No save, close, retry or automatic restoration on failure. This candidate is
offline-tested only until separately authorised live qualification.
"""
import json
import math
from pathlib import Path

import adsk.core
import adsk.fusion

from .adapter import FusionAdapter
from .runner import _design_counts
from .test_envelope import snapshot
from ...modules.rounded_panel import PANEL_ID, build_rounded_panel, preview_rounded_panel
from ...modules.storage_box import restored_storage_measurements
from ...schemas.rounded_panel_spec import RoundedPanelSpec
from ...verification.validate import validate


def measure_rounded(design, assembly, guard, radius):
    guard()
    source = FusionAdapter(design).geometry_source()
    env = {p.name: source.parameter_value(p.name) for p in assembly.parameters.params}
    preview = preview_rounded_panel(env)  # Reject incomplete/nonfinite readback.
    body = source.body(PANEL_ID)
    if (body is None or not all(type(v) in (int, float) and math.isfinite(v)
                               for v in body.box.lo + body.box.hi + (body.volume_mm3,))
            or min(body.box.size) <= 0 or body.volume_mm3 <= 0):
        raise RuntimeError("Incomplete finite BRep measurements")
    report = validate(assembly, source)
    checks = [c.to_dict() for c in report.checks]

    def check(name, ok, **data):
        checks.append(dict(check_id=name, status="PASS" if ok else "FAIL", **data))

    expected = assembly.parameters.resolve({'Panel_Radius': radius})
    check('rounded.parameters', all(abs(env[k]-v) <= 0.001 for k, v in expected.items()))
    w, l, r = env['Panel_Width'], env['Panel_Length'], env['Panel_Radius']
    # Both sides of the curved boundary, away from the surface. A bounding box
    # or chamfer cannot pass these tests merely by having the right dimensions.
    probes = [('centre', (w/2, l/2, 9), True), ('lower_left', (1, 1, 9), True)]
    for i, angle in enumerate((math.pi/8, math.pi/4, 3*math.pi/8)):
        for label, offset, inside in (('inside', -0.1, True), ('outside', 0.1, False)):
            probes.append(('%s.%s' % (i, label),
                           (w-r+(r+offset)*math.cos(angle), l-r+(r+offset)*math.sin(angle), 9), inside))
    for name, point, expected_inside in probes:
        observed = source.point_in_material(PANEL_ID, point)
        checks.append(dict(check_id='rounded.material.'+name,
                           status='UNKNOWN' if observed is None else 'PASS' if observed is expected_inside else 'FAIL',
                           point_mm=point, observed=observed, expected=expected_inside, object_ids=[PANEL_ID]))
    counts = _design_counts(design)
    root = design.rootComponent
    check('rounded.inventory', counts['root_occurrences'] == 1 and counts['all_components'] == 2
          and counts['timeline_items'] == 3 and counts['user_parameters'] == 3
          and root.bRepBodies.count == 0 and root.sketches.count == 0
          and design.timeline.markerPosition == design.timeline.count, observed=counts)
    if root.occurrences.count != 1:
        raise RuntimeError('Ambiguous rounded panel occurrence')
    comp = root.occurrences.item(0).component
    check('rounded.features', comp.bRepBodies.count == 1 and comp.bRepBodies.item(0).isSolid
          and comp.bRepBodies.item(0).isValid and comp.sketches.count == 1
          and comp.features.count == 1 and comp.features.extrudeFeatures.count == 1)
    sketch = comp.sketches.item(0)
    feature = comp.features.extrudeFeatures.item(0)
    healthy = adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState
    check('rounded.profile', sketch.profiles.count == 1 and sketch.sketchCurves.sketchLines.count == 4
          and sketch.sketchCurves.sketchArcs.count == 1 and sketch.isFullyConstrained
          and sketch.healthState == healthy and feature.healthState == healthy and not feature.isSuppressed
          and feature.operation == adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    guard()
    return dict(outcome='PASS' if checks and all(c['status'] == 'PASS' for c in checks) else 'FAIL',
                checks=checks, parameters_mm=env, counts=counts, preview=preview,
                bodies={PANEL_ID: dict(min=body.box.lo, max=body.box.hi, volume_mm3=body.volume_mm3)})


def run_rounded_panel(app, output_dir, guard):
    path = Path(output_dir) / 'rounded_panel.json'
    if path.exists():
        raise RuntimeError('Existing report; no retry')
    payload = dict(outcome='FAIL', stages=[], refusal=None)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        guard()
        design, doc = adsk.fusion.Design.cast(app.activeProduct), app.activeDocument
        if (doc.isSaved or doc.isModified or design.designType != adsk.fusion.DesignTypes.ParametricDesignType
                or design.rootComponent.occurrences.count or design.rootComponent.bRepBodies.count
                or design.rootComponent.sketches.count or design.userParameters.count or design.timeline.count):
            raise RuntimeError('New empty unsaved parametric fixture required')
        spec = RoundedPanelSpec()
        assembly = build_rounded_panel(spec)
        payload.update(specification=json.loads(spec.to_json()), spec_hash=assembly.spec_hash)
        guard()
        FusionAdapter(design).compile(assembly)
        parameter = design.userParameters.itemByName('Panel_Radius')
        original = parameter.expression
        for radius in (50, 75, 50):
            if payload['stages']:
                preview_rounded_panel(assembly.parameters.resolve({'Panel_Radius': radius}))
                guard()
                parameter.expression = original if radius == 50 else '75 mm'
                adsk.doEvents()
            stage = measure_rounded(design, assembly, guard, radius)
            payload['stages'].append(stage)
            if stage['outcome'] != 'PASS':
                raise RuntimeError('Rounded panel measurement failed; no automatic restoration')
            if len(payload['stages']) == 1:
                payload['baseline_state'] = snapshot(design)
        payload['restored_state'] = snapshot(design)
        if (payload['baseline_state'] != payload['restored_state'] or not
                restored_storage_measurements(payload['stages'][0], payload['stages'][-1])):
            raise RuntimeError('Rounded panel restoration differs')
        guard()
        invalid = dict(payload['stages'][-1]['parameters_mm'], Panel_Radius=600)
        try:
            preview_rounded_panel(invalid)
        except ValueError as exc:
            payload['refusal'] = dict(outcome='REFUSED', radius_mm=600, reason=str(exc))
        else:
            raise RuntimeError('Invalid radius not refused')
        payload['after_refusal'] = measure_rounded(design, assembly, guard, 50)
        payload['final_state'] = snapshot(design)
        if (payload['restored_state'] != payload['final_state'] or not
                restored_storage_measurements(payload['stages'][-1], payload['after_refusal'])):
            raise RuntimeError('Refusal changed geometry or state')
        guard()
        app.activeViewport.fit()
        payload['outcome'] = 'PASS'
    except Exception as exc:
        payload['error'] = str(exc)
        raise
    finally:
        path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return str(path)
