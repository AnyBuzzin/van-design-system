"""Layout regression and parameter edits; real BRep checks run in Fusion script."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'VanCabinetJoineryV5')))
from vandesign.modules.interior_demo import build_interior, check_layout


class InteriorTests(unittest.TestCase):
    def test_layout_and_edits(self):
        assembly = build_interior()
        for overrides in ({}, {'Bed_Length': 1800}, {'Cab_Width': 1100}):
            env = assembly.parameters.resolve(overrides)
            boxes = check_layout(assembly, env)
            self.assertEqual(boxes['bed.deck.001'].size[1], env['Bed_Length'])
            self.assertEqual(boxes['panel.top.001'].size[0], env['Cab_Width']-2*env['Cab_Ply'])
            self.assertEqual(len(boxes), len(set(boxes)))
            for operation in assembly.operations:
                self.assertTrue(boxes[operation.target_panel_id].contains_box(operation.cut.resolve(env)))

    def test_refuse_bad_layout(self):
        assembly = build_interior()
        for edits in ({'Bed_Length': 3900}, {'Van_Width': 1000}, {'Bed_Height': 2100}):
            with self.assertRaises(ValueError):
                check_layout(assembly, assembly.parameters.resolve(edits))


if __name__ == '__main__':
    unittest.main()
