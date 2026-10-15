"""Read-only audit of the reviewed PR14 wheel and generated deployment copies."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

work = Path(sys.argv[1])
wheel = work / 'migration-wheels/vandesign-0.5.0-py3-none-any.whl'
expected = '549ff8843b8966e7339181e9a75d835c8cb5e1d3ac5b20a2954c7adc2bcef80f'
actual = hashlib.sha256(wheel.read_bytes()).hexdigest()
assert actual == expected, (actual, expected)
results = {'wheel_sha256': actual, 'bundles': {}}
with zipfile.ZipFile(wheel) as archive:
    sources = {name: archive.read(name) for name in archive.namelist()
               if name.startswith('vandesign/') and name.endswith('.py')}
    for name in ('VanCabinetJoineryV5', 'FirstInteriorDemo'):
        bundle = work / 'review-fusion-bundles' / name
        manifest = json.loads((bundle / 'DEPLOYMENT.json').read_text())
        inventory = {p.relative_to(bundle).as_posix() for p in bundle.rglob('*')
                     if p.is_file() and p.name != 'DEPLOYMENT.json'
                     and '__pycache__' not in p.parts}
        assert inventory == set(manifest['files']), (name, inventory ^ set(manifest['files']))
        for relative, digest in manifest['files'].items():
            assert hashlib.sha256((bundle / relative).read_bytes()).hexdigest() == digest, relative
        bundled_sources = {relative for relative in inventory if relative.startswith('vandesign/')}
        assert bundled_sources == set(sources)
        for relative, content in sources.items():
            assert (bundle / relative).read_bytes() == content, relative
        results['bundles'][name] = {
            'path': str(bundle), 'manifest_files_verified': len(inventory),
            'package_files_matching_reviewed_wheel': len(sources),
            'manifest_sha256': hashlib.sha256((bundle / 'DEPLOYMENT.json').read_bytes()).hexdigest(),
            'status': 'PASS',
        }
results['status'] = 'PASS'
print(json.dumps(results, indent=2))
