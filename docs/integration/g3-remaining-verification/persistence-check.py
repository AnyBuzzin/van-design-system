import adsk.core,adsk.fusion,sys,json,pathlib,math
from vandesign.cad.fusion.runner import FusionAdapter,load_design_spec,build_variant,validate,profile_limits,_raw_sha256,_write_report,_fusion_parameters_mm,_design_counts
def run(context):
 app=adsk.core.Application.get();state=sys.modules['_vandesign_g3_fixture_20261017'];doc=state.document
 folder=pathlib.Path.home()/'Documents/VanDesign-Runner/issue4-live-20261017'
 assert not getattr(state,'reopen_attempted',False)
 assert app.activeDocument==doc and doc.isSaved and not doc.isModified and doc.dataFile.id==state.design_id and doc.dataFile.isComplete
 def snapshot():
  design=adsk.fusion.Design.cast(app.activeProduct);adapter=FusionAdapter(design);raw=adapter.stored_spec_json();ds=load_design_spec(raw);assembly=build_variant(ds.resolved_params,ds.profile)
  report=validate(assembly,adapter.geometry_source(),profile_limits=profile_limits(ds.profile),profile_variant=ds.variant)
  assert report.to_dict()['verdict']=='PASS'
  paths=_write_report(str(folder),app,design,ds.resolved_params,assembly,report,'measure',design_spec=ds,stored={'raw_sha256_before':_raw_sha256(raw),'raw_sha256_after':_raw_sha256(adapter.stored_spec_json()),'unchanged':raw==adapter.stored_spec_json()})
  bodies=[]
  for i in range(design.rootComponent.occurrences.count):
   comp=design.rootComponent.occurrences.item(i).component;attr=comp.attributes.itemByName('VanDesign','stable_id')
   assert attr and comp.bRepBodies.count==1
   b=comp.bRepBodies.item(0);box=b.boundingBox
   bodies.append({'stable_id':attr.value,'solid':b.isSolid,'volume_mm3':b.volume*1000,'min_mm':[v*10 for v in box.minPoint.asArray()],'max_mm':[v*10 for v in box.maxPoint.asArray()]})
  return {'spec_json':raw,'spec_hash':ds.design_spec_hash,'params':_fusion_parameters_mm(design),'counts':_design_counts(design),'bodies':sorted(bodies,key=lambda b:b['stable_id']),'validation':report.to_dict(),'reports':[pathlib.Path(p).name for p in paths]}
 before=snapshot();df=doc.dataFile;identity={'design_id':df.id,'version':df.versionNumber,'name':df.name}
 assert not doc.isModified and df.isComplete
 (folder/'persistence-before.private.json').write_text(json.dumps({'identity':identity,'snapshot':before},indent=2))
 state.reopen_attempted=True
 assert doc.close(False), 'Clean dedicated close failed'
 reopened=app.documents.open(df,True);assert reopened and reopened.isActive
 state.document=reopened
 assert reopened.dataFile.id==identity['design_id'] and reopened.dataFile.versionNumber==identity['version'] and not reopened.isModified
 after=snapshot()
 def equivalent(a,b):
  if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(equivalent(a[k],b[k]) for k in a if k!='reports')
  if isinstance(a,list):return isinstance(b,list) and len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
  if isinstance(a,(int,float)) and not isinstance(a,bool):return isinstance(b,(int,float)) and abs(a-b)<=1e-6
  return a==b
 protected=all(d.isValid and d.name==n and d.isSaved==s and d.isModified==m for d,n,s,m in state.protected)
 result={'identity_before':identity,'identity_after':{'design_id':reopened.dataFile.id,'version':reopened.dataFile.versionNumber,'name':reopened.dataFile.name},'before':before,'after':after,'equivalent_with_absolute_tolerance_1e_6':equivalent(before,after),'protected_documents_unchanged':protected,'reopened_clean':not reopened.isModified,'outcome':'PASS' if equivalent(before,after) and protected and not reopened.isModified else 'FAIL'}
 (folder/'persistence.private.json').write_text(json.dumps(result,indent=2))
 print(json.dumps({'outcome':result['outcome'],'bodies':len(before['bodies']),'version_before':identity['version'],'version_after':reopened.dataFile.versionNumber,'protected_documents_unchanged':protected,'clean':not reopened.isModified}))
