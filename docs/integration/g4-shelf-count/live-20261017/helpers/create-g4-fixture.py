import adsk.core,adsk.fusion,sys,json,pathlib,traceback
from vandesign.cad.fusion.shelf_regeneration import ShelfFixtureAdapter,verified_state
from vandesign.schemas.design_spec import load_design_spec
from vandesign.modules.variants import build_variant,profile_limits
from vandesign.verification.validate import validate
from vandesign.cad.fusion.runner import _write_report,_raw_sha256
from fusion_backend import FusionBackend
def run(context):
 app=adsk.core.Application.get();st=sys.modules['_vandesign_g4_qualification_20261017'];assert not hasattr(st,'document')
 assert [st.info(d) for d in st.protected]==st.before
 assert not app.isOffLine
 lim=app.data.personalUseLimits;assert lim.editableFileCount<lim.maxEditableFileCount
 assert not any(st.folder.dataFiles.item(i).name.casefold()==st.name.casefold() for i in range(st.folder.dataFiles.count))
 out=pathlib.Path(r'C:\Users\Buzz\Documents\VanDesign-Runner\issue20-live-20261017T212117Z')
 ds=load_design_spec(json.dumps({'schema_version':'0.2','module':'cabinet@1','variant':'base','profile_version':1,'parameters':{}}))
 assembly=build_variant(ds.resolved_params,ds.profile)
 st.document=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
 st.document.name=st.name
 result={'stage':'initial fixture build','outcome':'FAIL'}
 try:
  assert [st.info(d) for d in st.protected]==st.before
  assert app.activeDocument==st.document and not st.document.isSaved
  design=adsk.fusion.Design.cast(app.activeProduct);adapter=ShelfFixtureAdapter(design)
  adapter.compile(assembly);adapter.store_spec_json(ds.canonical_stored_spec_json)
  report=validate(assembly,adapter.geometry_source(),profile_limits=profile_limits(ds.profile),profile_variant=ds.variant)
  paths=_write_report(str(out/'baseline'),app,design,ds.resolved_params,assembly,report,'build',design_spec=ds,stored={'raw_sha256_before':_raw_sha256(adapter.stored_spec_json()),'raw_sha256_after':_raw_sha256(adapter.stored_spec_json()),'unchanged':True})
  inv=verified_state(adapter,assembly)
  cfg=json.loads((pathlib.Path(r'C:\Users\Buzz\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\VanDesignRunner')/'config.json').read_text())
  audit=FusionBackend(app,cfg).audit(str(out/'baseline'),'G4 initial baseline')
  result.update(validation=report.to_dict(),reports=paths,inventory=inv,audit=audit)
  assert report.to_dict()['verdict']=='PASS'
  assert audit['overall']=='PASS' and audit['features_passed']==audit['features_total']==2 and audit['timeline_restored'] and audit['counts_equal']
  assert [st.info(d) for d in st.protected]==st.before
  st.baseline=inv;st.original_spec=ds.canonical_stored_spec_json
  result['outcome']='PASS'
 except Exception as e:
  result.update(error=str(e),traceback=traceback.format_exc())
 result['existing_documents_unchanged']=all(d.isValid for d in st.protected) and [st.info(d) for d in st.protected]==st.before
 result['fixture_saved']=st.document.isSaved
 (out/'baseline-build.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps({'outcome':result['outcome'],'error':result.get('error'),'fixture_saved':result['fixture_saved'],'existing_documents_unchanged':result['existing_documents_unchanged']}))
