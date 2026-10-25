import adsk.core,sys,json,pathlib,hashlib,importlib
from fusion_backend import FusionBackend
def run(context):
 app=adsk.core.Application.get();st=sys.modules['_vandesign_g4_qualification_20261017'];assert [st.info(d) for d in st.protected]==st.before
 root=pathlib.Path(r'C:\Users\Buzz\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\VanDesignRunner')
 cfg=json.loads((root/'config.json').read_text());b=FusionBackend(app,cfg);g3=b._g3();importlib.import_module('vandesign.cad.fusion.shelf_regeneration')
 base=pathlib.Path(cfg['g3_script_dir']);manifest=json.loads((base/'DEPLOYMENT.json').read_text())['files']
 paths=[]
 for n,m in list(sys.modules.items()):
  if n=='vandesign' or n.startswith('vandesign.'):
   p=pathlib.Path(m.__file__);rel=p.relative_to(base).as_posix();h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==manifest[rel];paths.append({'module':n,'path':str(p),'sha256':h})
 patches=json.loads((pathlib.Path(r'C:\Users\Buzz\Documents\VanDesign-Runner\issue20-live-20261017T212117Z')/'temporary-deployment.private.json').read_text())['changed_files']
 for name in ('fusion_backend','vdrunner.executor','vdrunner.journal','vdrunner.schema','vdrunner.shelf_change'):
  p=pathlib.Path(sys.modules[name].__file__);rel=p.relative_to(root).as_posix();assert hashlib.sha256(p.read_bytes()).hexdigest()==patches[rel]
 assert app.scripts.itemsByName('VanDesignRunner')[0].isRunning
 print(json.dumps({'candidate_loaded':True,'runner_files_verified':5,'cabinet_modules':paths,'existing_documents_unchanged':True}))
