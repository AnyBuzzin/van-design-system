"""Five butt-contact panels; nominal geometry, no load or access qualification."""
from dataclasses import replace
import hashlib
import math
from itertools import combinations

from ..cad.protocol import preflight
from ..components.model import AssemblyDefinition, Panel, Constraint
from ..core.expr import Mm, Param
from ..core.geometry import Box, BoxExpr
from ..core.params import ParameterSet, ParamDef
from ..schemas.storage_box_spec import StorageBoxSpec, NOTICE
from .test_envelope import build_test_envelope, preview_fit, ARCHES

PREFIX = 'storage.001.'
PLACEMENT = (592, 600, 0)
RESTORATION_VOLUME_EPSILON_MM3 = 1e-6


def restored_storage_measurements(before, after):
    """Only BRep volume readback noise may differ; never rewrite raw evidence."""
    if not isinstance(before,dict) or not isinstance(after,dict):
        return False
    if before.get('outcome')!='PASS' or after.get('outcome')!='PASS':
        return False
    if {k:v for k,v in before.items() if k not in ('bodies','checks')} != {
            k:v for k,v in after.items() if k not in ('bodies','checks')}:
        return False
    bodies=before.get('bodies'); other=after.get('bodies')
    if not isinstance(bodies,dict) or not bodies or not isinstance(other,dict) or bodies.keys()!=other.keys():
        return False
    def finite(v):
        return type(v) in (int,float) and math.isfinite(v)
    for sid,body in bodies.items():
        restored=other[sid]
        if not isinstance(body,dict) or not isinstance(restored,dict):
            return False
        a,b=body.get('volume_mm3'),restored.get('volume_mm3')
        if not finite(a) or not finite(b) or min(a,b)<=0 or abs(a-b)>RESTORATION_VOLUME_EPSILON_MM3:
            return False
        if {k:v for k,v in body.items() if k!='volume_mm3'} != {k:v for k,v in restored.items() if k!='volume_mm3'}:
            return False
    checks=before.get('checks'); others=after.get('checks')
    if not isinstance(checks,list) or not isinstance(others,list) or len(checks)!=len(others):
        return False
    volume_ids={sid+'.volume':sid for sid in bodies}
    seen=set()
    for a,b in zip(checks,others):
        if not isinstance(a,dict) or not isinstance(b,dict) or a.get('status')!='PASS' or b.get('status')!='PASS':
            return False
        cid=a.get('check_id')
        if cid in volume_ids:
            sid=volume_ids[cid]
            if cid in seen or a.get('unit')!='mm3' or a.get('object_ids')!=[sid]:
                return False
            seen.add(cid)
            for check,body in ((a,bodies[sid]),(b,other[sid])):
                obs,expected,tol=(check.get(k) for k in ('observed','expected','tolerance'))
                if (not all(finite(v) for v in (obs,expected,tol)) or tol<0
                        or obs!=body['volume_mm3'] or abs(obs-expected)>tol):
                    return False
            if {k:v for k,v in a.items() if k!='observed'} != {k:v for k,v in b.items() if k!='observed'}:
                return False
        elif a!=b:
            return False
    return seen==set(volume_ids)


def build_storage_box(spec: StorageBoxSpec):
    if not isinstance(spec, StorageBoxSpec):
        raise TypeError('StorageBoxSpec required')
    parameters = ParameterSet(tuple(ParamDef(n, value_mm=v, comment=NOTICE) for n,v in (
        ('Storage_Width', spec.width_mm), ('Storage_Length', spec.length_mm),
        ('Storage_Height', spec.height_mm), ('Storage_Ply', spec.ply_mm))))
    w,l,h,t = map(Param, parameters.names())
    z = Mm(0)
    def panel(sid, role, origin, size):
        return Panel('storage.'+sid+'.001', 'Storage '+sid, role, 'ply_18_nominal', BoxExpr(origin,size))
    panels = (
        panel('bottom','bottom',(z,z,z),(w,l,t)),
        panel('left','left',(z,z,t),(t,l,h-t)),
        panel('right','right',(w-t,z,t),(t,l,h-t)),
        panel('front','back',(t,z,t),(w-2*t,t,h-t)),
        panel('rear','back',(t,l-t,t),(w-2*t,t,h-t)))
    constraints = (
        Constraint('storage.width','Positive interior width',w,'>',2*t),
        Constraint('storage.length','Positive interior length',l,'>',2*t),
        Constraint('storage.height','Positive interior height',h,'>',t),
        Constraint('storage.ply_min','Nominal 18 mm only',t,'>=',Mm(18)),
        Constraint('storage.ply_max','Nominal 18 mm only',Mm(18),'>=',t))
    assembly = AssemblyDefinition('storage.box.001',spec.spec_hash(),parameters,panels,(),constraints)
    preflight(assembly)
    return assembly


def build_storage_scene():
    scene = build_test_envelope()
    box = build_storage_box(StorageBoxSpec())
    panels = tuple(replace(p, stable_id=PREFIX+p.stable_id,
        box=BoxExpr(tuple(e+Mm(v) for e,v in zip(p.box.origin,PLACEMENT)),p.box.size)) for p in box.panels)
    assembly = replace(scene, assembly_id='test.storage_box.001',
        spec_hash=hashlib.sha256((scene.spec_hash+box.spec_hash+str(PLACEMENT)).encode()).hexdigest(),
        panels=scene.panels+panels, parameters=ParameterSet(scene.parameters.params+box.parameters.params),
        constraints=scene.constraints+box.constraints)
    preflight(assembly)
    preview_storage(assembly,assembly.parameters.resolve())
    return assembly


def envelope(boxes):
    return Box(tuple(min(b.lo[i] for b in boxes) for i in range(3)),
               tuple(max(b.hi[i] for b in boxes) for i in range(3)))


def preview_storage(assembly, env, boxes=None):
    # Existing complete/finite bounds, parameter and constraint checks first.
    preview_fit(assembly,env,boxes)
    boxes = boxes if boxes is not None else {p.stable_id:p.box.resolve(env) for p in assembly.panels}
    stored = {k:b for k,b in boxes.items() if k.startswith(PREFIX)}
    if len(stored)!=5:
        raise ValueError('Exactly five storage panels required')
    occupied = envelope(list(stored.values()))
    obstacles = [b for k,b in boxes.items() if k.startswith('bed.001.') or k in ARCHES]
    obstacles.append(envelope([b for k,b in boxes.items() if k.startswith('cabinet.001.')]))
    if any(occupied.overlap_volume(b)>1e-6 for b in obstacles):
        raise ValueError('Storage occupies bed material, cabinet or assumed arch')
    if any(a.overlap_volume(b)>1e-6 for a,b in combinations(stored.values(),2)):
        raise ValueError('Storage panels overlap')
    return dict(top_to_deck_mm=boxes['bed.001.bed.deck.001'].lo[2]-occupied.hi[2],
                left_arch_gap_mm=occupied.lo[0]-boxes[ARCHES[0]].hi[0],
                right_arch_gap_mm=boxes[ARCHES[1]].lo[0]-occupied.hi[0])


def storage_contacts(boxes):
    """Eight intended butt contacts, measured from rectangular BRep bounds."""
    b = {name: boxes[PREFIX+'storage.'+name+'.001'] for name in ('bottom','left','right','front','rear')}
    pairs = [('bottom',n,2) for n in ('left','right','front','rear')]
    pairs += [('left',n,0) for n in ('front','rear')]+[(n,'right',0) for n in ('front','rear')]
    return {a+'.'+c: abs(b[a].hi[axis]-b[c].lo[axis])<=0.01 and all(
        min(b[a].hi[i],b[c].hi[i])-max(b[a].lo[i],b[c].lo[i])>0.01
        for i in range(3) if i!=axis) for a,c,axis in pairs}


def preview_invalid_storage(assembly, env):
    boxes = {p.stable_id:p.box.resolve(env) for p in assembly.panels}
    for sid,b in list(boxes.items()):
        if sid.startswith(PREFIX):
            boxes[sid]=Box((b.lo[0]+500,b.lo[1],b.lo[2]),(b.hi[0]+500,b.hi[1],b.hi[2]))
    try:
        preview_storage(assembly,env,boxes)
    except ValueError as exc:
        return dict(outcome='REFUSED', reason=str(exc), proposed_storage_delta_x_mm=500)
    return dict(outcome='FAIL', reason='Unsafe storage move was not refused')


def phase_a_persistence_matches(before, after):
    """Compare geometry with distinct pre-save participant/post-reopen affected-body proofs.

    Does not establish persistence of the configured participant list.
    Original reports are retained; the unchanged volume epsilon comparator is reused.
    """
    operations=build_storage_scene().operations
    if len(operations)!=2: return False
    def geometry(report, reopened):
        if not isinstance(report,dict) or report.get('outcome')!='PASS': return None
        checks=report.get('checks')
        if not isinstance(checks,list): return None
        suffix='.affected_body_ownership' if reopened else '.ownership'
        expected={op.operation_id+suffix:op.target_panel_id for op in operations}
        found=[c for c in checks if isinstance(c,dict) and c.get('check_id') in expected]
        if len(found)!=2 or {c['check_id'] for c in found}!=set(expected):return None
        for c in found:
            target=expected[c['check_id']]
            if c.get('status')!='PASS':return None
            if reopened:
                if c.get('affected_bodies')!=[target] or c.get('feature_parent')!=target:return None
            elif c.get('participants')!=[target]:return None
        return dict(report,checks=[c for c in checks if c not in found])
    a,b=geometry(before,False),geometry(after,True)
    return a is not None and b is not None and restored_storage_measurements(a,b)
