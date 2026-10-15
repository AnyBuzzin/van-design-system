"""One-shot PR14 Fusion checkpoint; never builds, saves, closes or loads a runner.

Run only with the user's new unsaved Untitled cabinet active. Existing imported
VanDesign modules are inspected before importing any further VanDesign code.
"""
from dataclasses import asdict
from datetime import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import traceback

REPO = Path(__file__).resolve().parents[2]
BUNDLE = Path(r'C:\Users\Buzz\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an-3\work\review-fusion-bundles\VanCabinetJoineryV5')
MANIFEST_SHA = '9dca986105401b2b3c506b151d5d21684057a8f8cc2eece85752705ce66bcb2a'
SPEC_SHA = 'a0a43e005535b33f069dd786dc847682734819a09bd0803650688bb5e4b0a750'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_identity():
    manifest_path = BUNDLE / 'DEPLOYMENT.json'
    if sha(manifest_path) != MANIFEST_SHA:
        raise RuntimeError('Reviewed deployment manifest mismatch')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for relative, expected in manifest['files'].items():
        if sha(BUNDLE / relative) != expected:
            raise RuntimeError('Deployment file mismatch: ' + relative)
    loaded = {}
    for name, module in list(sys.modules.items()):
        if name == 'vandesign' or name.startswith('vandesign.'):
            path = Path(module.__file__).resolve()
            relative = path.relative_to(BUNDLE.resolve()).as_posix()
            if relative not in manifest['files'] or sha(path) != manifest['files'][relative]:
                raise RuntimeError('Unreviewed loaded module: ' + name)
            loaded[name] = {'path': str(path), 'sha256': sha(path)}
    required = {'vandesign', 'vandesign.cad.fusion.adapter',
                'vandesign.cad.fusion.runner', 'vandesign.verification.validate'}
    if not required.issubset(loaded):
        raise RuntimeError('Build runtime is not present in this Fusion process')
    return {'status': 'VERIFIED', 'manifest_sha256': sha(manifest_path),
            'manifest_files_verified': len(manifest['files']), 'loaded_modules': loaded}


def require_test_document(doc, design):
    if not doc or not design or doc.name != 'Untitled' or doc.isSaved:
        raise RuntimeError('Only the new unsaved Untitled test design is permitted')
    if (design.rootComponent.occurrences.count != 8 or design.allComponents.count != 9
            or design.userParameters.count != 16 or design.timeline.count != 28
            or design.timeline.markerPosition != design.timeline.count):
        raise RuntimeError('Active design does not match the disposable baseline')
    parameter = design.userParameters.itemByName('Cab_Width')
    if not parameter or parameter.expression != '1200 mm' or abs(parameter.value * 10 - 1200) > 1e-6:
        raise RuntimeError('Cab_Width no longer matches the approved baseline')
    return parameter


def edit_restore(parameter, measure, record):
    """Always restore the exact expression, including if edited validation raises."""
    original = parameter.expression
    try:
        parameter.expression = '1210 mm'
        record['edited'] = measure('edited')
    finally:
        parameter.expression = original
        record['restored'] = measure('restored')
        record['original_expression_restored'] = parameter.expression == original


def geometry_matches(before, after, epsilon, volume_tolerance):
    if set(before) != set(after):
        return False
    for panel_id in before:
        a, b = before[panel_id], after[panel_id]
        for corner in ('lo', 'hi'):
            if any(abs(x-y) > epsilon for x, y in zip(a['box'][corner], b['box'][corner])):
                return False
        if not math.isclose(a['volume_mm3'], b['volume_mm3'], rel_tol=volume_tolerance, abs_tol=1e-6):
            return False
    return True


def run(context):
    # Fusion API imports belong only to this Fusion-side test entrypoint.
    import adsk.core
    import adsk.fusion
    app = adsk.core.Application.get()
    evidence = REPO / 'docs/integration/pr14-checkpoint-evidence/live-20261015'
    evidence.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    output = evidence / ('checkpoint_' + stamp + '.json')
    result = {'overall': 'UNKNOWN', 'script_sha256': sha(Path(__file__)), 'stages': {}}
    try:
        result['package_identity_before'] = package_identity()
        doc = app.activeDocument
        design = adsk.fusion.Design.cast(app.activeProduct)
        parameter = require_test_document(doc, design)
        from vandesign.cad.fusion.adapter import FusionAdapter
        from vandesign.cad.fusion.runner import _write_report, _raw_sha256
        from vandesign.core.units import MODEL_EPSILON_MM, VOLUME_REL_TOL
        from vandesign.modules.variants import build_variant, profile_limits
        from vandesign.schemas.design_spec import load_design_spec
        from vandesign.verification.validate import validate
        adapter = FusionAdapter(design)
        stored = adapter.stored_spec_json()
        if not stored or hashlib.sha256(stored.encode('utf-8')).hexdigest() != SPEC_SHA:
            raise RuntimeError('Stored cabinet spec differs from approved baseline')
        spec = load_design_spec(stored)
        assembly = build_variant(spec.resolved_params, spec.profile)
        result.update(document_name=doc.name, fusion_version=app.version,
                      is_saved_before=doc.isSaved, original_expression=parameter.expression)
        audit_path = REPO / 'prototypes/claude-v5/tools/VanDesignCutAuditG3/VanDesignCutAuditG3.py'
        audit_spec = importlib.util.spec_from_file_location('pr14_existing_cut_audit', audit_path)
        audit = importlib.util.module_from_spec(audit_spec)
        audit_spec.loader.exec_module(audit)
        result['audit_source_sha256'] = sha(audit_path)

        def measure(stage):
            source = adapter.geometry_source()
            validation = validate(assembly, source, profile_limits=profile_limits(spec.profile),
                                  profile_variant=spec.variant)
            bodies = {}
            for panel in assembly.panels:
                body = source.body(panel.stable_id)
                if body is None:
                    raise RuntimeError('BRep unavailable: ' + panel.stable_id)
                bodies[panel.stable_id] = asdict(body)
            current = adapter.stored_spec_json()
            paths = _write_report(str(evidence), app, design, spec.resolved_params, assembly,
                                  validation, 'measure', design_spec=spec,
                                  stored={'raw_sha256_before': _raw_sha256(stored),
                                          'raw_sha256_after': _raw_sha256(current),
                                          'unchanged': current == stored})
            cuts = audit.run_audit(design, adsk.fusion.FeatureOperations.CutFeatureOperation)
            return {'stage': stage, 'validation': validation.to_dict(), 'bodies': bodies,
                    'cut_audit': cuts, 'reports': paths, 'stored_spec_unchanged': current == stored,
                    'width_mm': parameter.value * 10, 'width_expression': parameter.expression}

        stages = result['stages']
        stages['baseline'] = measure('baseline')
        baseline = stages['baseline']
        if (baseline['validation']['verdict'] != 'PASS'
                or baseline['cut_audit']['overall'] != 'PASS' or not baseline['stored_spec_unchanged']):
            raise RuntimeError('Baseline verification failed; no parameter edit attempted')
        if app.activeDocument != doc:
            raise RuntimeError('Active document changed; no parameter edit attempted')
        edit_restore(parameter, measure, stages)
        result['restored_geometry_matches_baseline'] = geometry_matches(
            baseline['bodies'], stages['restored']['bodies'], MODEL_EPSILON_MM, VOLUME_REL_TOL)
        result['package_identity_after'] = package_identity()
        result['is_saved_after'] = doc.isSaved
        ok = (stages['original_expression_restored'] and result['restored_geometry_matches_baseline']
              and abs(stages['edited']['width_mm'] - 1210) < MODEL_EPSILON_MM
              and abs(stages['restored']['width_mm'] - 1200) < MODEL_EPSILON_MM
              and not doc.isSaved)
        for stage in ('baseline', 'edited', 'restored'):
            entry = stages[stage]
            ok = (ok and entry['validation']['verdict'] == 'PASS'
                  and entry['cut_audit']['overall'] == 'PASS' and entry['stored_spec_unchanged'])
        result['overall'] = 'PASS' if ok else 'FAIL'
    except Exception:
        result['overall'] = 'FAIL'
        result['error'] = traceback.format_exc()
    finally:
        output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    app.userInterface.messageBox('PR14 compatibility checkpoint: ' + result['overall']
                                + '\nEvidence: ' + str(output) + '\nTest design remains unsaved.')
