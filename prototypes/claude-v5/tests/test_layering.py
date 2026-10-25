import os
import re
import subprocess
import sys
import unittest

from core_path import SCRIPT_DIR, HISTORICAL_SCRIPT_DIR

PKG = os.path.join(SCRIPT_DIR, "vandesign")
FUSION_PKG = os.path.join(PKG, "cad", "fusion")


class LayeringTests(unittest.TestCase):
    def test_adsk_only_imported_in_fusion_package(self):
        offenders = []
        for dirpath, _, files in os.walk(PKG):
            if os.path.abspath(dirpath).startswith(os.path.abspath(FUSION_PKG)):
                continue
            for f in files:
                if f.endswith(".py"):
                    with open(os.path.join(dirpath, f), encoding="utf-8") as fh:
                        text = fh.read()
                    if re.search(r"^\s*(import|from)\s+adsk", text, re.M):
                        offenders.append(os.path.join(dirpath, f))
        self.assertEqual(offenders, [])

    def test_core_imports_without_adsk(self):
        code = (
            "import sys; "
            "import vandesign.modules.cabinet, vandesign.verification.validate, vandesign.cad.protocol; "
            "assert not any(m == 'adsk' or m.startswith('adsk.') for m in sys.modules)"
        )
        subprocess.run([sys.executable, "-I", "-c", code], check=True)

    def test_entrypoint_has_no_business_logic(self):
        with open(os.path.join(HISTORICAL_SCRIPT_DIR, "VanCabinetJoineryV5.py"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertLess(len(text.splitlines()), 50)
        self.assertNotIn("sketch", text.lower())


if __name__ == "__main__":
    unittest.main()
