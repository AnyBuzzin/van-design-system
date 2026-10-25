"""C4: shipped 0.2 fixture files are exactly the immutable profile defaults."""
import json
import os
import unittest

import core_path  # noqa: F401
from vandesign.modules.variants import get_profile
from vandesign.schemas.design_spec import load_design_spec

SPECS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "specs")


class SpecFiles(unittest.TestCase):
    def test_each_file_loads_and_matches_profile(self):
        for v in ("base", "tall", "overhead"):
            with self.subTest(variant=v):
                with open(os.path.join(SPECS, v + ".json"), "rb") as fh:
                    raw = fh.read()
                d = load_design_spec(raw)
                self.assertEqual((d.variant, d.profile_version, d.original_schema), (v, 1, "0.2"))
                prof = get_profile(v, 1)
                for k, val in prof.defaults.items():
                    self.assertEqual(getattr(d.resolved_params, k), val)
                self.assertEqual(json.loads(raw)["parameters"].keys(), dict(prof.defaults).keys())
                self.assertLess(len(raw), 64 * 1024)
                self.assertNotIn(b"\r", raw)


if __name__ == "__main__":
    unittest.main()
