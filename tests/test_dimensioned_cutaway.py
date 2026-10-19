import copy
import unittest
from vandesign.modules.dimensioned_cutaway import build_dimensioned_cutaway, dimension_labels
from vandesign.modules.storage_box import build_storage_scene
from vandesign.modules.test_envelope import furniture_rows

class CutawayTests(unittest.TestCase):
    def setUp(self):
        self.a=build_dimensioned_cutaway();self.env=self.a.parameters.resolve()
        self.report=dict(outcome='PASS',parameters_mm=self.env,bodies={p.stable_id:dict(
            min=p.box.resolve(self.env).lo,max=p.box.resolve(self.env).hi,
            volume_mm3=p.box.resolve(self.env).volume) for p in self.a.panels})

    def test_exact_furniture_reuse_and_reference_bounds(self):
        old=build_storage_scene()
        self.assertEqual(self.a,build_dimensioned_cutaway())
        self.assertEqual(self.a.parameters,old.parameters)
        self.assertEqual(self.a.operations,old.operations)
        self.assertEqual(furniture_rows(self.a),furniture_rows(old))
        self.assertEqual(len(furniture_rows(self.a)),16)
        for a,b in zip(self.a.panels,old.panels):
            if a.stable_id!='reference.right':self.assertEqual(a,b)
        wall=next(p.box.resolve(self.env) for p in self.a.panels if p.stable_id=='reference.right')
        self.assertEqual(wall.lo,(1784,0,0));self.assertEqual(wall.hi,(1794,3044,2025))
        for p in self.a.panels:
            if not p.stable_id.startswith('reference.'):
                self.assertEqual(wall.overlap_volume(p.box.resolve(self.env)),0)

    def test_labels_use_complete_measured_values_and_explicit_assumptions(self):
        labels=dimension_labels(self.a,self.report);text='\n'.join(labels)
        for value in ('3044 x 1784 x 2025','1400 x 1900 x 700','1100 x 568 x 850',
                      '600 x 800 x 250','550 mm','382 mm','634 mm','432 mm','396 x 396 mm',
                      '196 x 800 x 300','600 mm','TEST ONLY / UNMEASURED','ASSUMED','not live-updating'):
            self.assertIn(value,text)
        for mutation in ('missing','nan','contradiction','unknown'):
            r=copy.deepcopy(self.report)
            if mutation=='missing':del r['bodies']['reference.arch.left']
            if mutation=='nan':r['bodies']['reference.right']['volume_mm3']=float('nan')
            if mutation=='contradiction':r['bodies']['reference.right']['max']=(1794,3044,2024)
            if mutation=='unknown':r['outcome']='UNKNOWN'
            with self.assertRaises((ValueError,KeyError)):dimension_labels(self.a,r)
