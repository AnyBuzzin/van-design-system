"""Layout regression and parameter edits; real BRep checks run in Fusion script."""
import os
import sys
import unittest

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

    def test_configurable_dimensions_and_placement(self):
        assembly = build_interior(dict(Bed_Width=1500, Bed_Length=2000, Bed_Height=650,
                                       Kitchen_X=200, Kitchen_Y=600))
        env = assembly.parameters.resolve()
        boxes = check_layout(assembly, env)
        self.assertEqual(boxes['bed.deck.001'].lo, (150, 1982, 650))
        self.assertEqual(boxes['bed.deck.001'].size, (1500, 2000, 18))
        self.assertEqual(boxes['panel.left.001'].lo, (200, 618, 18))
        for op in assembly.operations:
            self.assertTrue(boxes[op.target_panel_id].contains_box(op.cut.resolve(env)))
        self.assertNotIn('Bed_Width', build_interior().parameters.names())

    def test_refuse_overlap_and_envelope_excess(self):
        for layout in ({'Kitchen_Y':3000}, {'Bed_Width':2000}, {'Bed_Length':4100},
                       {'Bed_Height':2000}, {'Kitchen_X':700}, {'Kitchen_Y':-1},
                       {'Bed_Height':1200, 'Kitchen_Y':2500}):
            with self.assertRaises(ValueError, msg=layout):
                a = build_interior(layout)
                check_layout(a, a.parameters.resolve())

    def test_refuse_bad_types_and_unknown_inputs(self):
        for layout in ({'Bed_Width':True}, {'Bed_Length':float('nan')}, {'Kitchen_Y':'600 mm'},
                       {'arbitrary_python':'x'}, {'Bed_Length':0}):
            with self.assertRaises(ValueError):
                a = build_interior(layout)
                check_layout(a, a.parameters.resolve())


if __name__ == '__main__':
    unittest.main()
