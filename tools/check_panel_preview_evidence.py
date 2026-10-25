"""Reuse immutable accepted reports; write NEW offline G5 previews and a sidecar.

Run from the reviewed installed wheel interpreter. Does not connect to Fusion.
The sidecar links historical evidence, not the current state of any open document.
"""
import argparse
import json
from pathlib import Path
import sys
import sysconfig
import zipfile

import vandesign
from vandesign.panel_preview import make_preview, canonical_json, csv_text, sha256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_COMMIT = '2da3feb8dd359fe3c0d0e50d6f8fb3568176bb74'
BASE_URL = 'https://github.com/AnyBuzzin/van-design-system/blob/' + EVIDENCE_COMMIT + '/'
G4 = 'docs/integration/g4-shelf-count/live-20261017/'
G3 = 'docs/integration/g3-remaining-verification/'


def artifact(path, member=None):
    raw = (ROOT / path).read_bytes()
    ref = {'url': BASE_URL + path, 'sha256': sha256(raw)}
    if member:
        with zipfile.ZipFile(ROOT / path) as archive:
            raw = archive.read(member)
        ref.update(member=member, member_sha256=sha256(raw))
    return raw, ref


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--wheel', required=True, type=Path)
    args = parser.parse_args()
    package = Path(vandesign.__file__).resolve().parent
    assert package.is_relative_to(Path(sysconfig.get_path('purelib')).resolve())
    # Prove supplied wheel actually contains every loaded package source byte.
    with zipfile.ZipFile(args.wheel) as wheel:
        sources = {p.relative_to(package).as_posix(): sha256(p.read_bytes()) for p in sorted(package.rglob('*.py'))}
        assert all(sha256(wheel.read('vandesign/' + name)) == digest for name, digest in sources.items())
        assert {name for name in wheel.namelist() if name.startswith('vandesign/') and name.endswith('.py')} == {'vandesign/' + name for name in sources}
    args.output.mkdir(parents=True, exist_ok=False)
    sidecar = {'format': 'vandesign.g5-evidence/1', 'source_commit': args.source_commit,
               'wheel_sha256': sha256(args.wheel.read_bytes()), 'package_version': vandesign.__version__,
               'installed_sources_sha256': sources, 'python_version': sys.version,
               'live_operations': 'NOT RUN', 'structural_persistence': 'UNKNOWN; excluded', 'cases': {}}
    cases = []
    for stage in ('to-two', 'to-one'):
        job_path = G4 + 'jobs/g4-live-20261017-' + stage + '/result.json'
        job_raw, job_ref = artifact(job_path)
        verification = json.loads(job_raw)['steps'][0]['post_verification']
        report_dir = ROOT / G4 / ('jobs/g4-live-20261017-' + stage) / 'evidence/00_update_shelf_count/post/reports'
        report_path = next(report_dir.glob('*.json')).relative_to(ROOT).as_posix()
        raw, ref = artifact(report_path)
        cases.append(('base-' + stage, raw, ref, verification, job_ref))
    raw, ref = artifact(G3 + 'report_20261017_011732_786085_build.json')
    cases.append(('overhead-default', raw, ref, None, None))
    raw, ref = artifact('docs/integration/evidence/G3-F2-F3-partial-evidence.zip',
                        'reports/report_20261014_221815_930645_build.json')
    cases.append(('tall-default', raw, ref, None, None))
    for name, raw, ref, verification, job_ref in cases:
        report = json.loads(raw)
        preview = make_preview(report['design_spec_canonical_json'], raw)
        assert preview['evidence']['status'] == 'PASS', (name, preview['evidence'])
        record = {'report': ref, 'historical_report_consistency': preview['evidence']['status'],
                  'document_state': 'UNKNOWN in this report', 'cut_ownership': 'UNKNOWN in this report',
                  'measurement_comparison': 'accepted bbox-deviation checks, <=0.01 mm',
                  'acceptance': 'https://github.com/AnyBuzzin/van-design-system/issues/4#issuecomment-6227536777'}
        if verification:
            state = verification['state']
            observed = state['inventory']['panels']
            assert set(observed) == {row['panel_id'] for row in preview['panels']}
            for row in preview['panels']:
                bounds = observed[row['panel_id']]['bounds_cm']
                sizes = [(b-a)*10 for a,b in zip(*bounds)]
                for axis, dim in [('blank_axis_1','blank_1_mm'), ('blank_axis_2','blank_2_mm'), ('thickness_axis','nominal_thickness_mm')]:
                    assert abs(sizes['XYZ'.index(row[axis])] - float(row[dim])) <= .01
            expected_cuts = {g['operation_id']: g['target_panel_id'] for g in preview['grooves']}
            assert state['inventory']['cuts'] == expected_cuts
            audit = verification['audit']
            assert audit['overall'] == 'PASS' and audit['features_passed'] == audit['features_total'] == len(expected_cuts)
            assert set(audit['operations']) == set(expected_cuts) and all(v == 'PASS' for v in audit['operations'].values())
            record.update(document_state=state['identity'], cut_ownership=audit,
                          state_and_ownership_source=job_ref, measurement_comparison='PASS; raw BRep bounds converted cm to mm',
                          acceptance='https://github.com/AnyBuzzin/van-design-system/pull/22#pullrequestreview-5560245734')
        for suffix, text in [('json', canonical_json(preview)), ('csv', csv_text(preview))]:
            data = text.encode('utf-8')
            (args.output / (name + '.' + suffix)).write_bytes(data)
            record[suffix + '_sha256'] = sha256(data)
        sidecar['cases'][name] = record
    for key, path in [('historical_g4_package', G4 + 'candidate-source-proof.json'),
                      ('historical_g3_package', G3 + 'live-module-provenance.json'),
                      ('g4_restoration', G4 + 'restoration-extra-proof.json')]:
        sidecar[key] = artifact(path)[1]
    (args.output / 'TRACEABILITY.json').write_text(canonical_json(sidecar), encoding='utf-8', newline='\n')
    print('PASS: four accepted configurations; no live operations')


if __name__ == '__main__':
    main()
