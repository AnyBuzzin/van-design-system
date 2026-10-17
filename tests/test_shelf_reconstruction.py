"""Ownership/deletion failure boundaries using small API doubles, not Fusion proof."""
import importlib
import ast
import inspect
import textwrap
import json
import sys
import types
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch


class Collection:
    def __init__(self, values=()): self.values=list(values)
    @property
    def count(self): return len(self.values)
    def item(self,i): return self.values[i]


class Owned:
    def __init__(self, collection, name):
        self.collection=collection; self.name=name; self.isValid=True; self.isDeletable=True
    def deleteMe(self):
        self.collection.values.remove(self); self.isValid=False; return True


class ReconstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        adsk=types.ModuleType('adsk')
        adsk.core=types.ModuleType('adsk.core'); adsk.fusion=types.ModuleType('adsk.fusion')
        with patch.dict(sys.modules,{'adsk':adsk,'adsk.core':adsk.core,'adsk.fusion':adsk.fusion}):
            cls.mod=importlib.import_module('vandesign.cad.fusion.shelf_regeneration')

    @classmethod
    def tearDownClass(cls):
        for name in ('vandesign.cad.fusion.shelf_regeneration','vandesign.cad.fusion.adapter'):
            sys.modules.pop(name,None)

    def setup_handle(self):
        occs=Collection(); params=Collection()
        old=Owned(occs,'old'); occs.values.append(old)
        p=Owned(params,'Cab_Width'); params.values.append(p)
        adapter=NS(root=NS(occurrences=occs),design=NS(userParameters=params))
        assembly=NS(parameters=NS(params=[NS(name='Cab_Width')]))
        with patch.object(self.mod,'verified_state',return_value={}):
            handle=self.mod.Reconstruction(adapter,assembly,assembly)
        return handle,adapter,occs,params,old

    def test_only_captured_entities_deleted_and_empty_verified(self):
        h,a,occs,params,old=self.setup_handle()
        with patch.object(self.mod,'require_empty') as empty:
            h._empty_owned()
        self.assertFalse(old.isValid)
        self.assertEqual((occs.count,params.count),(0,0))
        empty.assert_called_once_with(a.design)

    def test_unknown_occurrence_stops_before_any_deletion(self):
        h,a,occs,params,old=self.setup_handle()
        occs.values.append(Owned(occs,'protected'))
        with self.assertRaisesRegex(self.mod.FusionAdapterError,'unexpected occurrence'):
            h._empty_owned()
        self.assertTrue(old.isValid)
        self.assertEqual(params.count,1)

    def test_parameter_dependencies_or_delete_failure_fail_closed(self):
        h,a,occs,params,old=self.setup_handle()
        params.item(0).isDeletable=False
        with self.assertRaisesRegex(self.mod.FusionAdapterError,'still referenced'):
            h._empty_owned()
        self.assertEqual(params.count,1)
        h,a,occs,params,old=self.setup_handle()
        old.deleteMe=lambda: False
        with self.assertRaisesRegex(self.mod.FusionAdapterError,'deletion failed'):
            h._empty_owned()
        self.assertEqual(params.count,1)

    def test_partial_compile_entities_remain_captured_for_recovery(self):
        h,a,occs,params,old=self.setup_handle()
        calls=[]
        def compile(assembly):
            fresh=Owned(occs,'partial'); occs.values.append(fresh)
            a._structural_created.append(fresh)
            calls.append('compile')
            if len(calls)==1: raise RuntimeError('failed after new occurrence')
        a.compile=compile
        a.store_spec_json=lambda text: calls.append(text)
        a.stored_spec_json=lambda: 'original'
        with patch.object(self.mod,'require_empty'), patch.object(self.mod,'verified_state',return_value={}):
            with self.assertRaisesRegex(RuntimeError,'failed after'):
                h.apply('new')
            partial=occs.item(0)
            h.restore('original')
        self.assertFalse(partial.isValid)
        self.assertEqual(occs.count,1)
        self.assertEqual(calls,['compile','compile','original'])

    def test_orphan_blocks_compile(self):
        h,a,occs,params,old=self.setup_handle()
        a.compile=lambda *args,**kw: self.fail('compile reached')
        with patch.object(self.mod,'require_empty',side_effect=self.mod.FusionAdapterError('orphan')), patch.object(self.mod,'verified_state',return_value={}):
            with self.assertRaisesRegex(self.mod.FusionAdapterError,'orphan'): h.apply('new')

    def test_receipt_requires_matching_resolved_entities_not_token_strings(self):
        m=self.mod; entity=object()
        saved={'state':{'value':1},'tokens':{'panel':'old-token'}}
        a=NS(root=NS(attributes=NS(itemByName=lambda *args:NS(value=json.dumps(saved)))),
             design=NS(findEntityByToken=lambda token:[entity]))
        with patch.object(m,'snapshot',return_value=({'value':1},{'panel':'new-token'})):
            self.assertEqual(m.verified_state(a,None),{'value':1})
            a.design.findEntityByToken=lambda token:[object()]
            with self.assertRaisesRegex(m.FusionAdapterError,'replaced'): m.verified_state(a,None)
        with patch.object(m,'snapshot',return_value=({'value':2},{'panel':'new-token'})):
            with self.assertRaisesRegex(m.FusionAdapterError,'differs'): m.verified_state(a,None)
        a.root.attributes.itemByName=lambda *args:None
        with self.assertRaisesRegex(m.FusionAdapterError,'cannot be adopted'): m.verified_state(a,None)

    def test_unavailable_snapshot_never_authorizes(self):
        a=NS(root=NS(attributes=NS(itemByName=lambda *args:NS(value='{"state":{}}'))))
        with patch.object(self.mod,'snapshot',side_effect=RuntimeError('API unavailable')):
            with self.assertRaisesRegex(RuntimeError,'unavailable'): self.mod.verified_state(a,None)

    def test_tracked_panel_wrapper_preserves_g3_construction(self):
        original=ast.parse(textwrap.dedent(inspect.getsource(self.mod.FusionAdapter._make_panel))).body[0]
        tracked=ast.parse(textwrap.dedent(inspect.getsource(self.mod.ShelfFixtureAdapter._make_panel))).body[0]
        original.args.args[1].annotation=None
        self.assertEqual(ast.unparse(tracked.body[1]), "if hasattr(self, '_structural_created'):\n    self._structural_created.append(occ)")
        del tracked.body[1]
        self.assertEqual(ast.dump(original),ast.dump(tracked))

    def test_final_drift_guard_does_not_start_deletion(self):
        h,a,occs,params,old=self.setup_handle()
        with patch.object(self.mod,'verified_state',side_effect=self.mod.FusionAdapterError('drift')):
            with self.assertRaisesRegex(self.mod.FusionAdapterError,'drift'): h.apply('new')
        self.assertFalse(h.started)
        self.assertTrue(old.isValid)

    def snapshot_fixture(self):
        from vandesign.schemas.cabinet_spec import CabinetSpec
        from vandesign.modules.cabinet import build_cabinet
        m=self.mod; assembly=build_cabinet(CabinetSpec()); entities={}
        def token(entity,name):
            entity.entityToken=name; entities[name]=entity; return entity
        def attrset(values=None):
            values=dict(values or {})
            def add(group,name,value): values[(group,name)]=NS(value=value)
            return NS(itemByName=lambda g,n:values.get((g,n)),add=add)
        def aux(comp):
            for name in ('occurrences','meshBodies','constructionPlanes','constructionAxes','constructionPoints','joints','asBuiltJoints','rigidGroups'):
                setattr(comp,name,Collection())
            return comp
        p=NS(x=0.,y=0.,z=0.)
        root=aux(NS(attributes=attrset(),bRepBodies=Collection(),sketches=Collection(),features=Collection()))
        for panel in assembly.panels:
            pid=panel.stable_id
            attrs=attrset({(m.ATTR_GROUP,m.ATTR_ID):NS(value=pid),
                           (m.ATTR_GROUP,m.ATTR_GEN):NS(value=m.GENERATOR_ID),
                           (m.ATTR_GROUP,m.ATTR_RULE):NS(value='module:%s role:%s'%(m.GENERATOR_ID,panel.role))})
            names=[panel.display_name+' - solid']+[op.operation_id for op in assembly.operations if op.target_panel_id==pid]
            features=[token(NS(name=n,operation=0,healthState=0,isSuppressed=False),pid+'/'+n) for n in names]
            sketches=[]
            for name in names:
                sn=name.replace(' - solid','')+' - parametric profile'
                curves=Collection([NS(startSketchPoint=NS(geometry=p),endSketchPoint=NS(geometry=p)) for _ in range(4)])
                curves.sketchLines=curves
                sketches.append(token(NS(name=sn,sketchCurves=curves,sketchPoints=Collection([p]),
                                         geometricConstraints=Collection(),sketchDimensions=Collection(),profiles=Collection([object()])),pid+'/'+sn))
            body=token(NS(name=panel.display_name,isSolid=True,boundingBox=NS(minPoint=p,maxPoint=p),volume=1.,
                          faces=Collection([1]),edges=Collection([1]),vertices=Collection([1])),pid+'/body')
            feature_collection=Collection(features); feature_collection.extrudeFeatures=Collection(features)
            comp=aux(NS(name=panel.display_name,attributes=attrs,bRepBodies=Collection([body]),
                        features=feature_collection,sketches=Collection(sketches),modelParameters=Collection()))
            occ=token(NS(component=comp,isReferencedComponent=False,transform2=NS(asArray=lambda:[1.,0.,0.,0.])),pid)
            root.occurrences.values.append(occ)
        env=assembly.parameters.resolve()
        params=Collection([NS(name=k,expression=str(v)+' mm',unit='mm',value=v/10) for k,v in env.items()])
        design=NS(rootComponent=root,allComponents=Collection([root]+[o.component for o in root.occurrences.values]),
                  userParameters=params,timeline=NS(count=28,markerPosition=28),findEntityByToken=lambda t:[entities[t]] if t in entities else [])
        return NS(root=root,design=design),assembly

    def test_actual_inventory_detects_structural_and_manual_drift(self):
        for fault in ('extra_occ','duplicate_id','missing_body','extra_feature','unhealthy','root_body','extra_param','orphan','rolled_timeline','transform','model_expression'):
            a,asm=self.snapshot_fixture(); self.mod.record_receipt(a,asm)
            self.mod.verified_state(a,asm)
            comp=a.root.occurrences.item(0).component
            if fault=='extra_occ': a.root.occurrences.values.append(a.root.occurrences.item(0))
            elif fault=='duplicate_id': a.root.occurrences.item(1).component.attributes.add(self.mod.ATTR_GROUP,self.mod.ATTR_ID,asm.panels[0].stable_id)
            elif fault=='missing_body': comp.bRepBodies.values.clear()
            elif fault=='extra_feature': comp.features.values.append(object())
            elif fault=='unhealthy': comp.features.extrudeFeatures.item(0).healthState=1
            elif fault=='root_body': a.root.bRepBodies.values.append(object())
            elif fault=='extra_param': a.design.userParameters.values.append(NS(name='Unknown',expression='1 mm',unit='mm',value=.1))
            elif fault=='orphan': a.design.allComponents.values.append(object())
            elif fault=='rolled_timeline': a.design.timeline.markerPosition=0
            elif fault=='transform': a.root.occurrences.item(0).transform2.asArray=lambda:[2.,0.,0.,0.]
            elif fault=='model_expression': comp.modelParameters.values.append(NS(expression='manual',unit='mm',value=1.))
            with self.assertRaises(self.mod.FusionAdapterError,msg=fault): self.mod.verified_state(a,asm)
