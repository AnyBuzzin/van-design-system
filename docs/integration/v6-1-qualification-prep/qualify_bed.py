"""PINNED PREPARATION ONLY. Requires independent review and final owner approval.
One new unsaved bed; no caller-controlled paths, model arguments or commands.
"""
import hashlib
import importlib.util
import importlib
import json
import math
from pathlib import Path
import sys
import traceback

CANDIDATE = Path(r'C:\Users\Buzz\Documents\VanDesign-V6-1-offline-20261018\live-candidate-20261018\VanCabinetJoineryV5')
MANIFEST_SHA = 'f12c7ce95cf28ea8590b0036260be18b95c5e41ae712b459a1ddd0357ba79dab'
RUNNER = Path(r'C:\Users\Buzz\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\VanDesignRunner')
QUEUE = Path(r'C:\Users\Buzz\Documents\VanDesign-Runner\queue')
OUTPUT = Path(r'C:\Users\Buzz\Documents\VanDesign-V6-1-live-qualification-20261018')
NAME = 'VanDesign-V6-1-bed-unsaved-20261018'
ALIAS = '_vandesign_v61_qualification'
IDS = ('bed.deck.001', 'bed.front.001', 'bed.rear.001')


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_inventory(root):
    return {p.relative_to(root).as_posix(): digest(p.read_bytes())
            for p in root.rglob('*') if p.is_file()}


def module_inventory(prefixes):
    return {k: v for k, v in sys.modules.items()
            if any(k == p or k.startswith(p + '.') for p in prefixes)}


def verify_candidate():
    raw = (CANDIDATE / 'DEPLOYMENT.json').read_bytes()
    require(digest(raw) == MANIFEST_SHA, 'Candidate manifest changed')
    files = json.loads(raw)['files']
    for name, expected in files.items():
        path = (CANDIDATE / name).resolve()
        require(path.is_relative_to(CANDIDATE.resolve()), 'Invalid candidate path')
        require(digest(path.read_bytes()) == expected, 'Candidate bytes changed: ' + name)
    require({p.relative_to(CANDIDATE).as_posix() for p in CANDIDATE.rglob('*.py')}
            == {p for p in files if p.endswith('.py')}, 'Unexpected candidate Python source')
    return files


def queue_clear():
    require(not list((QUEUE / 'inbox').iterdir()) and not list((QUEUE / 'claimed').iterdir()),
            'Pending Runner work')
    require(not json.loads((QUEUE / 'runner/heartbeat.json').read_text())['busy'], 'Runner busy')
    for path in (QUEUE / 'journal').glob('*.json'):
        require(not json.loads(path.read_text()).get('entries'), 'Unresolved journal')


def document_state(doc):
    require(doc.isValid is True, 'Document invalidated')
    name, saved, modified = doc.name, doc.isSaved, doc.isModified
    require(isinstance(name, str) and bool(name.strip()), 'Document name unavailable')
    require(type(saved) is bool and type(modified) is bool, 'Document state unavailable')
    data = doc.dataFile
    identity, version, read_only = None, None, None
    if saved:
        require(data is not None, 'Saved document has no data file')
        identity, version, read_only = data.id, data.versionNumber, data.isReadOnly
        require(isinstance(identity, str) and bool(identity.strip()), 'Saved identity unavailable')
        require(type(version) is int and version > 0, 'Saved version invalid')
        require(type(read_only) is bool, 'Saved editability unavailable')
    else:
        require(data is None, 'Unsaved document has contradictory saved identity')
    return dict(name=name, saved=saved, modified=modified,
                identity_sha256=digest(identity.encode()) if saved else None,
                version=version, read_only=read_only)


def capacity_state(app, documents):
    limits = app.data.personalUseLimits
    require(limits is not None, 'Editable capacity unavailable')
    used, maximum = limits.editableFileCount, limits.maxEditableFileCount
    require(type(used) is int and type(maximum) is int,
            'Editable capacity must contain integer counts')
    require(0 <= used <= maximum and maximum > 0, 'Editable capacity invalid')
    identities = [d['identity_sha256'] for d in documents if d['saved']]
    require(len(set(identities)) == len(identities), 'Duplicate saved document identity')
    require(sum(d['saved'] and not d['read_only'] for d in documents) <= used,
            'Editable capacity contradicts open saved documents')
    # Full capacity is valid: this qualification never saves its new fixture.
    return dict(used=used, maximum=maximum)


def equivalent(left, right):
    # Relative1e-6 for volume/area; absolute1e-6 for near-zero values.
    # Every snapshot independently enforces bounds0.01mm/parameters1e-6mm.
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isfinite(left) and math.isfinite(right) and math.isclose(left, right, rel_tol=1e-6, abs_tol=1e-6)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equivalent(left[k],right[k]) for k in left)
    if isinstance(left, (tuple,list)) and isinstance(right, (tuple,list)):
        return len(left)==len(right) and all(equivalent(a,b) for a,b in zip(left,right))
    return left == right


def run(context):
    import adsk.core
    import adsk.fusion
    app = adsk.core.Application.get()
    require(app is not None, 'Fusion application missing')
    require(not OUTPUT.exists(), 'One-shot evidence path already exists; no retry')
    require(not module_inventory((ALIAS,)), 'Candidate namespace already loaded')
    original_modules = module_inventory(('vandesign', 'fusion_backend', 'vdrunner'))
    original_path = list(sys.path)
    original_bytecode = sys.dont_write_bytecode
    originals = [app.documents.item(i) for i in range(app.documents.count)]
    before = [document_state(d) for d in originals]
    capacity = capacity_state(app, before)
    require(not any(d.name == NAME for d in originals), 'Fixture name already open')
    original_files = file_inventory(RUNNER)
    require(digest(json.dumps(original_files, sort_keys=True).encode()) == '3bb69fd87377d74543b59d1b003c54025f49186b75f747c6dc16b86330c16924', 'Original installation differs from reviewed preparation')
    journal_files = file_inventory(QUEUE / 'journal')
    config = json.loads((RUNNER / 'config.json').read_text())
    require(Path(config['queue_root']).resolve() == QUEUE.resolve(), 'Queue path mismatch')
    scripts = app.scripts.itemsByName('VanDesignRunner')
    require(len(scripts) == 1 and scripts[0].isRunning, 'Original Runner not running')
    queue_clear()
    candidate_files = verify_candidate()
    for name, module in original_modules.items():
        path = Path(module.__file__).resolve()
        if name == 'vandesign' or name.startswith('vandesign.'):
            base = Path(config['g3_script_dir']).resolve()
            manifest = json.loads((base / 'DEPLOYMENT.json').read_text())['files']
            require(path.is_relative_to(base) and digest(path.read_bytes()) == manifest[path.relative_to(base).as_posix()], 'Original module source mismatch')
        else:
            require(path.is_relative_to(RUNNER.resolve()), 'Runner module outside installation')
    require('fusion_backend' in original_modules and 'vandesign' in original_modules,
            'Original active sources unavailable; stop for read-only preflight')
    OUTPUT.mkdir()  # exclusive one-shot marker; never removed
    report = dict(outcome='UNKNOWN', stages=[], before=before,
                  candidate_manifest_sha256=MANIFEST_SHA, runner_files=original_files,
                  capacity=capacity,
                  capacity_discrepancy='UNKNOWN; no save or editability change proposed')
    doc = None

    def record():
        (OUTPUT / 'qualification.json').write_text(json.dumps(report, indent=2, allow_nan=False))

    def guard():
        require([document_state(d) for d in originals] == before, 'Protected document changed')
        require(capacity_state(app, before) == capacity, 'Editable capacity changed')
        current = [app.documents.item(i) for i in range(app.documents.count)]
        require(current == originals + ([doc] if doc is not None else []), 'Unexpected document operation')
        queue_clear()
        if doc is not None:
            require(doc.isValid and app.activeDocument == doc and not doc.isSaved and doc.dataFile is None,
                    'Fixture is not the exact active unsaved document')

    try:
        sys.dont_write_bytecode = True
        package = CANDIDATE / 'vandesign'
        spec = importlib.util.spec_from_file_location(ALIAS, package / '__init__.py',
                                                     submodule_search_locations=[str(package)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[ALIAS] = module
        spec.loader.exec_module(module)
        bed_spec = importlib.import_module(ALIAS + '.schemas.bed_platform_spec').BedPlatformSpec
        build = importlib.import_module(ALIAS + '.modules.bed_platform').build_bed_platform
        adapter_class = importlib.import_module(ALIAS + '.cad.fusion.adapter').FusionAdapter
        assembly = build(bed_spec())
        imported = {}
        for name, module in module_inventory((ALIAS,)).items():
            path = Path(module.__file__).resolve()
            rel = path.relative_to(CANDIDATE.resolve()).as_posix()
            require(digest(path.read_bytes()) == candidate_files[rel], 'Loaded candidate source mismatch')
            imported[name] = dict(path=str(path), sha256=digest(path.read_bytes()))
        report['candidate_imports'] = imported
        guard()
        # The only document creation. Never accepts an active/caller-supplied design.
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        guard()
        doc.name = NAME
        design = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
        require(design is not None and design.designType == adsk.fusion.DesignTypes.ParametricDesignType,
                'New design is not parametric')
        root = design.rootComponent
        require(root.occurrences.count == root.bRepBodies.count == design.userParameters.count == design.timeline.count == 0,
                'New design is not empty')
        adapter = adapter_class(design)
        guard()
        adapter.compile(assembly)
        adapter.store_spec_json(bed_spec().to_json())
        source = adapter.geometry_source()
        original_components = {}
        require(design.computeAll(), 'Initial recompute failed')

        def snapshot(label, expected):
            guard()
            require(design.designType == adsk.fusion.DesignTypes.ParametricDesignType, 'Design type changed')
            env = expected.parameters.resolve()
            params = {p.name: dict(expression=p.expression, value_mm=p.value*10)
                      for p in (design.userParameters.item(i) for i in range(design.userParameters.count))}
            require(set(params) == set(env), 'Parameter census mismatch')
            require(all(math.isfinite(params[n]['value_mm']) and abs(params[n]['value_mm']-v) <= 1e-6 for n,v in env.items()), 'Parameter mismatch')
            require(source.managed_ids() == {sid:1 for sid in IDS}, 'Stable-ID ownership mismatch')
            require(root.occurrences.count == 3 and root.allOccurrences.count == 3
                    and root.bRepBodies.count == 0 and design.allComponents.count == 4, 'Orphan/extra component or body')
            panels = {}
            contacts = {}
            components = {}
            for i in range(root.occurrences.count):
                comp = root.occurrences.item(i).component
                attr = comp.attributes.itemByName('VanDesign','stable_id')
                require(attr is not None and attr.value in IDS and attr.value not in components, 'Ambiguous component')
                require(comp.bRepBodies.count == 1 and comp.bRepBodies.item(0).isSolid, 'Expected one solid per panel')
                require(comp.sketches.count == comp.features.extrudeFeatures.count == 1
                        and comp.features.count == 1, 'Unexpected panel features')
                if attr.value in original_components:
                    require(comp == original_components[attr.value], 'Panel component replaced')
                else:
                    original_components[attr.value] = comp
                for feature in (comp.sketches.item(0), comp.features.extrudeFeatures.item(0)):
                    require(feature.healthState == adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState, 'Unhealthy feature')
                components[attr.value] = comp
            for panel in expected.panels:
                sid = panel.stable_id
                actual = source.body(sid)
                require(actual is not None, 'Missing measured body')
                nominal = panel.box.resolve(env)
                require(actual.box.max_deviation(nominal)[0] <= .01, 'Panel bounds mismatch: '+sid)
                require(math.isfinite(actual.volume_mm3) and abs(actual.volume_mm3-nominal.volume) <= max(1e-6,nominal.volume*1e-6), 'Volume mismatch: '+sid)
                panels[sid] = dict(lo_mm=actual.box.lo, hi_mm=actual.box.hi, volume_mm3=actual.volume_mm3)
            require(source.interference_count(IDS) == 0, 'Solid interference or unavailable measurement')

            def horizontal_face(sid, z, upward):
                body = components[sid].bRepBodies.item(0)
                matches = []
                for face in (body.faces.item(i) for i in range(body.faces.count)):
                    bb = face.boundingBox
                    if abs(bb.minPoint.z*10-z) <= .01 and abs(bb.maxPoint.z*10-z) <= .01:
                        ok, normal = face.evaluator.getNormalAtPoint(face.pointOnFace)
                        require(ok and abs(normal.x)<1e-6 and abs(normal.y)<1e-6 and abs(normal.z-upward)<1e-6, 'Contact normal unavailable/wrong')
                        require(face.loops.count == 1 and face.edges.count == 4 and all(adsk.core.Line3D.cast(face.edges.item(j).geometry) is not None for j in range(4)), 'Contact face not rectangular')
                        bounds = [bb.minPoint.x*10,bb.minPoint.y*10,bb.maxPoint.x*10,bb.maxPoint.y*10]
                        area = face.area*100
                        require(abs(area-(bounds[2]-bounds[0])*(bounds[3]-bounds[1]))<=max(.01,area*1e-6), 'Contact face area inconsistent')
                        matches.append((bounds,area))
                require(len(matches)==1, 'Ambiguous/missing contact face')
                return matches[0]

            z = env['Bed_Support_Height']
            deck,_ = horizontal_face('bed.deck.001',z,-1)
            for sid in IDS[1:]:
                support,area = horizontal_face(sid,z,1)
                overlap = max(0,min(deck[2],support[2])-max(deck[0],support[0]))*max(0,min(deck[3],support[3])-max(deck[1],support[1]))
                require(abs(overlap-env['Bed_Width']*18)<=.01 and abs(overlap-area)<=.01, 'Contact coverage mismatch')
                contacts[sid] = dict(measured_face_area_mm2=area, projected_overlap_mm2=overlap)
            state = dict(label=label, parameters=params, panels=panels, contacts=contacts,
                         timeline_count=design.timeline.count, stored_spec=adapter.stored_spec_json(),
                         expected_spec_hash=expected.spec_hash, result='PASS')
            report['stages'].append(state)
            record()
            return state

        baseline = snapshot('baseline', assembly)
        for field, name, value in [('width_mm','Bed_Width',1500),('length_mm','Bed_Length',2000),('height_mm','Bed_Height',800)]:
            param = design.userParameters.itemByName(name)
            expression = param.expression
            guard()
            param.expression = str(value)+' mm'
            require(design.computeAll(), 'Edit recompute failed')
            snapshot(name+' changed', build(bed_spec(**{field:value})))
            guard()
            param.expression = expression
            require(design.computeAll(), 'Restore recompute failed')
            restored = snapshot(name+' restored', assembly)
            for key in ('parameters','panels','contacts','timeline_count','stored_spec','expected_spec_hash'):
                require(equivalent(restored[key], baseline[key]), 'Baseline restoration mismatch: '+key)
        guard()
        report['fixture'] = document_state(doc)
        report['outcome'] = 'PASS'
    except Exception:
        report['outcome'] = 'FAIL'
        report['error'] = traceback.format_exc()
        # Preserve any partial model/edit exactly as observed. No model recovery here.
    finally:
        for name in list(module_inventory((ALIAS,))):
            del sys.modules[name]
        sys.dont_write_bytecode = original_bytecode
        try:
            require(sys.path == original_path, 'Python search path changed')
            require(module_inventory(('vandesign','fusion_backend','vdrunner')) == original_modules, 'Original module objects changed')
            require(not module_inventory((ALIAS,)), 'Candidate imports remain')
            require(file_inventory(RUNNER) == original_files, 'Runner installation/config changed')
            require(file_inventory(QUEUE/'journal') == journal_files, 'Historical journal changed')
            require(scripts[0].isRunning, 'Original Runner stopped')
            guard()
            report['environment_restored'] = True
            report['existing_documents_unchanged'] = True
        except Exception:
            report['outcome'] = 'FAIL'
            report['restoration_error'] = traceback.format_exc()
        record()
    require(report['outcome']=='PASS', 'Qualification stopped; preserve fixture and evidence')
