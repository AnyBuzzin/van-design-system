import adsk.core,json,pathlib,datetime,sys
def run(context):
 app=adsk.core.Application.get();folder=pathlib.Path.home()/'Documents/VanDesign-Runner/issue4-live-20261017/final-guarded-persistence'
 marker=folder/'single-attempt-started.txt'
 assert not marker.exists(), 'One attempt only; do not repeat'
 result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'outcome':'UNKNOWN','explicit_save_calls':0,'explicit_close_calls':0,'explicit_open_calls':0,'geometry_tests_run':False}
 def inventory():
  rows=[]
  for i in range(app.documents.count):
   d=app.documents.item(i);f=d.dataFile if d.isSaved else None
   rows.append({'name':d.name,'saved':d.isSaved,'modified':d.isModified,'active':d.isActive,'design_id':f.id if f else None,'version':f.versionNumber if f else None,'complete':f.isComplete if f else None})
  return rows
 def record():
  (folder/'lifecycle.private.json').write_text(json.dumps(result,indent=2))
 try:
  result['before']=inventory();record()
  assert len(result['before'])==1, 'REFUSED: another document is open'
  doc=app.documents.item(0);f=doc.dataFile if doc.isSaved else None
  assert doc.isActive and doc.isSaved and not doc.isModified and f and f.isComplete, 'REFUSED: fixture not clean/saved/complete/active'
  assert f.id=='OWNER_AUTHORIZED_FIXTURE_ID' and f.versionNumber==2 and f.name=='VanDesign-G3-overhead-remaining-20261017', 'REFUSED: identity/version mismatch'
  # Recheck immediately before the only authorized close, without processing events.
  assert app.documents.count==1 and app.documents.item(0)==doc and not doc.isModified and f.id=='OWNER_AUTHORIZED_FIXTURE_ID' and f.versionNumber==2 and f.isComplete
  marker.write_text(result['utc']);result['explicit_close_calls']=1;record()
  assert doc.close(False), 'Unexpected: dedicated clean close failed'
  result['after_close']=inventory();record()
  assert not result['after_close'], 'STOP: unexpected document present after close; no reopen attempted'
  result['explicit_open_calls']=1;record()
  reopened=app.documents.open(f,True)
  result['after_reopen']=inventory();record()
  assert reopened and reopened.isActive and len(result['after_reopen'])==1 and app.documents.item(0)==reopened, 'STOP: unexpected document inventory after reopen'
  assert reopened.isSaved and not reopened.isModified and reopened.dataFile.isComplete, 'STOP: reopened document is not clean/saved/complete'
  assert reopened.dataFile.id=='OWNER_AUTHORIZED_FIXTURE_ID' and reopened.dataFile.versionNumber==2, 'STOP: reopened identity/version changed'
  if '_vandesign_g3_fixture_20261017' in sys.modules:sys.modules['_vandesign_g3_fixture_20261017'].document=reopened
  result['outcome']='PASS'
 except Exception as e:
  result['outcome']='REFUSED' if not result['explicit_close_calls'] else 'FAIL'
  result['error']=str(e)
 finally:
  result['final_inventory']=inventory();record()
 print(json.dumps({'outcome':result['outcome'],'error':result.get('error'),'close_calls':result['explicit_close_calls'],'open_calls':result['explicit_open_calls'],'final_document_count':len(result['final_inventory'])}))
