"""Manual, new-document-only interior build and real BRep edit verification."""
import datetime
import json
import math
import os

import adsk.core
import adsk.fusion

from ...modules.interior_demo import LAYOUT_KEYS, VEHICLE_KEYS, build_interior, check_layout, vehicle_clearances
from .adapter import FusionAdapter
from .runner import _design_counts


def measure(design, assembly, composition=False):
    adapter = FusionAdapter(design)
    source = adapter.geometry_source()
    # Read-only reconstruction for persistence of earlier configured documents.
    # Existing default documents retain their original parameter set.
    if not composition and (('Bed_Width' not in assembly.parameters.names() and source.parameter_value('Bed_Width') is not None)
            or ('Arch_Width' not in assembly.parameters.names() and source.parameter_value('Arch_Width') is not None)):
        layout = ({k: source.parameter_value(k) for k in LAYOUT_KEYS if source.parameter_value(k) is not None}
                  if source.parameter_value('Bed_Width') is not None else None)
        vehicle = ({k: source.parameter_value(k) for k in VEHICLE_KEYS if source.parameter_value(k) is not None}
                   if source.parameter_value('Arch_Width') is not None else None)
        assembly = build_interior(layout, vehicle)
    env = assembly.parameters.resolve({p.name: source.parameter_value(p.name)
                                       for p in assembly.parameters.base()})
    expected = ({p.stable_id: p.box.resolve(env) for p in assembly.panels} if composition
                else check_layout(assembly, env))
    checks = []
    measured_boxes = {}
    for panel in assembly.panels:
        body = source.body(panel.stable_id)
        if body is not None:
            measured_boxes[panel.stable_id] = body.box
        volume = expected[panel.stable_id].volume - sum(
            o.cut.resolve(env).volume for o in assembly.operations
            if o.target_panel_id == panel.stable_id)
        ok = (body is not None and all(math.isfinite(v) for v in body.box.lo + body.box.hi + (body.volume_mm3,))
              and expected[panel.stable_id].max_deviation(body.box)[0] < 0.05
              and abs(body.volume_mm3-volume) < max(1, volume*1e-5))
        checks.append(dict(id=panel.stable_id, status="PASS" if ok else "FAIL",
                           expected_volume_mm3=volume,
                           expected_bounds_mm=dict(min=expected[panel.stable_id].lo, max=expected[panel.stable_id].hi),
                           measured_bounds_mm=None if body is None else dict(min=body.box.lo, max=body.box.hi),
                           measured_volume_mm3=None if body is None else body.volume_mm3))
    ids_ok = source.managed_ids() == {p.stable_id: 1 for p in assembly.panels}
    checks.append(dict(id="stable_ids", status="PASS" if ids_ok else "FAIL"))
    for operation in assembly.operations:
        cut = operation.cut.resolve(env)
        point = tuple((a+b)/2 for a, b in zip(cut.lo, cut.hi))
        material = source.point_in_material(operation.target_panel_id, point)
        checks.append(dict(id=operation.operation_id+".empty",
                           status="UNKNOWN" if material is None else "PASS" if material is False else "FAIL"))
    interference = source.interference_count([p.stable_id for p in assembly.panels])
    checks.append(dict(id="body_interference", count=interference,
                       status="UNKNOWN" if interference is None else "PASS" if interference == 0 else "FAIL"))
    if 'Arch_Width' in env:
        try:
            clearances = vehicle_clearances(env, measured_boxes, tolerance_mm=0.05)
            checks.append(dict(id='vehicle_clearances', status='PASS', measured=clearances))
        except (ValueError, KeyError) as exc:
            checks.append(dict(id='vehicle_clearances', status='FAIL', error=str(exc)))
    return dict(outcome="PASS" if all(c['status']=='PASS' for c in checks) else "FAIL",
                parameters_mm=env, checks=checks, counts=_design_counts(design))


def run_demo(app, output_dir, layout_mm=None, vehicle_mm=None):
    doc = app.activeDocument
    design = adsk.fusion.Design.cast(app.activeProduct)
    if (not doc or not design or doc.isSaved or doc.isModified
            or design.rootComponent.occurrences.count or design.rootComponent.bRepBodies.count
            or design.rootComponent.sketches.count or design.userParameters.count
            or design.timeline.count):
        raise RuntimeError("Select a NEW, EMPTY, unmodified, unsaved design. Existing documents are refused.")
    assembly = build_interior(layout_mm, vehicle_mm)
    check_layout(assembly, assembly.parameters.resolve())
    payload = dict(fusion_version=app.version, document_name=doc.name,
                   assembly_id=assembly.assembly_id, layout_mm=layout_mm, vehicle_mm=vehicle_mm, stages=[])
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "interior_%s.json" % datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    try:
        FusionAdapter(design).compile(assembly)
        design.rootComponent.attributes.add("VanDesignInterior", "demo_id", assembly.assembly_id)
        baseline = measure(design, assembly)
        payload['stages'].append(dict(label="baseline", **baseline))
        if baseline['outcome'] != 'PASS':
            raise RuntimeError("Baseline BRep verification failed; see report")
        bed_test_length = max(2*baseline['parameters_mm']['Demo_Ply'], baseline['parameters_mm']['Bed_Length']-100)
        cases = [("Bed_Length", bed_test_length), ("Cab_Width", 1100)]
        if layout_mm is not None:
            cases += [('Kitchen_X', (baseline['parameters_mm']['Kitchen_X']+baseline['parameters_mm']['Demo_Ply'])/2),
                      ('Kitchen_Y', max(0, baseline['parameters_mm']['Kitchen_Y']-50))]
            payload['layout_edit_stages'] = []
        for index, (name, value) in enumerate(cases):
            stages = payload['stages'] if index < 2 else payload['layout_edit_stages']
            param = design.userParameters.itemByName(name)
            original = param.expression
            try:
                param.expression = "%s mm" % value
                adsk.doEvents()
                edited = measure(design, assembly)
                if edited['counts'] != baseline['counts'] or abs(param.value*10-value) > 0.001:
                    edited['outcome'] = 'FAIL'
                    edited['error'] = 'Counts changed or parameter readback mismatch'
                stages.append(dict(label="edit_"+name, **edited))
                if edited['outcome'] != 'PASS':
                    raise RuntimeError("Edited BRep verification failed: " + name)
            finally:
                param.expression = original
                adsk.doEvents()
                restored = measure(design, assembly)
                if restored['counts'] != baseline['counts'] or restored['parameters_mm'] != baseline['parameters_mm']:
                    restored['outcome'] = 'FAIL'
                    restored['error'] = 'Counts or parameters did not restore'
                stages.append(dict(label="restore_"+name, **restored))
            if restored['outcome'] != 'PASS':
                raise RuntimeError("Restored BRep verification failed: " + name)
        payload['outcome'] = 'PASS'
        if vehicle_mm is not None:
            camera = app.activeViewport.camera
            camera.viewOrientation = adsk.core.ViewOrientations.IsoTopRightViewOrientation
            camera.isFitView = True
            app.activeViewport.camera = camera
        app.activeViewport.fit()
    except Exception as exc:
        payload['outcome'] = 'FAIL'
        payload['error'] = str(exc)
        raise
    finally:
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=2)
    return path


def composition_assembly(editable_placement=False):
    from ...composition import compose_layout
    from ...layout_preview import make_layout
    return compose_layout(make_layout([
        dict(instance_id='bed.001', translation_mm=[0, 0, 0]),
        dict(instance_id='cabinet.001', translation_mm=[1500, 0, 0]),
    ]), editable_placement=editable_placement).assembly


def measure_composition(design, assembly, guard):
    """Actual solids plus exact cut participants; no cabinet-spec reinterpretation."""
    from .adapter import ATTR_GROUP, ATTR_ID
    guard()
    result = measure(design, assembly, composition=True)
    checks = result['checks']
    root = design.rootComponent
    components = [design.allComponents.item(i) for i in range(design.allComponents.count)]
    cuts = [f for comp in components for f in
            (comp.features.extrudeFeatures.item(i) for i in range(comp.features.extrudeFeatures.count))
            if f.operation == adsk.fusion.FeatureOperations.CutFeatureOperation]
    expected = {o.operation_id: o.target_panel_id for o in assembly.operations}
    counts = result['counts']
    body_count = sum(c.bRepBodies.count for c in components)
    inventory_ok = (body_count == 11 and root.bRepBodies.count == 0
                    and all(c.bRepBodies.item(i).isSolid for c in components for i in range(c.bRepBodies.count))
                    and counts['root_occurrences'] == 11 and counts['all_components'] == 12
                    and counts['timeline_items'] == 37
                    and counts['user_parameters'] == len(assembly.parameters.params)
                    and sorted(f.name for f in cuts) == sorted(expected)
                    and all(f.healthState == adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState
                            and not f.isSuppressed for c in components for f in
                            (c.features.extrudeFeatures.item(i) for i in range(c.features.extrudeFeatures.count))))
    checks.append(dict(id='composition_inventory', status='PASS' if inventory_ok else 'FAIL',
                       body_count=body_count, cut_names=[f.name for f in cuts]))
    timeline = design.timeline
    marker = timeline.markerPosition
    if marker != timeline.count:
        raise RuntimeError('Unexpected rolled-back timeline; stopped')
    for name, owner in expected.items():
        observation = dict(id=name+'.ownership', status='UNKNOWN', participants=None)
        matches = [f for f in cuts if f.name == name]
        try:
            guard()
            if len(matches) != 1:
                observation['status'] = 'FAIL'
            else:
                feature = matches[0]
                if not feature.timelineObject.rollTo(True):
                    raise RuntimeError('Cannot position timeline for participant readback')
                parts = feature.participantBodies
                ids = []
                for body in parts:
                    attr = body.parentComponent.attributes.itemByName(ATTR_GROUP, ATTR_ID)
                    ids.append(attr.value if attr else None)
                attr = feature.parentComponent.attributes.itemByName(ATTR_GROUP, ATTR_ID)
                observation.update(participants=ids, owner_id=attr.value if attr else None)
                observation['status'] = 'PASS' if ids == [owner] and observation['owner_id'] == owner else 'FAIL'
        except Exception as exc:
            observation['error'] = str(exc)
        finally:
            # Restore only this owned fixture's timeline, not CAD geometry or other documents.
            guard()
            timeline.markerPosition = marker
            if timeline.markerPosition != marker or timeline.count != marker:
                raise RuntimeError('Timeline restoration failed; stopped')
        checks.append(observation)
        if observation['status'] != 'PASS':
            break
    # Measure after timeline restoration, using the assembly-context bodies.
    source = FusionAdapter(design).geometry_source()
    bed = [source.body(p.stable_id) for p in assembly.panels if p.stable_id.startswith('bed.001.')]
    cabinet = [source.body(p.stable_id) for p in assembly.panels if p.stable_id.startswith('cabinet.001.')]
    gap = None if any(b is None for b in bed+cabinet) else min(b.box.lo[0] for b in cabinet)-max(b.box.hi[0] for b in bed)
    expected_gap = result['parameters_mm'].get('Cab_Pos_X', 1500)-result['parameters_mm']['Bed_Width']
    checks.append(dict(id='composition_gap', measured_mm=gap, expected_mm=expected_gap,
                       status='UNKNOWN' if gap is None else 'PASS' if math.isfinite(gap)
                       and ('Cab_Pos_X' in result['parameters_mm'] or gap > 0)
                       and abs(gap-expected_gap) < 0.05 else 'FAIL'))
    if 'Cab_Pos_X' in result['parameters_mm']:
        # Reuse established BRep groove boundary/solid probes and joinery checks.
        from ...verification.validate import validate
        from ...composition import preview_cabinet_placement
        joinery = validate(assembly, source)
        env = result['parameters_mm']
        preview = preview_cabinet_placement(assembly, {p.name: env[p.name] for p in assembly.parameters.base()},
                                            env['Cab_Pos_X'], env['Cab_Pos_Y'])
        checks.append(dict(id='translated_joinery', status=joinery.verdict if preview['outcome'] == 'PASS' else 'FAIL',
                           occupied_envelopes=preview,
                           checks=[c.to_dict() for c in joinery.checks]))
    guard()
    expected_checks = 20 if 'Cab_Pos_X' in result['parameters_mm'] else 19
    result['outcome'] = 'PASS' if len(checks) == expected_checks and all(c['status'] == 'PASS' for c in checks) else 'FAIL'
    return result


def move_composition(design, assembly, x_mm, y_mm, guard, restore_expressions=None):
    """Preview before any setter. Only the existing session guard grants access."""
    from ...composition import preview_cabinet_placement
    guard()
    source = FusionAdapter(design).geometry_source()
    current = {p.name: source.parameter_value(p.name) for p in assembly.parameters.base()}
    preview = preview_cabinet_placement(assembly, current, x_mm, y_mm)
    if preview['outcome'] != 'PASS':
        return preview
    intermediate = preview_cabinet_placement(assembly, current, x_mm, current['Cab_Pos_Y'])
    if intermediate['outcome'] != 'PASS':
        return dict(intermediate, reason='X-first intermediate placement overlaps; no parameters changed')
    # Validate restore expressions before either setter; never accept arbitrary job expressions.
    if restore_expressions is not None and set(restore_expressions) != {'Cab_Pos_X', 'Cab_Pos_Y'}:
        raise RuntimeError('Incomplete original placement expressions')
    for name, value in (('Cab_Pos_X', x_mm), ('Cab_Pos_Y', y_mm)):
        guard()
        param = design.userParameters.itemByName(name)
        param.expression = restore_expressions[name] if restore_expressions else '%s mm' % value
        adsk.doEvents()
        guard()
        if not math.isfinite(param.value) or abs(param.value*10-value) > 0.001:
            raise RuntimeError('Placement readback mismatch; no automatic rollback')
    return preview


def composition_placement_sequence(design, assembly, guard, result=None):
    """One valid move/restore and one occupied-envelope refusal; no fault injection."""
    def snapshot():
        guard()
        ups = design.userParameters
        return dict(parameters={ups.item(i).name: (ups.item(i).expression, ups.item(i).value)
                                for i in range(ups.count)},
                    timeline=(design.timeline.count, design.timeline.markerPosition))
    original = snapshot()
    baseline = measure_composition(design, assembly, guard)
    if baseline['outcome'] != 'PASS':
        raise RuntimeError('Placement baseline is not verified')
    initial = baseline['parameters_mm']
    expressions = {n: original['parameters'][n][0] for n in ('Cab_Pos_X', 'Cab_Pos_Y')}
    if result is None:
        result = dict(stages=[], refusal=None)
    for label, x, y, restore in [('edit_cabinet_position',1600,100,None),
                               ('restore_cabinet_position',initial['Cab_Pos_X'],initial['Cab_Pos_Y'],expressions)]:
        preview = move_composition(design, assembly, x, y, guard, restore)
        stage = dict(label=label, preview=preview, outcome='UNKNOWN')
        result['stages'].append(stage)
        if preview['outcome'] != 'PASS':
            raise RuntimeError('Valid placement unexpectedly refused')
        stage.update(measure_composition(design, assembly, guard))
        actual = stage['parameters_mm']
        if (stage['outcome'] != 'PASS' or stage['counts'] != baseline['counts']
                or any(abs(actual[n]-v) > 0.001 for n,v in preview['parameters_mm'].items())):
            raise RuntimeError('Translated geometry/counts/parameters failed; stopped')
    if snapshot() != original:
        raise RuntimeError('Original parameter expressions/timeline did not restore')
    before = measure_composition(design, assembly, guard)
    before_state = snapshot()
    refusal = dict(outcome='UNKNOWN', before=before, state_before=before_state)
    result['refusal'] = refusal
    if before['outcome'] != 'PASS':
        raise RuntimeError('Pre-refusal measurement failed; no placement request made')
    refused = move_composition(design, assembly, 100, 100, guard)
    refusal['preview'] = refused
    after = measure_composition(design, assembly, guard)
    unchanged = (before['outcome'] == after['outcome'] == 'PASS'
                 and snapshot() == before_state and before == after)
    refusal.update(after=after, state_after=snapshot(),
                   outcome='PASS' if refused['outcome'] == 'REFUSED' and unchanged else 'FAIL')
    if result['refusal']['outcome'] != 'PASS':
        raise RuntimeError('Overlap refusal changed the fixture or did not refuse')
    return result


def run_composition_demo(app, output_dir, guard):
    """Fixed Runner entry point. Stop on failure, leaving the unsaved fixture intact."""
    guard()
    doc = app.activeDocument
    design = adsk.fusion.Design.cast(app.activeProduct)
    from .shelf_regeneration import require_empty
    require_empty(design)
    if doc.isSaved or doc.isModified or design.designType != adsk.fusion.DesignTypes.ParametricDesignType:
        raise RuntimeError('Composition requires an empty unsaved parametric design')
    assembly = composition_assembly(editable_placement=True)
    path = os.path.join(output_dir, 'composition.json')
    if os.path.exists(path):
        raise RuntimeError('Composition result already exists; no retry')
    payload = dict(assembly_id=assembly.assembly_id, spec_hash=assembly.spec_hash,
                   fusion_version=app.version, stages=[], outcome='UNKNOWN')
    try:
        guard()
        FusionAdapter(design).compile(assembly)
        baseline = None
        for name, value in [(None, None), ('Bed_Width', 1300), ('Bed_Width', None),
                            ('Cab_Width', 1100), ('Cab_Width', None)]:
            guard()
            label = 'baseline'
            if name:
                param = design.userParameters.itemByName(name)
                label = ('restore_' if value is None else 'edit_')+name
                param.expression = baseline['expressions'][name] if value is None else '%s mm' % value
                adsk.doEvents()
                guard()
            stage = measure_composition(design, assembly, guard)
            stage['label'] = label
            stage['expressions'] = {n: design.userParameters.itemByName(n).expression for n in ('Bed_Width', 'Cab_Width')}
            payload['stages'].append(stage)
            if baseline is None:
                baseline = stage
                expected_params = assembly.parameters.resolve()
            else:
                overrides = {} if value is None else {name: value}
                expected_params = assembly.parameters.resolve(overrides)
            actual = stage['parameters_mm']
            if (actual.keys() != expected_params.keys()
                    or any(not math.isfinite(actual[n]) or abs(actual[n]-v) > 0.001 for n,v in expected_params.items())
                    or stage['counts'] != baseline['counts']
                    or (name and value is None and stage['expressions'] != baseline['expressions'])):
                stage.update(outcome='FAIL', error='Parameter readback or counts differ')
            if stage['outcome'] != 'PASS':
                raise RuntimeError('Composition verification failed at '+label+'; no automatic restoration')
        guard()
        payload['placement'] = dict(stages=[], refusal=None)
        composition_placement_sequence(design, assembly, guard, payload['placement'])
        guard()
        app.activeViewport.fit()
        payload['outcome'] = 'PASS'
    except Exception as exc:
        payload.update(outcome='FAIL', error=str(exc))
        raise
    finally:
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=2)
    return path


def run_test_envelope(app, output_dir, guard):
    from .test_envelope import run_test_envelope as run
    return run(app, output_dir, guard)


def run_storage_box(app, output_dir, guard):
    from .storage_box import run_storage_box as run
    return run(app, output_dir, guard)


def run_phase_a(app, output_dir, guard, combined=False):
    from .phase_a import run_phase_a as run
    return run(app, output_dir, guard, combined)


def measure_phase_a_combined(app, guard):
    from .phase_a import phase_a_measure
    from .test_envelope import snapshot
    return phase_a_measure(app,guard,True), snapshot(adsk.fusion.Design.cast(app.activeProduct))


def run_dimensioned_cutaway(app, output_dir, guard):
    from .dimensioned_cutaway import run_dimensioned_cutaway as run
    return run(app, output_dir, guard)


def measure_phase_a_reopened(app, guard):
    from .storage_box import measure_storage
    from .test_envelope import snapshot
    from ...modules.storage_box import build_storage_scene
    guard()
    design=adsk.fusion.Design.cast(app.activeProduct)
    report=measure_storage(design,build_storage_scene(),guard,600,read_only_ownership=True)
    guard()
    return report,snapshot(design)
