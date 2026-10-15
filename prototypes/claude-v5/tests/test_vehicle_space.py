"""Focused usable-space checks; live BRep evidence is captured separately."""
import unittest
import core_path
from vandesign.modules.interior_demo import build_interior, check_layout, vehicle_clearances

LAYOUT = dict(Bed_Width=1700, Bed_Length=2000, Bed_Height=750, Kitchen_X=100, Kitchen_Y=500)
VEHICLE = dict(Van_Width=2100, Van_Length=4600, Van_Height=2200, Arch_Width=250,
               Arch_Length=800, Arch_Height=300, Arch_Left_Y=3000, Arch_Right_Y=3000, Min_Aisle=600)


class VehicleSpaceTests(unittest.TestCase):
    def check(self, layout=None, vehicle=None):
        a = build_interior(dict(LAYOUT, **(layout or {})), dict(VEHICLE, **(vehicle or {})))
        env = a.parameters.resolve()
        boxes = check_layout(a, env)
        return a, boxes, vehicle_clearances(env, boxes)

    def test_valid_arches_under_bed_and_clear_aisle(self):
        a,b,c = self.check()
        self.assertEqual(len(a.panels),17)
        self.assertEqual(b['van.arch_left.001'].lo,(18,3000,18))
        self.assertEqual(b['van.arch_right.001'].lo,(1832,3000,18))
        self.assertEqual(c['aisle_width_mm'],782)
        self.assertEqual(c['bed_deck_above_arch_top_mm'],432)
        self.assertEqual(c['prohibited_overlap_count'],0)

    def test_refuse_cabinet_and_support_wheel_arch_collisions(self):
        for edits in ({'Arch_Left_Y':500}, {'Arch_Left_Y':2582}, {'Arch_Height':800}):
            with self.assertRaisesRegex(ValueError,'restricted wheel-arch'):
                self.check(vehicle=edits)

    def test_refuse_aisle_and_account_for_right_arch(self):
        with self.assertRaisesRegex(ValueError,'aisle'):
            self.check(layout={'Kitchen_X':400})
        with self.assertRaisesRegex(ValueError,'aisle'):
            self.check(vehicle={'Arch_Right_Y':600})
        _,_,c=self.check(vehicle={'Arch_Right_Y':600,'Min_Aisle':500})
        self.assertEqual(c['aisle_width_mm'],532)
        with self.assertRaisesRegex(ValueError,'aisle'):
            self.check(vehicle={'Min_Aisle':782.01})

    def test_refuse_invalid_dimensions_positions_and_types(self):
        for edits in ({'Arch_Left_Y':4500},{'Arch_Width':1100},{'Arch_Height':0},
                      {'Min_Aisle':-1},{'Van_Height':600},{'Arch_Length':float('nan')},
                      {'Arch_Width':True},{'unknown':20}):
            with self.assertRaises(ValueError,msg=edits): self.check(vehicle=edits)

    def test_legacy_defaults_and_cuts_remain_compatible(self):
        self.assertEqual(len(build_interior().panels),15)
        self.assertNotIn('Arch_Width',build_interior({}).parameters.names())
        a,b,_=self.check()
        env=a.parameters.resolve()
        for cut in a.operations:
            self.assertTrue(b[cut.target_panel_id].contains_box(cut.cut.resolve(env)))
