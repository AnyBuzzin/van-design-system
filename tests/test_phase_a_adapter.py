"""Historical fake-API trace oracle; never imports a historical production runtime."""
import ast
import hashlib
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from vandesign.modules.bed_platform import build_bed_platform
from vandesign.schemas.bed_platform_spec import BedPlatformSpec
from vandesign.modules.variants import get_profile, profile_defaults_spec, build_variant


class AdapterRegressionTests(unittest.TestCase):
    def setUp(self):
        self.fake=NS(core=NS(Point3D=NS(create=lambda *v:v)),fusion=NS(
            DimensionOrientations=NS(HorizontalDimensionOrientation='H',VerticalDimensionOrientation='V')))
        with patch.dict(sys.modules,{'adsk':self.fake,'adsk.core':self.fake.core,'adsk.fusion':self.fake.fusion}):
            self.current=importlib.import_module('vandesign.cad.fusion.adapter')
        patcher=patch.object(self.current,'adsk',self.fake);patcher.start();self.addCleanup(patcher.stop)
        root=Path(__file__).resolve().parents[1]
        tree=ast.parse((root/'prototypes/claude-v5/VanCabinetJoineryV5/vandesign/cad/fusion/adapter.py').read_text(encoding='utf-8'))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FusionAdapter')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_rectangle_profile')
        # Independently matched to git 17b74de^ (before PR49) during preparation.
        self.assertEqual(hashlib.sha256(ast.dump(method).encode()).hexdigest(),
            'd51537a5f9dc71a14b7977be55a65a3e8bc8ccb01a52072b8b5db0b5217c7349')
        namespace={'adsk':self.fake,'FusionAdapterError':RuntimeError}
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<pinned pre49 profile>','exec'),namespace)
        self.old=namespace['_rectangle_profile']

    def trace(self,box,env,current):
        trace=[];lines=[NS(startSketchPoint=i,endSketchPoint=(i+1)%4) for i in range(4)]
        def dimension(a,b,axis,text):
            parameter=NS(expression=None);trace.append(('dimension',a,b,axis,text,parameter));return NS(parameter=parameter)
        def record(name):return lambda *args:trace.append((name,*args))
        def rectangle(*args):trace.append(('rectangle',*args));return NS(item=lambda i:lines[i])
        sketch=NS(originPoint='origin',geometricConstraints=NS(**{n:record(n) for n in (
            'addHorizontal','addVertical','addCoincident','addVerticalPoints','addHorizontalPoints')}),
            sketchDimensions=NS(addDistanceDimension=dimension),
            sketchCurves=NS(sketchLines=NS(addTwoPointRectangle=rectangle)))
        comp=NS(xYConstructionPlane='XY',sketches=NS(add=lambda plane:sketch))
        exprs=box.origin[:2]+box.size[:2];values={e.render():e.eval(env)/10 for e in exprs}
        adapter=NS(_eval_cm=lambda e:values[e])
        args=(adapter,comp,'panel',*(e.render() for e in exprs))
        if current:
            self.current.FusionAdapter._rectangle_profile(*args,x_dynamic=bool(exprs[0].refs()),y_dynamic=bool(exprs[1].refs()))
        else:self.old(*args)
        return [t[:-1]+(t[-1].expression,) if t[0]=='dimension' else t for t in trace]

    def test_every_default_panel_and_cut_profile_matches_pre49(self):
        assemblies=[build_variant(profile_defaults_spec(get_profile(v,1))) for v in ('base','tall','overhead')]
        assemblies.append(build_bed_platform(BedPlatformSpec()))
        for assembly in assemblies:
            env=assembly.parameters.resolve()
            for obj in list(assembly.panels)+list(assembly.operations):
                box=obj.box if hasattr(obj,'box') else obj.cut
                with self.subTest(assembly=assembly.assembly_id,object=getattr(obj,'stable_id',getattr(obj,'operation_id',''))):
                    self.assertFalse(any(e.refs() and abs(e.eval(env)/10)<1e-7 for e in box.origin[:2]))
                    self.assertEqual(self.trace(box,env,True),self.trace(box,env,False))

    def test_only_dynamic_zero_binding_exception_is_explicit(self):
        from vandesign.core.expr import Mm, Param
        from vandesign.core.geometry import BoxExpr
        box=BoxExpr((Param('X'),Mm(0),Mm(0)),(Mm(100),Mm(200),Mm(18)))
        before=self.trace(box,{'X':0},False);after=self.trace(box,{'X':0},True)
        self.assertEqual([t for t in before if t[0]=='dimension'],[t for t in after if t[0]=='dimension'][-2:])
        extra=[t for t in after if t[0]=='dimension'][0]
        self.assertEqual((extra[1],extra[2],extra[3],extra[-1]),('origin',2,'H','(X + 100 mm)'))
        self.assertEqual(self.trace(box,{'X':50},True),self.trace(box,{'X':50},False))
