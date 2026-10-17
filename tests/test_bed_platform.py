import csv
from dataclasses import replace
import io
import itertools
import json
import unittest

from vandesign.cad.protocol import preflight
from vandesign.components.model import ConstraintViolation
from vandesign.modules.bed_platform import build_bed_platform
from vandesign.panel_preview import make_preview, csv_text, canonical_json
from vandesign.schemas.bed_platform_spec import BedPlatformSpec, load_bed_spec, SCHEMA, MODULE


class BedPlatformTests(unittest.TestCase):
    def boxes(self, spec):
        a = build_bed_platform(spec)
        return a, {p.stable_id: p.box.resolve(a.parameters.resolve()) for p in a.panels}

    def test_default_geometry_independent_expected_values(self):
        a, b = self.boxes(BedPlatformSpec())
        self.assertEqual(a.operations, ())
        self.assertEqual(list(b), ['bed.deck.001', 'bed.front.001', 'bed.rear.001'])
        self.assertEqual(b['bed.deck.001'].lo, (0, 0, 682))
        self.assertEqual(b['bed.deck.001'].hi, (1400, 1900, 700))
        self.assertEqual(b['bed.front.001'].lo, (0, 0, 0))
        self.assertEqual(b['bed.front.001'].hi, (1400, 18, 682))
        self.assertEqual(b['bed.rear.001'].lo, (0, 1882, 0))
        self.assertEqual(b['bed.rear.001'].hi, (1400, 1900, 682))
        self.assertEqual(b['bed.deck.001'].volume, 47880000)
        self.assertEqual(b['bed.front.001'].volume, 17186400)
        self.assertEqual(b['bed.rear.001'].volume, 17186400)

    def test_independent_dimensions_contacts_no_overlaps_and_restore(self):
        original = BedPlatformSpec()
        baseline = self.boxes(original)
        for field, value in [('width_mm', 1500), ('length_mm', 2000), ('height_mm', 800)]:
            with self.subTest(field=field):
                s = replace(original, **{field: value});a, boxes = self.boxes(s)
                self.assertEqual([p.stable_id for p in a.panels], [p.stable_id for p in baseline[0].panels])
                self.assertNotEqual(a.spec_hash, baseline[0].spec_hash)
                deck = boxes['bed.deck.001']
                self.assertEqual(deck.size, (s.width_mm, s.length_mm, 18))
                self.assertEqual(deck.hi[2], s.height_mm)
                for key in ('bed.front.001', 'bed.rear.001'):
                    support = boxes[key]
                    self.assertEqual(support.hi[2], deck.lo[2])
                    self.assertEqual(support.size, (s.width_mm, 18, s.height_mm-18))
                    self.assertEqual(support.lo[0], deck.lo[0])
                    self.assertEqual(support.hi[0], deck.hi[0])
                    self.assertGreater(min(support.hi[1], deck.hi[1])-max(support.lo[1], deck.lo[1]), 0)
                for x,y in itertools.combinations(boxes.values(), 2):
                    self.assertEqual(x.overlap_volume(y), 0)
                env = a.parameters.resolve({'Bed_Width':1400, 'Bed_Length':1900, 'Bed_Height':700})
                self.assertEqual({p.stable_id:p.box.resolve(env) for p in a.panels}, baseline[1])
                self.assertEqual(self.boxes(original), baseline)

    def test_strict_spec_and_canonical_identity(self):
        s = BedPlatformSpec();self.assertEqual(load_bed_spec(s.to_json()), s)
        self.assertEqual(BedPlatformSpec(width_mm=1400).spec_hash(), BedPlatformSpec(width_mm=1400.0).spec_hash())
        raw={'schema_version':SCHEMA,'module':MODULE,'parameters':{}}
        self.assertEqual(load_bed_spec(json.dumps(raw)), s)
        bad=[{}, [], {**raw,'extra':1}, {**raw,'schema_version':'0.2'},
             {**raw,'module':'cabinet@1'}, {**raw,'parameters':{'unknown':1}},
             {**raw,'parameters':[]}, {**raw,'parameters':{'height_mm':None}}]
        for item in bad:
            with self.subTest(item=item), self.assertRaises(ValueError):load_bed_spec(json.dumps(item))
        for text in ['{"module":"x","module":"bed-platform@1"}', s.to_json().replace('1400.0','NaN'), ' '*65537]:
            with self.assertRaises(ValueError):load_bed_spec(text)

    def test_invalid_values_before_geometry(self):
        for field in ('width_mm','length_mm','height_mm','ply_mm'):
            for value in (0,-1,True,'18',None,float('nan'),float('inf'),10001,10**400):
                with self.subTest(field=field,value=repr(value)), self.assertRaises(ValueError):
                    build_bed_platform(BedPlatformSpec(**{field:value}))
        for t in (5,10,12,15,17.9,18.1):
            with self.assertRaises(ValueError):BedPlatformSpec(ply_mm=t)
        for kwargs in ({'width_mm':18},{'length_mm':36},{'height_mm':18}):
            with self.assertRaises(ValueError):build_bed_platform(BedPlatformSpec(**kwargs))
        # The shared preflight also rejects a later unsupported thickness override.
        a=build_bed_platform(BedPlatformSpec())
        params=replace(a.parameters,params=tuple(replace(p,value_mm=15) if p.name=='Bed_Ply' else p for p in a.parameters.params))
        with self.assertRaises(ConstraintViolation):preflight(replace(a,parameters=params))

    def test_preview_orientation_parity_and_determinism(self):
        s=BedPlatformSpec();p=make_preview(s.to_json())
        self.assertEqual(p['evidence']['status'],'UNKNOWN')
        self.assertEqual(p['grooves'],[])
        self.assertEqual(p['specification']['design_spec_hash'],s.spec_hash())
        self.assertEqual(canonical_json(p),canonical_json(make_preview(s.to_json())))
        rows=list(csv.DictReader(io.StringIO(csv_text(p))))
        self.assertEqual(rows,[{k:str(v) for k,v in row.items()} for row in p['panels']])
        self.assertEqual([r['panel_id'] for r in rows],sorted(r['panel_id'] for r in rows))
        for r in rows:
            self.assertEqual(r['quantity'],'1');self.assertEqual(r['nominal_thickness_mm'],'18.000000')
            if r['panel_id']=='bed.deck.001':
                self.assertEqual((r['blank_axis_1'],r['blank_axis_2'],r['thickness_axis']),('X','Y','Z'))
                self.assertEqual((r['blank_1_mm'],r['blank_2_mm']),('1400.000000','1900.000000'))
            else:
                self.assertEqual((r['blank_axis_1'],r['blank_axis_2'],r['thickness_axis']),('X','Z','Y'))
                self.assertEqual((r['blank_1_mm'],r['blank_2_mm']),('1400.000000','682.000000'))
        with self.assertRaisesRegex(ValueError,'not qualified'):
            make_preview(s.to_json(),b'{"validation":{"verdict":"PASS"}}')
        # Role-defined thickness axis must not be guessed as smallest dimension.
        short=make_preview(replace(s,height_mm=19).to_json())
        support=next(r for r in short['panels'] if r['role']=='bed_support')
        self.assertEqual(support['blank_2_mm'],'1.000000')
        self.assertEqual(support['nominal_thickness_mm'],'18.000000')


if __name__=='__main__':unittest.main()
