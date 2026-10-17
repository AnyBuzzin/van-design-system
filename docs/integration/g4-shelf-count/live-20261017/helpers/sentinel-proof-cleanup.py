import adsk.core,sys,json,pathlib
from fusion_backend import FusionBackend
from vdrunner.shelf_change import equivalent
def run(context):
 app=adsk.core.Application.get();st=sys.modules['_vandesign_g4_qualification_20261017'];out=pathlib.Path(r'C:\Users\Buzz\Documents\VanDesign-Runner\issue20-live-20261017T212117Z')
 assert app.activeDocument==st.document and [st.info(d) for d in st.protected]==st.before
 result=json.loads((pathlib.Path.home()/'Documents/VanDesign-Runner/queue/results/g4-live-20261017-sentinel/result.json').read_text())
 assert result['outcome']=='FAIL' and 'unexpected timeline entities' in result['steps'][0]['error']
 after=st.fingerprint();assert equivalent(st.sentinel_before,after)
 assert st.sentinel.isValid and st.sentinel.component.name=='G4 refusal sentinel (test-created only)' and st.sentinel.component.bRepBodies.count==0
 (out/'sentinel-refusal-proof.json').write_text(json.dumps({'expected_refusal':True,'model_unchanged':True,'before':st.sentinel_before,'after':after},indent=2))
 assert st.sentinel.deleteMe();assert not st.sentinel.isValid
 cfg=json.loads((pathlib.Path(r'C:\Users\Buzz\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\VanDesignRunner')/'config.json').read_text())
 assert equivalent(FusionBackend(app,cfg).shelf_state()['inventory'],st.baseline)
 print(json.dumps({'expected_refusal':True,'model_unchanged':True,'only_captured_sentinel_removed':True,'baseline_restored':True}))
