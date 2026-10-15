"""Installed runtime compatibility, source parity and generated deployment tests."""
from dataclasses import FrozenInstanceError, fields
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import vandesign
from vandesign.core.joinery import DadoShelf
from vandesign.modules.cabinet import build_cabinet
from vandesign.schemas.cabinet_spec import CabinetSpec

ROOT = Path(__file__).resolve().parents[1]


class MigrationTests(unittest.TestCase):
    def test_v5_runtime_matches_preserved_source(self):
        historical = ROOT / 'prototypes/claude-v5/VanCabinetJoineryV5/vandesign'
        installed = Path(vandesign.__file__).parent
        sources = sorted(historical.rglob('*.py'))
        self.assertGreater(len(sources), 20)
        for source in sources:
            with self.subTest(file=str(source.relative_to(historical))):
                self.assertEqual(source.read_bytes().replace(b'\r\n', b'\n'),
                                 (installed / source.relative_to(historical)).read_bytes().replace(b'\r\n', b'\n'))

    def test_dado_shelf_api_and_canonical_parameters_agree(self):
        self.assertEqual([f.name for f in fields(DadoShelf)],
                         ['cabinet_width_mm', 'plywood_mm', 'dado_depth_mm', 'end_clearance_mm'])
        for width, ply, dado, clearance in ((1200,18,6,.3),(1000,18,10,.3),(1200,15,8,.3),(600,18,6,0)):
            with self.subTest(width=width, ply=ply, dado=dado):
                legacy = DadoShelf(width, ply, dado, clearance)
                params = build_cabinet(CabinetSpec(width_mm=width, ply_mm=ply,
                                                   dado_depth_mm=dado, end_clearance_mm=clearance)).parameters.resolve()
                self.assertAlmostEqual(legacy.shelf_length_mm, params['Cab_Shelf_Length'])
                self.assertAlmostEqual(legacy.shelf_start_x_mm, params['Cab_Shelf_X'])
                self.assertAlmostEqual(legacy.insertion_each_end_mm, dado-clearance)
                legacy.validate()
                with self.assertRaises(FrozenInstanceError):
                    legacy.cabinet_width_mm = 500
        for values in ((36,18,6,.3),(1200,18,18,.3),(1200,18,0,.3),(1200,18,6,-1),(1200,18,6,6)):
            with self.assertRaises(ValueError):
                DadoShelf(*values)

    def test_generated_bundles_and_launchers(self):
        spec = importlib.util.spec_from_file_location('deploy_fusion', ROOT / 'tools/deploy_fusion.py')
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        with tempfile.TemporaryDirectory() as temp:
            historical = ROOT / 'prototypes/claude-v5/VanCabinetJoineryV5/vandesign/__init__.py'
            with patch.object(vandesign, '__file__', str(historical)):
                with self.assertRaises(RuntimeError):
                    tool.deploy(Path(temp) / 'refuse-historical')
            self.assertFalse((Path(temp) / 'refuse-historical').exists())
            output = tool.deploy(Path(temp) / 'new-bundle')
            with self.assertRaises(FileExistsError):
                tool.deploy(output)
            for name in ('VanCabinetJoineryV5', 'FirstInteriorDemo'):
                bundle = output / name
                manifest = json.loads((bundle / 'DEPLOYMENT.json').read_text())
                self.assertEqual(manifest['generator_id'], vandesign.GENERATOR_ID)
                for rel, expected in manifest['files'].items():
                    self.assertEqual(hashlib.sha256((bundle / rel).read_bytes()).hexdigest(), expected)
                # Separate isolated process: bundle must win over installed runtime,
                # reload stale modules, and refuse absent designs without CAD calls.
                code = '''
import importlib.util, pathlib, sys, types
from types import SimpleNamespace as N
bundle = pathlib.Path(sys.argv[1]); name = sys.argv[2]
messages=[]
app=N(activeProduct=None, activeDocument=None, userInterface=N(messageBox=messages.append), log=lambda x: None)
adsk=types.ModuleType('adsk'); adsk.core=types.ModuleType('adsk.core'); adsk.fusion=types.ModuleType('adsk.fusion')
adsk.core.Application=N(get=lambda: app); adsk.fusion.Design=N(cast=lambda x: None)
sys.modules.update({'adsk':adsk,'adsk.core':adsk.core,'adsk.fusion':adsk.fusion,'vandesign':types.ModuleType('vandesign')})
spec=importlib.util.spec_from_file_location('launcher', bundle/(name+'.py'))
launcher=importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
launcher.run(None)
import vandesign
assert pathlib.Path(vandesign.__file__).resolve() == (bundle/'vandesign/__init__.py').resolve()
assert messages, 'missing-design refusal was not surfaced'
assert ('Open a Fusion design first.' in messages if name == 'VanCabinetJoineryV5'
        else 'Existing documents are refused.' in ''.join(messages)), messages
assert not (bundle/'reports').exists(), messages
sys.path.insert(0, sys.argv[3])
sys.path.insert(0, sys.argv[4])
from fusion_backend import FusionBackend
backend=FusionBackend(app, {'g3_script_dir':str(bundle), 'audit_script':'unused'})
modules=backend._g3()
assert pathlib.Path(modules['runner'].__file__).resolve().is_relative_to(bundle)
from demo_workflow import modules as demo_modules
demo=demo_modules({'demo_package_dir':str(bundle)})
assert pathlib.Path(demo.__file__).resolve().is_relative_to(bundle)
print(name, 'bundle import and no-design refusal PASS', messages)
'''
                result = subprocess.run([sys.executable, '-I', '-c', code, str(bundle), name,
                                         str(ROOT / 'automation/VanDesignRunner'), str(ROOT / 'automation')],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
