import adsk.core,sys,json,pathlib,hashlib
from fusion_backend import FusionBackend
def run(context):
 app=adsk.core.Application.get();st=sys.modules['_vandesign_g4_qualification_20261017'];out=pathlib.Path(r'C:\Users\Buzz\Documents\VanDesign-Runner\issue20-live-20261017T212117Z')
 root=pathlib.Path(r'C:\Users\Buzz\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\VanDesignRunner');expected=json.loads((out/'backup/installation-manifest.json').read_text())
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 assert {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}==expected
 cfg=json.loads((root/'config.json').read_text());assert sha(root/'config.json')=='70bf4288f224cef35efc1760aae594c54cf39d1676a298aa10956621d81d8378'
 assert not hasattr(FusionBackend,'begin_shelf_regeneration') and 'vdrunner.shelf_change' not in sys.modules
 g=FusionBackend(app,cfg)._g3();base=pathlib.Path(cfg['g3_script_dir']);manifest=json.loads((base/'DEPLOYMENT.json').read_text())['files'];modules=[]
 for n,m in list(sys.modules.items()):
  p=getattr(m,'__file__',None)
  if not p:continue
  p=pathlib.Path(p)
  if n=='vandesign' or n.startswith('vandesign.'):
   assert sha(p)==manifest[p.relative_to(base).as_posix()];modules.append({'name':n,'path':str(p),'sha256':sha(p)})
  elif n=='fusion_backend' or n=='vdrunner' or n.startswith('vdrunner.'):
   assert sha(p)==expected[p.relative_to(root).as_posix()]
 assert [st.info(d) for d in st.protected]==st.before
 assert app.documents.count==len(st.protected)+1 and app.activeDocument==st.document
 assert st.document.dataFile.id==st.design_id and st.document.dataFile.versionNumber==1 and st.document.isModified
 assert app.scripts.itemsByName('VanDesignRunner')[0].isRunning
 result={'original_runner_active':True,'exact_installation_restored':True,'config_sha256':sha(root/'config.json'),'original_cabinet_modules':modules,'protected_before':st.before,'protected_after':[st.info(d) for d in st.protected],'existing_documents_unchanged':True,'fixture':st.info(st.document),'fixture_left_open_unsaved_after_first_save':True}
 (out/'final-state.private.json').write_text(json.dumps(result,indent=2))
 print(json.dumps({'original_runner_active':True,'exact_installation_restored':True,'original_modules_verified':len(modules),'existing_documents_unchanged':True,'fixture_version':1,'fixture_left_open_with_unsaved_test_changes':True}))
