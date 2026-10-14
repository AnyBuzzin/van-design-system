"""C3: Fusion-side census against a mocked adsk object graph (offline; NOT real Fusion)."""
import subprocess
import sys
import textwrap
import unittest

from core_path import SCRIPT_DIR


class AdapterCensusMock(unittest.TestCase):
    def test_census_counts_multiplicity_and_is_read_only(self):
        script = textwrap.dedent("""
            import sys, types
            adsk = types.ModuleType('adsk'); adsk.core = types.ModuleType('adsk.core'); adsk.fusion = types.ModuleType('adsk.fusion')
            sys.modules.update({'adsk': adsk, 'adsk.core': adsk.core, 'adsk.fusion': adsk.fusion})
            sys.path.insert(0, __SCRIPT_DIR__)
            from vandesign.cad.fusion.adapter import FusionGeometrySource
            from types import SimpleNamespace as N

            class Attrs:
                def __init__(self, value): self.value = value; self.writes = 0
                def itemByName(self, group, name):
                    assert (group, name) == ('VanDesign', 'stable_id'), (group, name)
                    return None if self.value is None else N(value=self.value)
                def add(self, *a): self.writes += 1; raise AssertionError('census must not write')
            def occ(v): return N(component=N(attributes=Attrs(v)))
            def root(values):
                occs = [occ(v) for v in values]
                return N(occurrences=N(count=len(occs), item=occs.__getitem__))

            def src(values): return FusionGeometrySource(N(rootComponent=root(values)))
            assert src(['a', 'b', None, 'c']).managed_ids() == {'a': 1, 'b': 1, 'c': 1}
            assert src(['a', 'a', 'b']).managed_ids() == {'a': 2, 'b': 1}
            assert src([]).managed_ids() == {}
            s = src(['a'])
            def boom(i): raise RuntimeError('api')
            s.design = N(rootComponent=N(occurrences=N(count=1, item=boom)))
            assert s.managed_ids() is None and any('census failed' in d for d in s.diagnostics)
            print('CENSUS MOCK PASSED')
        """).replace('__SCRIPT_DIR__', repr(SCRIPT_DIR))
        r = subprocess.run([sys.executable, '-I', '-c', script], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('CENSUS MOCK PASSED', r.stdout)


if __name__ == '__main__':
    unittest.main()
