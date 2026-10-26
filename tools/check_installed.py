"""Run using python -I in a clean environment after installing the wheel."""
import importlib
from importlib import metadata
import json
from pathlib import Path
import sys
import sysconfig

import vandesign
from vandesign.core.joinery import DadoShelf
from vandesign.modules.cabinet import build_cabinet
from vandesign.schemas.cabinet_spec import CabinetSpec

origin = Path(vandesign.__file__).resolve()
assert origin.is_relative_to(Path(sysconfig.get_path('purelib')).resolve()), origin
assert metadata.version('vandesign') == vandesign.__version__ == '0.5.0'
assert vandesign.SCHEMA_VERSION == '0.1'
assert vandesign.GENERATOR_ID == 'vandesign.cabinet@0.5.0'
for name in ('core.expr', 'core.frames', 'core.geometry', 'core.params', 'core.units',
             'components.model', 'components.ids', 'cad.protocol', 'schemas.design_spec',
             'modules.variants', 'modules.interior_demo', 'modules.bed_platform',
             'schemas.bed_platform_spec', 'schemas.storage_box_spec', 'schemas.envelope_spec',
             'modules.test_envelope', 'modules.storage_box', 'modules.rounded_panel',
             'schemas.rounded_panel_spec', 'verification.validate',
             'verification.geometry_source', 'verification.report'):
    module = importlib.import_module('vandesign.' + name)
    assert Path(module.__file__).resolve().is_relative_to(origin.parent)
assert not any(m == 'adsk' or m.startswith('adsk.') for m in sys.modules)
asm = build_cabinet(CabinetSpec())
assert asm.spec_hash == 'a0a43e005535b33f069dd786dc847682734819a09bd0803650688bb5e4b0a750'
assert abs(asm.parameters.resolve()['Cab_Shelf_Length'] - DadoShelf(1200, 18, 6, .3).shelf_length_mm) < 1e-9
print(json.dumps({'installed_origin': str(origin), 'distribution_version': metadata.version('vandesign'),
                  'generator_id': vandesign.GENERATOR_ID, 'legacy_hash': asm.spec_hash,
                  'core_without_adsk': True, 'isolated': bool(sys.flags.isolated)}, indent=2))
