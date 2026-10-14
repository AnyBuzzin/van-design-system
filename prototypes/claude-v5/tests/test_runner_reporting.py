"""Offline test of Fusion report serialization with a mocked adsk package."""
import subprocess
import sys
import textwrap
import unittest

from core_path import SCRIPT_DIR


class RunnerReportTests(unittest.TestCase):
    def test_json_and_text_reports_capture_live_values(self):
        script = textwrap.dedent("""
            import json, pathlib, sys, tempfile, types
            adsk = types.ModuleType('adsk')
            adsk.core = types.ModuleType('adsk.core')
            adsk.fusion = types.ModuleType('adsk.fusion')
            sys.modules.update({'adsk':adsk, 'adsk.core':adsk.core, 'adsk.fusion':adsk.fusion})
            sys.path.insert(0, __SCRIPT_DIR__)
            from vandesign.cad.fusion.runner import _write_report
            from types import SimpleNamespace as N
            params = [N(name='Cab_Width', value=120.0, expression='1200 mm'),
                      N(name='Cab_Dado_Depth', value=0.6, expression='6 mm'),
                      N(name='other_parameter', value=1, expression='1 mm')]
            collection = N(count=len(params), item=params.__getitem__)
            design = N(userParameters=collection)
            app = N(version='Fusion offline mock', activeDocument=N(name='v5-smoke-test'))
            spec = N(to_dict=lambda: {'ok':True})
            assembly = N(assembly_id='abc', spec_hash='deadbeef')
            report = N(to_dict=lambda:{'verdict':'PASS'}, text=lambda:'RESULT: PASS')
            with tempfile.TemporaryDirectory() as folder:
                p_json, p_txt = _write_report(folder, app, design, spec, assembly, report, 'build')
                data = json.loads(pathlib.Path(p_json).read_text())
                text = pathlib.Path(p_txt).read_text()
                assert data['document_name'] == 'v5-smoke-test'
                assert data['fusion_version'] == 'Fusion offline mock'
                assert data['mode'] == 'build'
                assert data['parameters_read_from_fusion']['Cab_Width']['value_mm'] == 1200.0
                assert data['parameters_read_from_fusion']['Cab_Dado_Depth']['value_mm'] == 6.0
                assert 'other_parameter' not in data['parameters_read_from_fusion']
                assert 'Cab_Dado_Depth = 6.0000 mm' in text
                assert 'RESULT: PASS' in text
                assert pathlib.Path(p_txt).name.endswith('_build.txt')
            print('REPORT TEST PASSED')
        """).replace('__SCRIPT_DIR__', repr(SCRIPT_DIR))
        result = subprocess.run([sys.executable, '-I', '-c', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('REPORT TEST PASSED', result.stdout)


if __name__ == '__main__':
    unittest.main()
