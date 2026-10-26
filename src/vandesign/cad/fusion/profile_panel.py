"""Profile-driven fixed XY sketches; only trusted thickness Expr is editable.

Uses existing Fusion extrusion/ownership machinery. No document lifecycle API.
New CAD behaviour is UNKNOWN until separately authorised live qualification.
"""
import math
from types import SimpleNamespace

import adsk.core
import adsk.fusion

from .adapter import FusionAdapter, FusionGeometrySource, ATTR_GROUP, ATTR_ID, ATTR_GEN, GENERATOR_ID, _find_occurrences
from .runner import _design_counts
from .test_envelope import affected_body_check
from ...core.expr import Mm
from ...modules.profile_fixture import (PARAMETERS, PARAMETER, THICKNESS, feature_loop, feature_depth,
                                       feature_start, feature_id, inventory, validate_panels)
from ...verification.profile_panel import measure_profiles, probes
from ...manufacturing.profile import Line


class ProfileAdapter(FusionAdapter):
    def _loop_sketch(self, comp, name, loop, origin):
        sketch=comp.sketches.add(comp.xYConstructionPlane);sketch.name=name+' - profile'
        def point(xy):return adsk.core.Point3D.create((xy[0]+origin[0])/10,(xy[1]+origin[1])/10,0)
        for seg in loop.segments:
            if isinstance(seg,Line):
                curve=sketch.sketchCurves.sketchLines.addByTwoPoints(point(seg.start),point(seg.end))
            else:
                curve=sketch.sketchCurves.sketchArcs.addByCenterStartSweep(point(seg.center),point(seg.start),seg.sweep)
            if curve is None:raise RuntimeError('Profile curve creation failed')
            # Resolved XY geometry is explicitly fixed, never advertised as shape-parametric.
            curve.isFixed=True
        if sketch.profiles.count!=1:raise RuntimeError('Profile must produce one closed region')
        return sketch

    def compile_profiles(self, panels, guard, records):
        validate_panels(panels)
        for p in panels:
            probes(p)  # Refuse unsupported/narrow probe geometry before any CAD write.
            if p.profile.thickness!=18:raise ValueError('Initial fixture thickness must be 18 mm')
        guard()
        if (self.root.occurrences.count or self.root.bRepBodies.count or self.root.sketches.count
                or self.design.userParameters.count or self.design.timeline.count):
            raise RuntimeError('Empty design required')
        for p in PARAMETERS.params:
            self.design.userParameters.add(p.name,adsk.core.ValueInput.createByString(Mm(p.value_mm).render()),'mm',p.comment)
        components={}
        for item in panels:
            guard();p=item.profile;comp=self.root.occurrences.addNewComponent(adsk.core.Matrix3D.create()).component
            comp.name=p.display_name;comp.attributes.add(ATTR_GROUP,ATTR_ID,p.panel_id)
            comp.attributes.add(ATTR_GROUP,ATTR_GEN,GENERATOR_ID)
            sketch=self._loop_sketch(comp,p.panel_id,p.outline,item.origin)
            feature=self._extrude(comp,sketch,p.panel_id+' - solid',Mm(item.origin[2]).render(),THICKNESS.render(),
                                  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            feature.bodies.item(0).name=p.display_name;components[p.panel_id]=comp
        # All owners resolve before the first cut, including future feature targets.
        if any(c.bRepBodies.count!=1 for c in components.values()):raise RuntimeError('Ambiguous profile owner')
        for item in panels:
            p=item.profile;comp=components[p.panel_id]
            for index,f in enumerate(p.features):
                guard();cid=feature_id(p,index)
                before={pid:c.bRepBodies.item(0).volume*1000 for pid,c in components.items()}
                sketch=self._loop_sketch(comp,cid,feature_loop(f),item.origin)
                start=Mm(item.origin[2])+feature_start(f)
                cut=self._extrude(comp,sketch,cid,start.render(),feature_depth(f).render(),
                                  adsk.fusion.FeatureOperations.CutFeatureOperation,participants=[comp.bRepBodies.item(0)])
                cut.attributes.add(ATTR_GROUP,ATTR_ID,cid)
                after={pid:c.bRepBodies.item(0).volume*1000 for pid,c in components.items()}
                expected=feature_loop(f).area*feature_depth(f).eval({PARAMETER:p.thickness})
                ok=(all(math.isfinite(v) for v in (*before.values(),*after.values()))
                    and abs(before[p.panel_id]-after[p.panel_id]-expected)<=max(1,expected*1e-6)
                    and all(abs(before[pid]-after[pid])<=1e-6 for pid in components if pid!=p.panel_id))
                ownership=affected_body_check(cut,SimpleNamespace(operation_id=cid,target_panel_id=p.panel_id))
                ok=ok and ownership['status']=='PASS'
                records.append(dict(cut_id=cid,owner=p.panel_id,before_mm3=before,after_mm3=after,
                                    expected_removed_mm3=expected,ownership=ownership,outcome='PASS' if ok else 'FAIL'))
                if not ok:raise RuntimeError('Profile cut changed unexpected material; stop without rollback')
        guard()


def measure_profile_design(design,panels,guard,thickness):
    guard();source=FusionGeometrySource(design)
    report=measure_profiles(source,{PARAMETER:thickness});checks=report['checks'];counts=_design_counts(design)
    def check(cid,ok,**data):checks.append(dict(check_id=cid,status='PASS' if ok else 'FAIL',**data))
    root=design.rootComponent
    check('profiles.inventory',counts==inventory(panels) and root.bRepBodies.count==0 and root.sketches.count==0
          and design.timeline.markerPosition==design.timeline.count,observed=counts)
    occ=_find_occurrences(root)
    if set(occ)!={p.profile.panel_id for p in panels} or any(len(v)!=1 for v in occ.values()):
        raise RuntimeError('Ambiguous profile occurrence')
    healthy=adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState
    for item in panels:
        p=item.profile;comp=occ[p.panel_id][0].component;n=1+len(p.features)
        ok=(comp.bRepBodies.count==1 and comp.bRepBodies.item(0).isValid and comp.bRepBodies.item(0).isSolid
            and comp.features.count==n and comp.features.extrudeFeatures.count==n and comp.sketches.count==n)
        cuts={}
        for i in range(comp.features.extrudeFeatures.count):
            f=comp.features.extrudeFeatures.item(i)
            ok=ok and f.healthState==healthy and not f.isSuppressed
            if f.operation==adsk.fusion.FeatureOperations.CutFeatureOperation:
                attr=f.attributes.itemByName(ATTR_GROUP,ATTR_ID);cid=attr.value if attr else None
                if cid in cuts:raise RuntimeError('Duplicate profile cut identity')
                cuts[cid]=f
            elif f.operation!=adsk.fusion.FeatureOperations.NewBodyFeatureOperation:ok=False
        for i in range(comp.sketches.count):
            s=comp.sketches.item(i);ok=ok and s.profiles.count==1 and s.healthState==healthy and s.isFullyConstrained
        check(p.panel_id+'.features',ok)
        expected={feature_id(p,i) for i in range(len(p.features))}
        if set(cuts)!=expected:raise RuntimeError('Unexpected profile cut identities')
        for cid in sorted(cuts):
            checks.append(affected_body_check(cuts[cid],SimpleNamespace(operation_id=cid,target_panel_id=p.panel_id)))
    guard();report.update(counts=counts,outcome='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL')
    return report
