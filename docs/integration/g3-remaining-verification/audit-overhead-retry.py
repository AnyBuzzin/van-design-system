import adsk.core,adsk.fusion,sys,pathlib,importlib.util,json,hashlib
def run(context):
 app=adsk.core.Application.get();state=sys.modules['_vandesign_g3_fixture_20261017']
 assert app.activeDocument==state.document and not state.document.isSaved
 source=pathlib.Path.home()/'Documents/VanDesign-G3/4d4345b/VanDesignCutAuditG3/VanDesignCutAuditG3.py'
 assert hashlib.sha256(source.read_bytes()).hexdigest()=='3f9426842a110768da0a0ca0ba6eecda27e4054fb7a20dd70867450efe59efb0'
 spec=importlib.util.spec_from_file_location('_g3_verified_audit',source);audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
 result=audit.run_audit(adsk.fusion.Design.cast(app.activeProduct),adsk.fusion.FeatureOperations.CutFeatureOperation)
 folder=pathlib.Path.home()/'Documents/VanDesign-Runner/issue4-live-20261017'
 (folder/'overhead-cut-audit-retry.json').write_text(json.dumps(result,indent=2))
 (folder/'overhead-cut-audit-retry.txt').write_text(audit.render_text(state.document.name,result))
 print(json.dumps(result))
