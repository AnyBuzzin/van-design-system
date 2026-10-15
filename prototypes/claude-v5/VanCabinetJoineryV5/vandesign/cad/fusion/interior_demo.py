"""Manual, new-document-only interior build and real BRep edit verification."""
import datetime
import json
import os

import adsk.core
import adsk.fusion

from ...modules.interior_demo import LAYOUT_KEYS, VEHICLE_KEYS, build_interior, check_layout, vehicle_clearances
from .adapter import FusionAdapter
from .runner import _design_counts


def measure(design, assembly):
    adapter = FusionAdapter(design)
    source = adapter.geometry_source()
    # Read-only reconstruction for persistence of earlier configured documents.
    # Existing default documents retain their original parameter set.
    if (('Bed_Width' not in assembly.parameters.names() and source.parameter_value('Bed_Width') is not None)
            or ('Arch_Width' not in assembly.parameters.names() and source.parameter_value('Arch_Width') is not None)):
        layout = ({k: source.parameter_value(k) for k in LAYOUT_KEYS if source.parameter_value(k) is not None}
                  if source.parameter_value('Bed_Width') is not None else None)
        vehicle = ({k: source.parameter_value(k) for k in VEHICLE_KEYS if source.parameter_value(k) is not None}
                   if source.parameter_value('Arch_Width') is not None else None)
        assembly = build_interior(layout, vehicle)
    env = assembly.parameters.resolve({p.name: source.parameter_value(p.name)
                                       for p in assembly.parameters.base()})
    expected = check_layout(assembly, env)
    checks = []
    measured_boxes = {}
    for panel in assembly.panels:
        body = source.body(panel.stable_id)
        if body is not None:
            measured_boxes[panel.stable_id] = body.box
        volume = expected[panel.stable_id].volume - sum(
            o.cut.resolve(env).volume for o in assembly.operations
            if o.target_panel_id == panel.stable_id)
        ok = (body is not None and expected[panel.stable_id].max_deviation(body.box)[0] < 0.05
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
        app.activeViewport.fit()
    except Exception as exc:
        payload['outcome'] = 'FAIL'
        payload['error'] = str(exc)
        raise
    finally:
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=2)
    return path
