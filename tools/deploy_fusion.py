"""Create NEW Fusion script bundles from the installed VanDesign distribution.

Run with the interpreter containing the reviewed wheel. Never installs/reloads
Fusion or modifies a runner configuration, queue or existing bundle.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil

import vandesign


def deploy(output):
    output = Path(output).resolve()
    # Refuse all existing targets, including empty directories and symlinks.
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    package = Path(vandesign.__file__).resolve().parent
    repo = Path(__file__).resolve().parents[1]
    sources = {
        'VanCabinetJoineryV5': repo / 'fusion' / 'VanCabinetJoineryV5',
        'FirstInteriorDemo': repo / 'demos' / 'FirstInteriorDemo',
    }
    version = importlib.metadata.version('vandesign')
    distribution = importlib.metadata.distribution('vandesign')
    if Path(distribution.locate_file('vandesign/__init__.py')).resolve() != package / '__init__.py':
        raise RuntimeError('Deploy from an installed wheel, not a historical or editable package')
    if version != vandesign.__version__:
        raise RuntimeError('Distribution/runtime version mismatch')
    # Inventory before creating anything. Only installed package sources ship.
    files = sorted(package.rglob('*.py'))
    if not (package / 'modules' / 'cabinet.py').is_file():
        raise RuntimeError('Installed V5 runtime is incomplete')
    output.mkdir(parents=True, exist_ok=False)
    for name, launcher in sources.items():
        target = output / name
        target.mkdir()
        for suffix in ('.py', '.manifest'):
            shutil.copyfile(launcher / (name + suffix), target / (name + suffix))
        for source in files:
            dest = target / 'vandesign' / source.relative_to(package)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        manifest = {
            'distribution': 'vandesign', 'version': version,
            'generator_id': vandesign.GENERATOR_ID,
            'schema_version': vandesign.SCHEMA_VERSION,
            'files': {
                p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(target.rglob('*')) if p.is_file()
            },
        }
        (target / 'DEPLOYMENT.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', help='New, nonexistent directory')
    print(deploy(parser.parse_args().output))
