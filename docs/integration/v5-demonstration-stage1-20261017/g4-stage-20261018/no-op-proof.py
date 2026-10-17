import adsk.core,sys,json,pathlib,hashlib
from fusion_backend import FusionBackend

def run(context):
 app=adsk.core.Application.get();st=sys.modules['_vandesign_v5_demo_g4'];out=pathlib.Path(r'C:\Users\Buzz\Documents\VanDesign-V5-demonstration-g4-20261018')
 assert app.activeDocument==st.document and st.document.dataFile.id==st.design_id and st.document.dataFile.versionNumber==1
 assert app.documents.count==len(st.protected)+1 and [st.info(d) for d in st.protected]==st.before
 cfg=json.loads(pathlib.Path(r'C:\Users\Buzz\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\VanDesignRunner\config.json').read_text());current=FusionBackend(app,cfg).shelf_state()
 assert current==st.noop_before,'No-op refusal changed model state'
 job=json.loads(pathlib.Path(r'C:\Users\Buzz\Documents\VanDesign-Runner\queue\results\v5demo-g4-20261018-no-op\result.json').read_text())
 assert job['outcome']=='FAIL'
 result={'expected_refusal_job':job,'exact_before_after_state_equal':True,'before':st.noop_before,'after':current,'protected_unchanged':True}
 (out/'no-op-proof.private.json').write_text(json.dumps(result,indent=2))
 st.before_restore=[st.info(app.documents.item(i)) for i in range(app.documents.count)]
 (out/'before-runner-restore.private.json').write_text(json.dumps(st.before_restore,indent=2))
 print(json.dumps({'refusal_unchanged':'PASS','documents_preserved':len(st.protected),'fixture_version':1,'fixture_modified':st.document.isModified,'editable_count':app.data.personalUseLimits.editableFileCount}))
