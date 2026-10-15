"""Small lifecycle extension; only live runner-created documents are writable.

Session references are deliberately memory-only. Restart => refuse old sessions.
Jobs never supply Python, module names or local filesystem paths.
"""
import importlib
import json
import os
import sys
import time
import unicodedata

import adsk.core
import adsk.fusion

from vdrunner.policy import PolicyError

SESSIONS = {}


def unchanged(state):
    observed = []
    for doc, before in state.get('existing', []):
        now = dict(name=doc.name, is_saved=doc.isSaved, is_modified=doc.isModified, is_valid=doc.isValid)
        if now != before:
            raise PolicyError("An existing document changed; stopping demo workflow")
        observed.append(now)
    return observed


def capacity(app):
    limits = app.data.personalUseLimits
    if limits is None:
        return {"personal_use": False}
    result = dict(personal_use=True, editable=limits.editableFileCount,
                  limit=limits.maxEditableFileCount)
    if result['editable'] >= result['limit']:
        raise PolicyError("No editable-document capacity; no existing file was changed")
    return result


def destinations(app):
    projects = app.data.dataProjects
    return [dict(project_id=p.id, project_name=p.name, folder_id=p.rootFolder.id,
                 folder_name=p.rootFolder.name,
                 document_names=[p.rootFolder.dataFiles.item(i).name for i in range(p.rootFolder.dataFiles.count)]) for p in
            (projects.item(i) for i in range(projects.count))]


def session(demo_id, allow_saved=False):
    state = SESSIONS.get(demo_id)
    if not state:
        raise PolicyError("Unknown demo session (or runner restarted); existing documents are never adopted")
    doc = state['document']
    if not doc.isValid or not doc.isActive or (doc.isSaved and not allow_saved):
        raise PolicyError("Demo must be active, valid and never previously saved")
    unchanged(state)
    return state, doc


def empty(design, doc):
    root = design.rootComponent
    if (doc.isSaved or doc.isModified or root.occurrences.count or root.bRepBodies.count
            or root.sketches.count or design.userParameters.count or design.timeline.count):
        raise PolicyError("Build requires a new, empty, unmodified, unsaved runner-created design")


def modules(cfg):
    path = cfg.get('demo_package_dir')
    if not path or not os.path.isfile(os.path.join(path, 'vandesign', 'cad', 'fusion', 'interior_demo.py')):
        raise PolicyError("Approved demo package is not configured")
    for name in list(sys.modules):
        if name == 'vandesign' or name.startswith('vandesign.'):
            del sys.modules[name]
    sys.path.insert(0, path)
    try:
        module = importlib.import_module('vandesign.cad.fusion.interior_demo')
    finally:
        sys.path.remove(path)
    if os.path.realpath(module.__file__) != os.path.realpath(os.path.join(path, 'vandesign', 'cad', 'fusion', 'interior_demo.py')):
        raise PolicyError("Unexpected demo module origin")
    return module


def verified(report):
    stages = report.get('stages', [])
    labels = ['baseline', 'edit_Bed_Length', 'restore_Bed_Length', 'edit_Cab_Width', 'restore_Cab_Width']
    extra = report.get('layout_edit_stages', [])
    expected_count = 22 if report.get('vehicle_mm') is not None else 19
    if report.get('layout_mm') is not None and [s.get('label') for s in extra] != [
            'edit_Kitchen_X','restore_Kitchen_X','edit_Kitchen_Y','restore_Kitchen_Y']:
        return False
    return (report.get('outcome') == 'PASS' and [s.get('label') for s in stages] == labels
            and all(s.get('outcome') == 'PASS' and len(s.get('checks', [])) == expected_count
                    and len({c['id'] for c in s['checks']}) == expected_count
                    and all(c.get('status') == 'PASS' for c in s['checks']) for s in stages+extra)
            and stages[-1]['parameters_mm'] == stages[0]['parameters_mm']
            and all(s['counts'] == stages[0]['counts'] for s in stages+extra)
            and (not extra or extra[-1]['parameters_mm'] == stages[0]['parameters_mm']))


def resolve_folder(app, project_id, folder_id):
    projects = app.data.dataProjects
    matches = [projects.item(i) for i in range(projects.count) if projects.item(i).id == project_id]
    if len(matches) != 1:
        raise PolicyError("Project ID does not resolve uniquely")
    todo = [matches[0].rootFolder]
    while todo:
        folder = todo.pop()
        if folder.id == folder_id:
            return folder
        children = folder.dataFolders
        todo.extend(children.item(i) for i in range(children.count))
    raise PolicyError("Folder is not in the explicitly selected project")


def unused(folder, name):
    norm = lambda s: unicodedata.normalize('NFC', s).strip().casefold()
    files = folder.dataFiles
    if any(norm(files.item(i).name) == norm(name) for i in range(files.count)):
        raise PolicyError("Document name already exists; no overwrite or duplicate-name save permitted")


def persistence(backend, design_id, out_dir):
    """Only the explicitly allowlisted, clean, active demo may be closed/reopened."""
    cfg, app = backend.cfg, backend.app
    protected = {x if isinstance(x, str) else x['design_id'] for x in cfg.get('protected_design_ids', [])}
    if design_id in protected or design_id not in cfg.get('demo_persistence_design_ids', []):
        raise PolicyError('Persistence target is not an explicitly approved demonstration')
    doc = app.activeDocument
    if backend.identity().get('design_id') != design_id or not doc.isSaved or doc.isModified:
        raise PolicyError('Persistence requires the exact active saved demo with NO unsaved changes')
    design = adsk.fusion.Design.cast(app.activeProduct)
    marker = design.rootComponent.attributes.itemByName('VanDesignInterior', 'demo_id')
    if not marker or marker.value != 'interior.demo.001':
        raise PolicyError('Persistence target lacks the interior-demo marker')
    module = modules(cfg)
    before = module.measure(design, module.build_interior())
    identity = backend.identity()
    other = dict(existing=[(d, dict(name=d.name, is_saved=d.isSaved, is_modified=d.isModified, is_valid=d.isValid))
                          for d in (app.documents.item(i) for i in range(app.documents.count)) if not d.isActive])
    payload = dict(outcome='UNKNOWN', before=before, identity_before=identity)
    path = os.path.join(out_dir, 'persistence.json')
    try:
        if before['outcome'] != 'PASS' or doc.isModified:
            raise PolicyError('Pre-reopen geometry failed or document became modified')
        data_file = doc.dataFile
        if not data_file.isComplete:
            raise PolicyError('Cloud version is not complete')
        if not doc.close(False):
            raise PolicyError('Clean demo did not close')
        reopened = app.documents.open(data_file, True)
        if not reopened or not reopened.isActive:
            raise PolicyError('Reopen failed; target remains closed, existing designs untouched')
        after = module.measure(adsk.fusion.Design.cast(app.activeProduct), module.build_interior())
        payload.update(after=after, identity_after=backend.identity(), existing_documents=unchanged(other))
        # Compare all measured geometry, allowing harmless floating-point readback noise.
        def close_values(a, b):
            if isinstance(a, dict):
                return isinstance(b, dict) and a.keys() == b.keys() and all(close_values(a[k], b[k]) for k in a)
            if isinstance(a, (list, tuple)):
                return isinstance(b, (list, tuple)) and len(a) == len(b) and all(close_values(x, y) for x, y in zip(a, b))
            if isinstance(a, (int, float)) and not isinstance(a, bool):
                return isinstance(b, (int, float)) and abs(a-b) <= max(1e-6, abs(a)*1e-10)
            return a == b
        same_identity = all(payload['identity_after'].get(k) == identity.get(k) for k in
                            ('fusion_version', 'design_id', 'data_file_name', 'version_number', 'is_saved', 'is_modified'))
        if after['outcome'] != 'PASS' or not close_values(before, after) or not same_identity:
            raise PolicyError('Reopened geometry, parameters, counts or document identity differ')
        payload['outcome'] = 'PASS'
        return payload
    except Exception as exc:
        payload.update(outcome='FAIL', error=str(exc))
        raise
    finally:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=2)


def execute(backend, command, args, out_dir, job_id):
    app = backend.app
    os.makedirs(out_dir, exist_ok=True)
    if command == 'verify_demo_persistence':
        return persistence(backend, args['design_id'], out_dir)
    if command == 'create_demo_design':
        available = capacity(app)
        # Read cloud metadata before opening a tab; unavailable evidence fails closed.
        folders = destinations(app)
        if job_id in SESSIONS:
            raise PolicyError("Demo session already exists")
        existing = [(d, dict(name=d.name, is_saved=d.isSaved, is_modified=d.isModified, is_valid=d.isValid))
                    for d in (app.documents.item(i) for i in range(app.documents.count))]
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        if not doc or not doc.isActive:
            raise PolicyError("New demo document was not activated")
        design = adsk.fusion.Design.cast(app.activeProduct)
        empty(design, doc)
        SESSIONS[job_id] = dict(document=doc, status='created', existing=existing)
        return dict(outcome='PASS', demo_id=job_id, identity=backend.identity(),
                    capacity=available, destinations=folders, existing_documents=unchanged(SESSIONS[job_id]))

    state, doc = session(args['demo_id'], allow_saved=command == 'capture_demo_viewport')
    design = adsk.fusion.Design.cast(app.activeProduct)
    if command == 'run_approved_demo':
        if args['entry_point'] != 'FirstInteriorDemo' or state['status'] != 'created':
            raise PolicyError("Only FirstInteriorDemo in an unused runner session is approved")
        empty(design, doc)
        module = modules(backend.cfg)
        layout = args.get('layout_mm')
        vehicle = args.get('vehicle_mm')
        # Pure preflight runs before the first CAD operation.
        try:
            assembly = (module.build_interior(layout, vehicle_mm=vehicle) if vehicle is not None else
                        module.build_interior(layout) if layout is not None else module.build_interior())
            module.check_layout(assembly, assembly.parameters.resolve())
        except ValueError as exc:
            with open(os.path.join(out_dir, 'layout_refusal.json'), 'w', encoding='utf-8') as fh:
                json.dump(dict(outcome='REFUSED', layout_mm=layout, vehicle_mm=vehicle, reason=str(exc), identity=backend.identity()), fh, indent=2)
            state['status'] = 'layout_refused'
            raise PolicyError(str(exc))
        state['status'] = 'build_attempted'  # Any interruption/failure permanently blocks saving.
        path = (module.run_demo(app, out_dir, layout_mm=layout, vehicle_mm=vehicle) if vehicle is not None else
                module.run_demo(app, out_dir, layout_mm=layout) if layout is not None else module.run_demo(app, out_dir))
        with open(path, encoding='utf-8') as fh:
            report = json.load(fh)
        if not verified(report):
            raise PolicyError("Build verification failed; saving is blocked")
        session(args['demo_id'])
        state.update(status='verified', baseline=report['stages'][0], layout_mm=layout, vehicle_mm=vehicle)
        return dict(outcome='PASS', demo_id=args['demo_id'], report_path=path,
                    verification=report, identity=backend.identity(), existing_documents=unchanged(state))

    if command == 'save_demo_design':
        if state['status'] != 'verified':
            raise PolicyError("Only a successfully verified build can be saved")
        capacity(app)
        folder = resolve_folder(app, args['project_id'], args['folder_id'])
        unused(folder, args['name'])
        module = modules(backend.cfg)
        state['status'] = 'verification_pending'
        assembly = (module.build_interior(state.get('layout_mm'), vehicle_mm=state['vehicle_mm']) if state.get('vehicle_mm') is not None else
                    module.build_interior(state['layout_mm']) if state.get('layout_mm') is not None else module.build_interior())
        fresh = module.measure(design, assembly)
        with open(os.path.join(out_dir, 'presave_geometry.json'), 'w', encoding='utf-8') as fh:
            json.dump(fresh, fh, indent=2)
        if (fresh['outcome'] != 'PASS' or fresh['counts'] != state['baseline']['counts']
                or fresh['parameters_mm'] != state['baseline']['parameters_mm']):
            state['status'] = 'verification_failed'
            raise PolicyError("Fresh geometry differs or fails verification; saving blocked")
        state['status'] = 'verified'
        session(args['demo_id'])
        unused(folder, args['name'])
        state['status'] = 'save_attempted'  # Never retry an uncertain cloud save.
        if not doc.saveAs(args['name'], folder, 'Verified VanDesign interior demonstration', ''):
            raise PolicyError("Fusion saveAs returned false; outcome uncertain, no automatic retry")
        deadline = time.monotonic() + 45
        data_file = None
        while time.monotonic() < deadline:
            adsk.doEvents()
            if doc.isSaved:
                data_file = doc.dataFile
                if data_file and data_file.isComplete:
                    break
            time.sleep(0.1)
        else:
            raise PolicyError("Cloud save completion UNKNOWN; no automatic retry")
        if data_file.name != args['name'] or data_file.parentFolder.id != folder.id or doc.isModified:
            raise PolicyError("Saved identity/location or clean state did not verify")
        state['status'] = 'saved'
        return dict(outcome='PASS', demo_id=args['demo_id'], identity=backend.identity(),
                    project_id=args['project_id'], folder_id=folder.id, data_file_id=data_file.id,
                    cloud_complete=True, geometry=fresh, existing_documents=unchanged(state))

    if command == 'capture_demo_viewport':
        if state['status'] not in ('verified', 'saved'):
            raise PolicyError("Viewport capture requires a verified demo")
        path = os.path.join(out_dir, 'viewport.png')
        if os.path.exists(path):
            raise PolicyError("Viewport evidence already exists")
        if not app.activeViewport.saveAsImageFile(path, 1600, 1000) or not os.path.isfile(path):
            raise PolicyError("Viewport capture failed")
        return dict(outcome='PASS', image_path=path, demo_id=args['demo_id'])
    raise PolicyError("Unsupported demo command")
