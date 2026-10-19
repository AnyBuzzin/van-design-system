import copy
import unittest
from vandesign.modules.storage_box import restored_storage_measurements


class RestorationTests(unittest.TestCase):
    def baseline(self):
        return dict(outcome='PASS',parameters_mm={'Storage_Width':600},counts={'timeline':67},
            bodies={'panel':dict(min=[0,0,0],max=[1,1,1],volume_mm3=3340799.999999995)},
            checks=[dict(check_id='panel.volume',status='PASS',unit='mm3',object_ids=['panel'],
                         observed=3340799.999999995,expected=3340800,tolerance=3.3408),
                    dict(check_id='ownership',status='PASS',participants=['side'])])

    def test_observed_noise_pass_without_mutation(self):
        a=self.baseline();b=copy.deepcopy(a)
        b['bodies']['panel']['volume_mm3']=b['checks'][0]['observed']=3340799.9999999683
        original=copy.deepcopy((a,b))
        self.assertTrue(restored_storage_measurements(a,b))
        self.assertEqual((a,b),original)

    def test_volume_material_change_missing_nonfinite_or_inconsistent_fail(self):
        a=self.baseline()
        for value in (3340800.001,None,True,float('nan'),float('inf'),-1):
            b=copy.deepcopy(a);b['bodies']['panel']['volume_mm3']=b['checks'][0]['observed']=value
            self.assertFalse(restored_storage_measurements(a,b))
            if value != 3340800.001:
                self.assertFalse(restored_storage_measurements(b,b))
        for mutation in (lambda b:b['bodies']['panel'].pop('volume_mm3'),
                         lambda b:b['checks'].pop(0),lambda b:b['checks'][0].pop('observed'),
                         lambda b:b['checks'][0].update(observed=0),
                         lambda b:b['checks'][0].update(tolerance=float('nan'))):
            b=copy.deepcopy(a);mutation(b);self.assertFalse(restored_storage_measurements(a,b))

    def test_other_fields_and_validation_stay_strict(self):
        a=self.baseline()
        for mutation in (lambda b:b['parameters_mm'].update(Storage_Width=600.00000001),
                         lambda b:b['counts'].update(timeline=68),
                         lambda b:b['bodies']['panel']['min'].__setitem__(0,1e-10),
                         lambda b:b['checks'][0].update(status='FAIL'),
                         lambda b:b['checks'][0].update(unit='mm'),
                         lambda b:b['checks'][0].update(object_ids=['other']),
                         lambda b:b['checks'][1].update(participants=['other']),
                         lambda b:b['checks'].append(copy.deepcopy(b['checks'][0]))):
            b=copy.deepcopy(a);mutation(b);self.assertFalse(restored_storage_measurements(a,b))
