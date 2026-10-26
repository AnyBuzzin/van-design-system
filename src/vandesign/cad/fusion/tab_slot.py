"""Fixed E1.2 compiler/qualification; no arbitrary cut or Python job inputs."""
import json
import math
from pathlib import Path

import adsk.core
import adsk.fusion

from .adapter import FusionAdapter, FusionGeometrySource, FusionAdapterError, ATTR_GROUP, ATTR_ID, _find_occurrences
from .runner import _design_counts
from .test_envelope import snapshot
from ...core.tab_slot import RECEIVER, UPRIGHT
from ...modules.tab_slot import build_tab_slot, preview_tab_slot, CUT_IDS, OWNERS, NAMES
from ...modules.storage_box import restored_storage_measurements
from ...schemas.tab_slot_spec import TabSlotSpec
from ...verification.tab_slot import measure_coupon_geometry


class CouponAdapter(FusionAdapter):
    def _circle_profile(self, comp, name, x, y, radius):
        px,py,r=(self._eval_cm(e) for e in (x,y,radius))
        if not all(math.isfinite(v) and v>0 for v in (px,py,r)):
            raise FusionAdapterError('Invalid coupon relief circle')
        point=adsk.core.Point3D.create
        sketch=comp.sketches.add(comp.xYConstructionPlane);sketch.name=name
        circle=sketch.sketchCurves.sketchCircles.addByCenterRadius(point(px,py,0),r)
        if circle is None:raise FusionAdapterError('Circle creation failed')
        dims=sketch.sketchDimensions
        H=adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation
        V=adsk.fusion.DimensionOrientations.VerticalDimensionOrientation
        for orientation,expression,position in ((H,x,point(px/2,-2,0)),(V,y,point(-2,py/2,0))):
            dims.addDistanceDimension(sketch.originPoint,circle.centerSketchPoint,orientation,position).parameter.expression=expression
        dims.addRadialDimension(circle,point(px+r+1,py+r+1,0)).parameter.expression=radius
        if sketch.profiles.count!=1:raise FusionAdapterError('Circle must form one profile')
        return sketch

    def compile_coupon(self, coupon, guard, records=None):
        if coupon!=build_tab_slot(coupon.spec):raise ValueError('Only canonical fixed coupon supported')
        guard()
        self.compile(coupon.blanks)
        occurrences=_find_occurrences(self.root)
        if set(occurrences)!={RECEIVER,UPRIGHT} or any(len(v)!=1 for v in occurrences.values()):
            raise FusionAdapterError('Ambiguous coupon owners')
        components={pid:occs[0].component for pid,occs in occurrences.items()}
        if any(c.bRepBodies.count!=1 for c in components.values()):
            raise FusionAdapterError('Every cut must resolve exactly one body before any cut')
        removed=[] if records is None else records
        expected=coupon.geometry().cut_volumes
        for i,(cid,owner) in enumerate(zip(CUT_IDS,OWNERS)):
            guard();comp=components[owner]
            before={pid:c.bRepBodies.item(0).volume*1000 for pid,c in components.items()}
            if i<3:
                box=(coupon.shoulders+(coupon.slot,))[i]
                x,y,z=(e.render() for e in box.origin);w,h,depth=(e.render() for e in box.size)
                sketch=self._rectangle_profile(comp,cid,x,y,w,h,
                         x_dynamic=bool(box.origin[0].refs()),y_dynamic=bool(box.origin[1].refs()))
            else:
                x,y=coupon.centres[i-3];z='0 mm';depth='18 mm'
                sketch=self._circle_profile(comp,cid,x.render(),y.render(),coupon.radius.render())
            guard()
            self._extrude(comp,sketch,cid,z,depth,adsk.fusion.FeatureOperations.CutFeatureOperation,
                          participants=[comp.bRepBodies.item(0)])
            after={pid:c.bRepBodies.item(0).volume*1000 for pid,c in components.items()}
            delta=before[owner]-after[owner];mate=RECEIVER if owner==UPRIGHT else UPRIGHT
            ok=(all(math.isfinite(v) for v in (*before.values(),*after.values()))
                and abs(delta-expected[i])<=max(1,expected[i]*1e-6)
                and abs(before[mate]-after[mate])<=1e-6)
            removed.append(dict(cut_id=cid,owner=owner,before_mm3=before,after_mm3=after,
                                removed_mm3=delta,expected_mm3=expected[i],outcome='PASS' if ok else 'FAIL'))
            if not ok:raise FusionAdapterError('Unexpected cut volume/mate change: '+cid)
        guard()
        return removed


class CouponSource(FusionGeometrySource):
    def coupon_faces(self,g):
        """Read selected planar BRep positions; missing/ambiguous faces stop."""
        planes={}
        for pid in (RECEIVER,UPRIGHT):
            body=self._single_body(pid)
            if body is None:raise RuntimeError('Missing coupon body')
            values=[]
            for i in range(body.faces.count):
                face=body.faces.item(i);plane=adsk.core.Plane.cast(face.geometry)
                if plane is None:continue
                bb=face.boundingBox
                lo=tuple(getattr(bb.minPoint,k)*10 for k in 'xyz')
                hi=tuple(getattr(bb.maxPoint,k)*10 for k in 'xyz')
                normal=tuple(getattr(plane.normal,k) for k in 'xyz')
                if not all(math.isfinite(v) for v in lo+hi+normal):raise RuntimeError('Nonfinite face')
                values.append((lo,hi,normal))
            planes[pid]=values
        def coordinate(pid,axis,value,contains):
            found=[]
            for lo,hi,n in planes[pid]:
                if (abs(abs(n[axis])-1)<1e-8 and abs(lo[axis]-value)<=0.01
                        and abs(hi[axis]-value)<=0.01
                        and all(lo[k]-0.01<=v<=hi[k]+0.01 for k,v in contains.items())):
                    found.append((lo[axis]+hi[axis])/2)
            if len(found)!=1:raise RuntimeError('Missing/ambiguous measured coupon face')
            return found[0]
        t,s=g.tab,g.slot;midz=18-g.engagement/2
        result={}
        for axis,name in ((0,'x'),(1,'y')):
            for side,index in (('low',0),('high',1)):
                result['tab_'+name+'_'+side]=coordinate(UPRIGHT,axis,(t.lo,t.hi)[index][axis],
                    {2:midz,1-axis:60 if axis==0 else 100})
                result['slot_'+name+'_'+side]=coordinate(RECEIVER,axis,(s.lo,s.hi)[index][axis],
                    {2:9,1-axis:60 if axis==0 else 100})
        result['receiver_top']=coordinate(RECEIVER,2,18,{0:10,1:10})
        result['tab_bottom']=coordinate(UPRIGHT,2,t.lo[2],{0:100,1:60})
        result['shoulder_left']=coordinate(UPRIGHT,2,18,{0:g.contact_x[0],1:60})
        result['shoulder_right']=coordinate(UPRIGHT,2,18,{0:g.contact_x[1],1:60})
        return result


def measure_coupon(design,coupon,guard,diameter):
    guard();source=CouponSource(design);report=measure_coupon_geometry(coupon,source)
    expected=coupon.blanks.parameters.resolve({'Joint_Tool_Diameter':diameter})
    checks=report['checks']
    def check(name,ok,**data):checks.append(dict(check_id=name,status='PASS' if ok else 'FAIL',**data))
    check('coupon.parameters',all(abs(report['parameters_mm'][n]-v)<=0.001 for n,v in expected.items()))
    counts=_design_counts(design);root=design.rootComponent;marker=design.timeline.markerPosition
    check('coupon.inventory',counts==dict(user_parameters=4,root_occurrences=2,all_components=3,timeline_items=20)
          and root.bRepBodies.count==0 and root.sketches.count==0 and marker==20,observed=counts)
    occ=_find_occurrences(root)
    if set(occ)!={RECEIVER,UPRIGHT} or any(len(v)!=1 for v in occ.values()):
        raise RuntimeError('Ambiguous ownership')
    features={}
    for pid,items in occ.items():
        comp=items[0].component;n=6 if pid==RECEIVER else 3
        check(pid+'.inventory',comp.bRepBodies.count==1 and comp.bRepBodies.item(0).isSolid
              and comp.bRepBodies.item(0).isValid and comp.features.count==n
              and comp.features.extrudeFeatures.count==n and comp.sketches.count==n)
        for i in range(comp.features.extrudeFeatures.count):
            f=comp.features.extrudeFeatures.item(i)
            check(pid+'.feature.%d'%i,f.healthState==adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState and not f.isSuppressed)
            if f.operation==adsk.fusion.FeatureOperations.CutFeatureOperation:
                if f.name in features:raise RuntimeError('Duplicate cut identity')
                features[f.name]=f
        for i in range(comp.sketches.count):
            sketch=comp.sketches.item(i)
            check(pid+'.sketch.%d'%i,sketch.isFullyConstrained and sketch.profiles.count==1
                  and sketch.healthState==adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState)
    if set(features)!=set(CUT_IDS):raise RuntimeError('Unexpected cut inventory')
    if any(c['status']!='PASS' for c in checks):
        report.update(counts=counts,outcome='FAIL')
        return report  # No timeline writes after an earlier failed measurement.
    for cid,owner in zip(CUT_IDS,OWNERS):
        f=features[cid]
        try:
            guard()
            if not f.timelineObject.rollTo(True):raise RuntimeError('Cut ownership readback unavailable')
            participants=[]
            for body in f.participantBodies:
                attr=body.parentComponent.attributes.itemByName(ATTR_GROUP,ATTR_ID)
                participants.append(attr.value if attr else None)
            parent=f.parentComponent.attributes.itemByName(ATTR_GROUP,ATTR_ID)
            check(cid+'.ownership',participants==[owner] and parent is not None and parent.value==owner,
                  participants=participants,expected_owner=owner)
        finally:
            guard();design.timeline.markerPosition=marker
        if design.timeline.markerPosition!=marker or design.timeline.count!=marker:
            raise RuntimeError('Ownership timeline restoration failed')
        if checks[-1]['status']!='PASS':break
    guard()
    report.update(counts=counts,outcome='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL')
    return report


def run_tab_slot(app,output_dir,guard):
    path=Path(output_dir)/'tab_slot.json'
    if path.exists():raise RuntimeError('Existing report; no retry')
    path.parent.mkdir(parents=True,exist_ok=True)
    payload=dict(outcome='FAIL',stages=[],refusal=None,construction_cuts=[])
    try:
        guard();doc=app.activeDocument;design=adsk.fusion.Design.cast(app.activeProduct)
        if (doc.isSaved or doc.isModified or design.designType!=adsk.fusion.DesignTypes.ParametricDesignType
                or design.rootComponent.occurrences.count or design.rootComponent.bRepBodies.count
                or design.rootComponent.sketches.count or design.userParameters.count or design.timeline.count):
            raise RuntimeError('New empty unsaved parametric fixture required')
        coupon=build_tab_slot(TabSlotSpec());payload['specification']=json.loads(coupon.spec.to_json())
        payload['spec_hash']=coupon.spec.spec_hash()
        CouponAdapter(design).compile_coupon(coupon,guard,payload['construction_cuts'])
        p=design.userParameters.itemByName('Joint_Tool_Diameter');original=p.expression
        for diameter in (6,8,6):
            if payload['stages']:
                preview_tab_slot(coupon.blanks.parameters.resolve({'Joint_Tool_Diameter':diameter}))
                guard();p.expression=original if diameter==6 else '8 mm'
                guard();adsk.doEvents()
            stage=measure_coupon(design,coupon,guard,diameter);payload['stages'].append(stage)
            if stage['outcome']!='PASS':raise RuntimeError('Coupon measurement failed; no automatic restoration')
            if len(payload['stages'])==1:payload['baseline_state']=snapshot(design)
        payload['restored_state']=snapshot(design)
        if (payload['baseline_state']!=payload['restored_state'] or not
                restored_storage_measurements(payload['stages'][0],payload['stages'][-1])):
            raise RuntimeError('Coupon restoration differs')
        guard()
        try:preview_tab_slot(dict(payload['stages'][-1]['parameters_mm'],Joint_Tool_Diameter=12))
        except ValueError as exc:
            if 'circles overlap' not in str(exc):raise RuntimeError('Unexpected refusal reason') from exc
            payload['refusal']=dict(outcome='REFUSED',tool_diameter_mm=12,reason=str(exc))
        else:raise RuntimeError('Invalid tool diameter not refused')
        payload['after_refusal']=measure_coupon(design,coupon,guard,6);payload['final_state']=snapshot(design)
        if (payload['final_state']!=payload['restored_state'] or not
                restored_storage_measurements(payload['stages'][-1],payload['after_refusal'])):
            raise RuntimeError('Refusal changed geometry or state')
        guard();app.activeViewport.fit();payload['outcome']='PASS'
    except Exception as exc:
        payload['error']=str(exc);raise
    finally:path.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    return str(path)
