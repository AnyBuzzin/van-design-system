import adsk.core,sys,json,time,pathlib
def run(context):
 app=adsk.core.Application.get();st=sys.modules['_vandesign_v5_demo_g4'];doc=st.document
 assert app.activeDocument==doc and not doc.isSaved and doc.name==st.name
 assert [st.info(d) for d in st.protected]==st.before
 out=pathlib.Path(r'C:\Users\Buzz\Documents\VanDesign-V5-demonstration-g4-20261018')
 assert json.loads((out/'baseline-build.json').read_text())['outcome']=='PASS'
 assert not hasattr(st,'save_attempted');st.save_attempted=True
 assert not any(st.folder.dataFiles.item(i).name.casefold()==st.name.casefold() for i in range(st.folder.dataFiles.count))
 assert doc.saveAs(st.name,st.folder,'Owner-approved disposable G4 shelf-count qualification',''), 'Save uncertain; no retry'
 deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  adsk.doEvents()
  if doc.isSaved and doc.dataFile and doc.dataFile.isComplete:break
  time.sleep(.1)
 assert doc.isSaved and doc.dataFile.isComplete and not doc.isModified
 assert doc.dataFile.parentFolder.id==st.folder.id and doc.dataFile.versionNumber==1
 assert [st.info(d) for d in st.protected]==st.before
 st.design_id=doc.dataFile.id
 result={'saved_once':True,'identity':st.info(doc),'complete':doc.dataFile.isComplete,'existing_documents_unchanged':True}
 (out/'first-save.private.json').write_text(json.dumps(result,indent=2))
 print(json.dumps({'saved_once':True,'version':doc.dataFile.versionNumber,'clean':not doc.isModified,'existing_documents_unchanged':True}))
