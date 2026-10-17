import adsk.core,sys,json,time
def run(context):
 app=adsk.core.Application.get();state=sys.modules['_vandesign_g3_fixture_20261017'];doc=state.document
 assert doc==app.activeDocument and doc.isSaved and doc.dataFile.id==state.design_id
 assert all(d.isValid and d.name==n and d.isSaved==s and d.isModified==m for d,n,s,m in state.protected)
 assert doc.save('G3 verified restored baseline; owner-approved persistence test')
 deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  adsk.doEvents()
  if not doc.isModified and doc.dataFile.isComplete:break
  time.sleep(0.1)
 assert not doc.isModified and doc.dataFile.isComplete
 print(json.dumps({'design_id':doc.dataFile.id,'version':doc.dataFile.versionNumber,'clean':not doc.isModified,'complete':doc.dataFile.isComplete}))
