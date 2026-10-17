import adsk.core,adsk.fusion,sys,json,pathlib
from fusion_backend import FusionBackend
from vdrunner.shelf_change import equivalent
def run(context):
 app=adsk.core.Application.get();st=sys.modules['_vandesign_g4_qualification_20261017'];out=pathlib.Path(r'C:\Users\Buzz\Documents\VanDesign-Runner\issue20-live-20261017T212117Z')
 assert app.activeDocument==st.document and [st.info(d) for d in st.protected]==st.before
 cfg=json.loads((pathlib.Path(r'C:\Users\Buzz\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\VanDesignRunner')/'config.json').read_text());b=FusionBackend(app,cfg)
 r=json.loads((pathlib.Path(cfg['queue_root'])/'results/g4-live-20261017-no-op/result.json').read_text());assert r['outcome']=='FAIL' and r['steps'][0]['refused'] and r['steps'][0]['checks']==['no-op shelf count']
 assert equivalent(b.shelf_state()['inventory'],st.baseline)
 def fingerprint():
  design=adsk.fusion.Design.cast(app.activeProduct);root=design.rootComponent
  occs=[]
  for i in range(root.occurrences.count):
   o=root.occurrences.item(i);c=o.component;bs=[]
   for k in range(c.bRepBodies.count):
    body=c.bRepBodies.item(k);bb=body.boundingBox
    bs.append([body.volume,bb.minPoint.asArray(),bb.maxPoint.asArray(),body.faces.count,body.edges.count,body.vertices.count])
   occs.append([o.entityToken,c.name,c.features.count,c.sketches.count,bs])
  return {'occurrences':occs,'timeline':design.timeline.count,'components':design.allComponents.count,'params':[[design.userParameters.item(i).name,design.userParameters.item(i).expression,design.userParameters.item(i).value] for i in range(design.userParameters.count)]}
 st.fingerprint=fingerprint
 design=adsk.fusion.Design.cast(app.activeProduct)
 st.sentinel=design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create());st.sentinel.component.name='G4 refusal sentinel (test-created only)'
 st.sentinel_before=fingerprint()
 (out/'refusal-before.json').write_text(json.dumps({'no_op_refused_without_change':True,'sentinel_before':st.sentinel_before},indent=2))
 print(json.dumps({'no_op_refused_without_change':True,'sentinel_created_and_captured':True}))
