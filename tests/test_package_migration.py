"""Installed runtime compatibility, source parity and generated deployment tests."""
from dataclasses import FrozenInstanceError, fields
import ast
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
                if source.relative_to(historical).as_posix() == 'cad/fusion/interior_demo.py':
                    # Issue #43 extends this adapter entry module. The original
                    # build/edit sequence remains identical; measure gains an
                    # explicit composition mode, covered by Runner readback tests.
                    old = ast.parse(source.read_text(encoding='utf-8'))
                    new = ast.parse((installed / source.relative_to(historical)).read_text(encoding='utf-8'))
                    functions = {n.name: n for n in new.body if isinstance(n, ast.FunctionDef)}
                    for node in old.body:
                        if isinstance(node, ast.FunctionDef) and node.name != 'measure':
                            self.assertEqual(ast.dump(node), ast.dump(functions[node.name]))
                    # Strip ONLY the three documented opt-in measurement changes
                    # before comparing the original measurement function's AST.
                    original = next(n for n in old.body if isinstance(n, ast.FunctionDef) and n.name == 'measure')
                    modified = functions['measure']
                    self.assertEqual(modified.args.args[-1].arg, 'composition')
                    self.assertEqual(ast.dump(modified.args.defaults[-1]), 'Constant(value=False)')
                    modified.args.args.pop(); modified.args.defaults.pop()
                    for node in ast.walk(modified):
                        if isinstance(node, ast.If) and isinstance(node.test, ast.BoolOp) and ast.unparse(node.test).startswith('not composition and'):
                            node.test = node.test.values[1]
                        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'expected' for t in node.targets):
                            self.assertIsInstance(node.value, ast.IfExp)
                            self.assertEqual(ast.unparse(node.value.test), 'composition')
                            node.value = node.value.orelse
                        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ok' for t in node.targets):
                            # New finite-measurement guard strengthens both modes.
                            self.assertIn('math.isfinite', ast.unparse(node.value.values[1]))
                            node.value.values.pop(1)
                    self.assertEqual(ast.dump(original), ast.dump(modified))
                    continue
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
