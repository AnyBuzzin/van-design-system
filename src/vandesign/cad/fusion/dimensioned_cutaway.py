"""Owned, unsaved-only visual checkpoint. No document lifecycle or parameter edits."""
import json
from pathlib import Path
import adsk.core
import adsk.fusion
from .adapter import FusionAdapter
from .storage_box import measure_storage
from ...modules.dimensioned_cutaway import build_dimensioned_cutaway, dimension_labels
from ...modules.test_envelope import furniture_rows, REFERENCE


def point(x,y,z=0):
    return adsk.core.Point3D.create(x/10,y/10,z/10)


def annotate(design, env, labels, guard):
    root=design.rootComponent
    guard()
    plane_input=root.constructionPlanes.createInput()
    if not plane_input.setByOffset(root.xYConstructionPlane,
            adsk.core.ValueInput.createByString('Test_Height')):
        raise RuntimeError('Roof plane unavailable')
    plane=root.constructionPlanes.add(plane_input)
    plane.isLightBulbOn=False
    roof=root.sketches.add(plane);roof.name='REFERENCE ONLY - open roof outline'
    roof.isVisible=True
    w,l,h=(env[k] for k in ('Test_Width','Test_Length','Test_Height'))
    corners=[(0,0,h),(w,0,h),(w,l,h),(0,l,h)]
    lines=[]
    for a,b in zip(corners,corners[1:]+corners[:1]):
        line=roof.sketchCurves.sketchLines.addByTwoPoints(point(a[0],a[1]),point(b[0],b[1]))
        line.isFixed=True
        lines.append(line)
    sketch=root.sketches.add(root.xYConstructionPlane)
    sketch.name='TEST ONLY - measured dimension snapshot';sketch.isVisible=True
    root.isSketchFolderLightBulbOn=True
    texts=[]
    for i,label in enumerate(labels):
        guard()
        text_input=sketch.sketchTexts.createInput3("'"+label+"'",adsk.core.ValueInput.createByString('28 mm'))
        if not text_input.setAsMultiLine(point(-2300,3000-i*180),point(-150,2870-i*180),
                adsk.core.HorizontalAlignments.LeftHorizontalAlignment,
                adsk.core.VerticalAlignments.TopVerticalAlignment,0):
            raise RuntimeError('Label placement unavailable')
        text=sketch.sketchTexts.add(text_input)
        if text is None or text.text!=label: raise RuntimeError('Visible label readback mismatch')
        texts.append(text)
    guard()
    observed=[]
    for line,(a,b) in zip(lines,zip(corners,corners[1:]+corners[:1])):
        ends=[line.startSketchPoint.worldGeometry,line.endSketchPoint.worldGeometry]
        values=[(p.x*10,p.y*10,p.z*10) for p in ends]
        if any(abs(x-y)>0.01 for p,q in zip(values,(a,b)) for x,y in zip(p,q)):
            raise RuntimeError('Roof outline does not span full clear interior')
        observed.append(values)
    if not roof.isVisible or not sketch.isVisible or not root.isSketchFolderLightBulbOn:
        raise RuntimeError('Reference annotations not visible')
    return dict(labels=[t.text for t in texts],roof_segments_mm=observed,
                label_visibility='PASS',label_legibility='UNKNOWN - requires captured-image review')


def captures(app, out, env, guard):
    viewport=app.activeViewport
    paths={}
    for name,eye,up in [('cutaway',(-3500,-4200,4200),(0,0,1)),
                        ('plan',(0,1500,6000),(0,1,0))]:
        guard()
        camera=viewport.camera
        camera.isSmoothTransition=False
        camera.cameraType=adsk.core.CameraTypes.OrthographicCameraType
        camera.target=point(0,1500,700 if name=='cutaway' else 0)
        camera.eye=point(*eye);camera.upVector=adsk.core.Vector3D.create(*up)
        camera.isFitView=True
        viewport.camera=camera
        if not viewport.refresh(): raise RuntimeError('Viewport refresh failed')
        guard()
        path=out/(name+'.png')
        if not viewport.saveAsImageFile(str(path),2400,1800) or not path.is_file():
            raise RuntimeError('Required visual capture unavailable')
        paths[name]=str(path)
    return paths


def run_dimensioned_cutaway(app, output_dir, guard):
    out=Path(output_dir);path=out/'dimensioned_cutaway.json'
    if path.exists(): raise RuntimeError('Existing visual report; no retry')
    payload=dict(outcome='FAIL',visual_review='UNKNOWN - owner/Jack image review required')
    out.mkdir(parents=True,exist_ok=True)
    try:
        guard()
        design=adsk.fusion.Design.cast(app.activeProduct);doc=app.activeDocument
        if (doc.isSaved or doc.isModified or design.designType!=adsk.fusion.DesignTypes.ParametricDesignType
                or design.rootComponent.occurrences.count or design.rootComponent.bRepBodies.count
                or design.rootComponent.sketches.count or design.userParameters.count or design.timeline.count):
            raise RuntimeError('Fresh empty unsaved parametric fixture required')
        assembly=build_dimensioned_cutaway()
        guard();FusionAdapter(design).compile(assembly)
        before=measure_storage(design,assembly,guard,600)
        payload.update(before=before,furniture_cut_list=furniture_rows(assembly),spec_hash=assembly.spec_hash)
        labels=dimension_labels(assembly,before)
        payload['annotations']=annotate(design,before['parameters_mm'],labels,guard)
        after=measure_storage(design,assembly,guard,600,expected_timeline=70)
        payload['after']=after
        if after['outcome']!='PASS' or dimension_labels(assembly,after)!=labels:
            raise RuntimeError('Post-annotation measured geometry or label values changed')
        if before['parameters_mm']!=after['parameters_mm']:
            raise RuntimeError('Annotations changed furniture parameters')
        for sid,body in before['bodies'].items():
            other=after['bodies'][sid]
            if (body['min']!=other['min'] or body['max']!=other['max']
                    or abs(body['volume_mm3']-other['volume_mm3'])>1e-6):
                raise RuntimeError('Annotations changed measured solids')
        # Explicitly test new reference walls against furniture, independently of cut-list filtering.
        source=FusionAdapter(design).geometry_source()
        ids=[p.stable_id for p in assembly.panels if not p.stable_id.startswith(REFERENCE)]
        overlaps={sid:source.interference_count(ids+[sid]) for sid in ('reference.right','reference.front','reference.floor')}
        payload['reference_interference']=overlaps
        if any(v!=0 for v in overlaps.values()): raise RuntimeError('Reference/furniture overlap or unavailable measurement')
        payload['captures']=captures(app,out,after['parameters_mm'],guard)
        guard();payload['outcome']='PASS'
    except Exception as exc:
        payload['error']=str(exc);raise
    finally:
        path.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    return payload
