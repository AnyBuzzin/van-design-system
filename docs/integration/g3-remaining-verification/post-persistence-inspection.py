import adsk.core,sys,json
def run(context):
 app=adsk.core.Application.get();state=sys.modules['_vandesign_g3_fixture_20261017'];protected=[]
 for d,n,s,m in state.protected:
  rec={'before':{'name':n,'saved':s,'modified':m},'valid':d.isValid}
  if d.isValid:rec['after']={'name':d.name,'saved':d.isSaved,'modified':d.isModified}
  protected.append(rec)
 print(json.dumps({'protected':protected,'open_documents':[{'name':app.documents.item(i).name,'saved':app.documents.item(i).isSaved,'modified':app.documents.item(i).isModified} for i in range(app.documents.count)]}))
