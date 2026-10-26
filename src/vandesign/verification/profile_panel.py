"""CAD-neutral expected profile measurements and material-side probes."""
import math
from types import SimpleNamespace

from ..manufacturing.profile import Arc, Hole, Pocket, PanelFrame, contains_point, contains_world_point
from ..modules.profile_fixture import (PARAMETER, PARAMETERS, feature_loop, feature_depth,
                                       feature_id, feature_start, inventory, resolve_profiles, spec_hash)


def world_probes(profile):
    """Reuse boundary sampling, with exact core material truth in world space."""
    if type(profile.frame) is not PanelFrame:
        raise ValueError('World probes require a validated PanelFrame')
    result = []
    for cid, local, _ in probes(SimpleNamespace(profile=profile, origin=(0, 0, 0))):
        world = profile.frame.to_world(*local)
        expected = contains_world_point(profile, world)
        if type(expected) is not bool:
            raise ValueError('Ambiguous world material probe')
        result.append((cid, world, expected))
    return result


def probes(panel):
    """Both sides of every boundary, including every arc/relief; no BBox proxy."""
    p = panel.profile
    loops = [('outline', p.outline, p.thickness/2, True)]
    for i, f in enumerate(p.features):
        depth = feature_depth(f).eval({PARAMETER: p.thickness})
        z = feature_start(f).eval({PARAMETER: p.thickness})+depth/2
        loops.append(('cut.%03d' % (i+1), feature_loop(f), z, False))
    result = []
    for name, loop, z, material_inside in loops:
        for i, seg in enumerate(loop.segments):
            for j, fraction in enumerate((0.25, 0.5, 0.75) if isinstance(seg, Arc) else (0.5,)):
                if isinstance(seg, Arc):
                    a = seg.start_angle+seg.sweep*fraction
                    x, y = seg._point(a)
                    nx, ny = -math.cos(a)*math.copysign(1, seg.sweep), -math.sin(a)*math.copysign(1, seg.sweep)
                else:
                    x, y = ((a+b)/2 for a, b in zip(seg.start, seg.end))
                    dx, dy = seg.end[0]-seg.start[0], seg.end[1]-seg.start[1]
                    length = math.hypot(dx, dy); nx, ny = -dy/length, dx/length
                for sign in (-1, 1):
                    xy = (x+sign*0.05*nx, y+sign*0.05*ny)
                    inside = contains_point(loop, xy)
                    if inside is None or inside is not (sign == 1):
                        raise ValueError('Unsupported narrow/ambiguous material probe')
                    point = (xy[0]+panel.origin[0], xy[1]+panel.origin[1], z+panel.origin[2])
                    result.append((f'{p.panel_id}.{name}.{i}.{j}.{sign}', point,
                                   inside if material_inside else not inside))
    # Blind features must remove material only to their specified depth.
    for i, f in enumerate(p.features):
        if isinstance(f, (Pocket, Hole)) and f.depth is not None:
            loop = feature_loop(f);lo, hi = loop.bounds;xy = tuple((a+b)/2 for a,b in zip(lo,hi))
            if contains_point(loop, xy) is not True:
                raise ValueError('Unsupported blind feature centre')
            boundary = p.thickness-f.depth if f.face == 'top' else f.depth
            for sign in (-1,1):
                result.append((f'{p.panel_id}.depth.{i}.{sign}',
                               (xy[0]+panel.origin[0],xy[1]+panel.origin[1],boundary+sign*0.05+panel.origin[2]),
                               sign == (-1 if f.face == 'top' else 1)))
    return result


def measure_profiles(source, values):
    panels = resolve_profiles(values);checks=[];bodies={}
    def numeric(cid, observed, expected, tolerance, ids=()):
        valid = type(observed) in (int,float) and math.isfinite(observed)
        checks.append(dict(check_id=cid, status='UNKNOWN' if not valid else 'PASS' if abs(observed-expected)<=tolerance else 'FAIL',
                           observed=observed, expected=expected, tolerance=tolerance, object_ids=list(ids),
                           unit='mm3' if cid.endswith('.volume') else 'mm'))
    params = {p.name:source.parameter_value(p.name) for p in PARAMETERS.params}
    for name, value in PARAMETERS.resolve(values).items():numeric(name,params[name],value,1e-6)
    census = source.managed_ids()
    checks.append(dict(check_id='profiles.ids',status='UNKNOWN' if census is None else 'PASS' if census=={p.profile.panel_id:1 for p in panels} else 'FAIL'))
    for panel in panels:
        pid=panel.profile.panel_id;body=source.body(pid)
        if body is None:
            checks.append(dict(check_id=pid+'.body',status='UNKNOWN'));continue
        bodies[pid]=dict(min=body.box.lo,max=body.box.hi,volume_mm3=body.volume_mm3)
        numeric(pid+'.volume',body.volume_mm3,panel.profile.volume_mm3,max(1,panel.profile.volume_mm3*1e-6),(pid,))
        for axis in range(3):
            for side in ('lo','hi'):numeric(f'{pid}.{side}.{axis}',getattr(body.box,side)[axis],getattr(panel.box,side)[axis],0.01,(pid,))
        for cid,point,expected in probes(panel):
            actual=source.point_in_material(pid,point)
            checks.append(dict(check_id=cid,status='UNKNOWN' if actual is None else 'PASS' if actual is expected else 'FAIL',
                               observed=actual,expected=expected,point_mm=point,object_ids=[pid]))
    numeric('profiles.interference',source.interference_count([p.profile.panel_id for p in panels]),0,0)
    return dict(outcome='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL',checks=checks,
                parameters_mm=params,bodies=bodies)


def expected_evidence():
    """Model-derived acceptance contract for the existing Runner validator."""
    stages=[];required=[]
    for label,t in [('baseline',18),('edit_'+PARAMETER,20),('restore_'+PARAMETER,18),('after_refusal_'+PARAMETER,18)]:
        panels=resolve_profiles({PARAMETER:t});numeric={PARAMETER:(t,1e-6),'profiles.interference':(0,0)}
        boxes={};volumes={};required=['profiles.ids','profiles.interference','profiles.inventory']
        for panel in panels:
            pid=panel.profile.panel_id;boxes[pid]=(list(panel.box.lo),list(panel.box.hi));volumes[pid]=panel.profile.volume_mm3
            numeric[pid+'.volume']=(volumes[pid],max(1,volumes[pid]*1e-6))
            for axis in range(3):
                for side in ('lo','hi'):numeric[f'{pid}.{side}.{axis}']=(getattr(panel.box,side)[axis],0.01)
            required += [cid for cid,_,_ in probes(panel)] + [pid+'.features']
            required += [feature_id(panel.profile,i)+'.affected_body_ownership' for i in range(len(panel.profile.features))]
        required += list(numeric)
        stages.append(dict(label=label,parameters_mm={PARAMETER:t},boxes=boxes,volumes=volumes,numeric=numeric))
    construction=[dict(cut_id=feature_id(p.profile,i),owner=p.profile.panel_id,
                       removed_mm3=feature_loop(f).area*feature_depth(f).eval({PARAMETER:18}))
                  for p in resolve_profiles() for i,f in enumerate(p.profile.features)]
    return dict(spec_hash=spec_hash(),instances=[p.profile.panel_id for p in panels],body_ids=sorted(boxes),
                construction_cuts=construction,
                parameter_names=[PARAMETER],inventory=inventory(panels),required_checks=sorted(set(required)),stages=stages,
                edits=[dict(parameter=PARAMETER,value_mm=20,expect='pass'),dict(parameter=PARAMETER,value_mm=5,expect='refused')])
