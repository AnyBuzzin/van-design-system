"""Finished coupon verification, separate from generic blank/dado validation."""
import math

from ..core.tab_slot import RECEIVER, UPRIGHT
from ..modules.tab_slot import NAMES, preview_tab_slot
from .report import Check, ValidationReport, PASS, FAIL, UNKNOWN


def measure_coupon_geometry(coupon, source):
    env={n:source.parameter_value(n) for n in NAMES}
    g=coupon.geometry(env)  # Incomplete/nonfinite/invalid evidence stops, never PASS.
    rep=ValidationReport()
    bodies={pid:source.body(pid) for pid in (RECEIVER,UPRIGHT)}
    for pid,m in bodies.items():
        if (m is None or any(type(v) not in (int,float) or not math.isfinite(v)
                            for v in m.box.lo+m.box.hi+(m.volume_mm3,))
                or min(m.box.size)<=0 or m.volume_mm3<=0):
            raise ValueError('Incomplete finite coupon BRep: '+pid)
        deviation,_=g.bounds[pid].max_deviation(m.box)
        rep.add(Check(pid+'.bbox',PASS if deviation<=0.01 else FAIL,deviation,0,0.01,'mm',(pid,)))
        volume=g.volumes[pid];tol=max(1,volume*1e-6)
        rep.add(Check(pid+'.volume',PASS if abs(m.volume_mm3-volume)<=tol else FAIL,
                      m.volume_mm3,volume,tol,'mm3',(pid,),'finished joint, overlapping cutter areas counted once'))
    census=source.managed_ids()
    rep.add(Check('coupon.identities',UNKNOWN if census is None else PASS if census=={RECEIVER:1,UPRIGHT:1} else FAIL))
    interference=source.interference_count((RECEIVER,UPRIGHT))
    rep.add(Check('coupon.interference',UNKNOWN if interference is None else PASS if interference==0 else FAIL,
                  interference,0,0,'pairs',(RECEIVER,UPRIGHT)))
    probes=[(RECEIVER,'slot',(100,60,9),False),(RECEIVER,'retained',(10,10,9),True),
            (UPRIGHT,'tab',(100,60,18-g.engagement/2),True),(UPRIGHT,'body',(100,60,68),True)]
    for i,shoulder in enumerate(g.shoulders):
        x=(shoulder.lo[0]+shoulder.hi[0])/2
        probes.extend(((UPRIGHT,'shoulder.%d'%i,(x,60,18-g.engagement/2),False),
                       (UPRIGHT,'contact.above.%d'%i,(g.contact_x[i],60,18.1),True),
                       (RECEIVER,'contact.below.%d'%i,(g.contact_x[i],60,17.9),True)))
    # Probe removed caps beyond each rectangle edge, and retained material beyond
    # the circle. At these points a plain slot without relief cannot pass.
    for i,(cx,cy) in enumerate(g.centres):
        for axis,sign in ((0,-1 if cx<100 else 1),(1,-1 if cy<60 else 1)):
            for label,factor,inside in (('cap',0.95,False),('outside',1.05,True)):
                p=[cx,cy,9];p[axis]+=sign*g.radius*factor
                probes.append((RECEIVER,'relief.%d.%d.%s'%(i,axis,label),tuple(p),inside))
    for pid,name,point,expected in probes:
        observed=source.point_in_material(pid,point)
        rep.add(Check('coupon.material.'+name,UNKNOWN if observed is None else PASS if observed is expected else FAIL,
                      object_ids=(pid,),note='point_mm=%r; expected=%r; observed=%r'%(point,expected,observed)))
    # Plane positions come from actual BRep faces, not model parameter arithmetic.
    faces=source.coupon_faces(g)
    metrics={}
    for axis in ('x','y'):
        for side in ('low','high'):
            a=faces['tab_'+axis+'_'+side];b=faces['slot_'+axis+'_'+side]
            gap=a-b if side=='low' else b-a
            metrics['clearance_'+axis+'_'+side]=gap
    metrics['engagement']=faces['receiver_top']-faces['tab_bottom']
    metrics['shoulder_left_contact']=faces['shoulder_left']-faces['receiver_top']
    metrics['shoulder_right_contact']=faces['shoulder_right']-faces['receiver_top']
    for name,v in metrics.items():
        expected=g.clearance/2 if name.startswith('clearance') else g.engagement if name=='engagement' else 0
        if type(v) not in (int,float) or not math.isfinite(v):
            raise ValueError('Unavailable coupon face measurement')
        rep.add(Check('coupon.'+name,PASS if abs(v-expected)<=0.01 else FAIL,v,expected,0.01,'mm',(RECEIVER,UPRIGHT)))
    return dict(outcome=rep.verdict,checks=[c.to_dict() for c in rep.checks],parameters_mm=env,
                measured_faces_mm=faces,measured_fit_mm=metrics,preview=preview_tab_slot(env),
                bodies={pid:dict(min=m.box.lo,max=m.box.hi,volume_mm3=m.volume_mm3) for pid,m in bodies.items()})
