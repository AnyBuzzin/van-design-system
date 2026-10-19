import copy
import csv
import io
import json
from dataclasses import replace
from itertools import combinations
import unittest

from vandesign.core.geometry import Box
from vandesign.modules.storage_box import (build_storage_box, build_storage_scene, preview_storage,
    preview_invalid_storage, storage_contacts, PREFIX)
from vandesign.modules.test_envelope import build_test_envelope, furniture_rows
from vandesign.panel_preview import make_preview, csv_text
from vandesign.schemas.storage_box_spec import StorageBoxSpec, load_storage_spec


class StorageTests(unittest.TestCase):
    def test_dimensions_volumes_identity_and_contacts(self):
        spec=StorageBoxSpec(); a=build_storage_box(spec)
        self.assertEqual(a,build_storage_box(load_storage_spec(spec.to_json())))
        expected={'bottom':((0,0,0),(600,800,18),8640000),
                  'left':((0,0,18),(18,800,250),3340800),
                  'right':((582,0,18),(600,800,250),3340800),
                  'front':((18,0,18),(582,18,250),2355264),
                  'rear':((18,782,18),(582,800,250),2355264)}
        boxes={p.stable_id:p.box.resolve(a.parameters.resolve()) for p in a.panels}
        self.assertEqual(set(boxes),{'storage.'+k+'.001' for k in expected})
        for name,(lo,hi,volume) in expected.items():
            b=boxes['storage.'+name+'.001']
            self.assertEqual(b,Box(lo,hi)); self.assertEqual(b.volume,volume)
        self.assertTrue(all(x.overlap_volume(y)==0 for x,y in combinations(boxes.values(),2)))
        self.assertEqual(a.operations,())
        contacts=storage_contacts({PREFIX+k:b for k,b in boxes.items()})
        self.assertEqual(len(contacts),8); self.assertTrue(all(contacts.values()))

    def test_independent_resize_and_restoration(self):
        baseline=build_storage_box(StorageBoxSpec())
        for key,value in [('width_mm',700),('length_mm',900),('height_mm',300)]:
            s=replace(StorageBoxSpec(),**{key:value}); a=build_storage_box(s)
            env=a.parameters.resolve(); boxes={PREFIX+p.stable_id:p.box.resolve(env) for p in a.panels}
            self.assertEqual([p.stable_id for p in a.panels],[p.stable_id for p in baseline.panels])
            self.assertNotEqual(a.spec_hash,baseline.spec_hash)
            self.assertEqual(a.panel('storage.bottom.001').box.resolve(env).size,(s.width_mm,s.length_mm,18))
            self.assertTrue(all(storage_contacts(boxes).values()))
            self.assertTrue(all(x.overlap_volume(y)==0 for x,y in combinations(boxes.values(),2)))
            restored=a.parameters.resolve(baseline.parameters.resolve())
            self.assertEqual([p.box.resolve(restored) for p in a.panels],
                             [p.box.resolve(baseline.parameters.resolve()) for p in baseline.panels])

    def test_strict_invalid_contract(self):
        for key in ('width_mm','length_mm','height_mm','ply_mm'):
            for value in (True,None,'600',0,-1,float('nan'),float('inf'),10001):
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    StorageBoxSpec(**{key:value})
        for fields in ({'ply_mm':12},{'width_mm':36},{'length_mm':36},{'height_mm':18}):
            with self.assertRaises(ValueError): StorageBoxSpec(**fields)
        raw=json.loads(StorageBoxSpec().to_json())
        for mutation in (lambda d:d.update(extra=1),lambda d:d.update(module='cabinet@1'),
                         lambda d:d.update(schema_version='2'),lambda d:d['parameters'].update(extra=1)):
            bad=copy.deepcopy(raw);mutation(bad)
            with self.assertRaises(ValueError): load_storage_spec(json.dumps(bad))
        with self.assertRaises(ValueError): load_storage_spec(StorageBoxSpec().to_json().replace('600.0','NaN'))
        with self.assertRaises(ValueError): load_storage_spec(StorageBoxSpec().to_json().replace('600.0','600,"width_mm":600'))

    def test_cut_list_orientation_and_csv_json_parity(self):
        preview=make_preview(StorageBoxSpec().to_json())
        self.assertEqual(preview['evidence']['status'],'UNKNOWN')
        rows=preview['panels']; self.assertEqual(len(rows),5)
        dimensions={'bottom':('X','Y','Z','600.000000','800.000000'),
                    'left':('Y','Z','X','800.000000','232.000000'),
                    'right':('Y','Z','X','800.000000','232.000000'),
                    'front':('X','Z','Y','564.000000','232.000000'),
                    'rear':('X','Z','Y','564.000000','232.000000')}
        for r in rows:
            self.assertEqual(tuple(r[k] for k in ('blank_axis_1','blank_axis_2','thickness_axis','blank_1_mm','blank_2_mm')),
                             dimensions[r['panel_id'].split('.')[1]])
            self.assertEqual(r['nominal_thickness_mm'],'18.000000');self.assertEqual(r['quantity'],1)
        self.assertEqual(list(csv.DictReader(io.StringIO(csv_text(preview)))),
                         [{k:str(v) for k,v in r.items()} for r in rows])
        with self.assertRaises(ValueError): make_preview(StorageBoxSpec().to_json(),b'{}')

    def test_scene_preserves_existing_geometry_and_anchored_gaps(self):
        original=build_test_envelope(); a=build_storage_scene()
        self.assertEqual(a.panels[:16],original.panels);self.assertEqual(a.operations,original.operations)
        self.assertEqual(a.parameters.params[:28],original.parameters.params)
        self.assertEqual(len(a.panels),21);self.assertEqual(len(furniture_rows(a)),16)
        for width,right in ((600,396),(700,296),(600,396)):
            env=a.parameters.resolve({'Storage_Width':width})
            gaps=preview_storage(a,env)
            self.assertEqual(gaps,dict(top_to_deck_mm=432,left_arch_gap_mm=396,right_arch_gap_mm=right))
            boxes={p.stable_id:p.box.resolve(env) for p in a.panels}
            self.assertEqual(boxes[PREFIX+'storage.bottom.001'].lo,(592,600,0))
            self.assertTrue(all(storage_contacts(boxes).values()))

    def test_refusal_and_invalid_observations_do_not_mutate(self):
        a=build_storage_scene(); env=a.parameters.resolve(); old=copy.deepcopy((a,env))
        self.assertEqual(preview_invalid_storage(a,env)['outcome'],'REFUSED')
        self.assertEqual((a,env),old)
        for bad in (None,True,float('nan'),float('inf')):
            with self.assertRaises(ValueError): preview_storage(a,dict(env,Storage_Width=bad))
        boxes={p.stable_id:p.box.resolve(env) for p in a.panels}
        with self.assertRaises(ValueError): preview_storage(a,env,{})
        for delta in ((0,-550,0),(0,1500,0),(0,0,500),(-600,0,0)):
            moved=dict(boxes)
            for sid,b in boxes.items():
                if sid.startswith(PREFIX):
                    moved[sid]=Box(tuple(x+d for x,d in zip(b.lo,delta)),tuple(x+d for x,d in zip(b.hi,delta)))
            with self.subTest(delta=delta),self.assertRaises(ValueError): preview_storage(a,env,moved)
        shifted=dict(boxes);sid=PREFIX+'storage.front.001';b=shifted[sid]
        shifted[sid]=Box((b.lo[0],b.lo[1],b.lo[2]+1),(b.hi[0],b.hi[1],b.hi[2]+1))
        self.assertFalse(storage_contacts(shifted)['bottom.front'])
