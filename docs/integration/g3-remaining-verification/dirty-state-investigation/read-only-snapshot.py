import adsk.core,adsk.fusion,json,hashlib,datetime
def run(context):
 app=adsk.core.Application.get();doc=app.activeDocument
 assert doc and doc.isSaved and doc.dataFile.id=='OWNER_AUTHORIZED_FIXTURE_ID', 'Wrong active fixture; stop'
 errors=[]
 def read(obj,key):
  try:return getattr(obj,key)
  except Exception as e:errors.append({'property':key,'error':str(e)});return None
 def inventory():
  result=[]
  for i in range(app.documents.count):
   d=app.documents.item(i);f=d.dataFile if d.isSaved else None
   result.append({'name':d.name,'saved':d.isSaved,'modified':d.isModified,'active':d.isActive,'design_id':f.id if f else None,'version':f.versionNumber if f else None,'complete':f.isComplete if f else None})
  return result
 before=inventory();design=adsk.fusion.Design.cast(app.activeProduct);assert design
 params={}
 for i in range(design.userParameters.count):
  p=design.userParameters.item(i);params[p.name]={'expression':p.expression,'value_mm':p.value*10,'unit':p.unit}
 counts={'user_parameters':design.userParameters.count,'root_occurrences':design.rootComponent.occurrences.count,'all_components':design.allComponents.count,'timeline_items':design.timeline.count}
 bodies=[];occurrences=[]
 for i in range(design.rootComponent.occurrences.count):
  occ=design.rootComponent.occurrences.item(i);comp=occ.component;a=comp.attributes.itemByName('VanDesign','stable_id')
  occurrences.append({'name':occ.name,'stable_id':a.value if a else None,'body_count':comp.bRepBodies.count,'transform':occ.transform2.asArray()})
  for j in range(comp.bRepBodies.count):
   b=comp.bRepBodies.item(j);box=b.boundingBox
   bodies.append({'stable_id':a.value if a else None,'solid':b.isSolid,'volume_mm3':b.volume*1000,'min_mm':[v*10 for v in box.minPoint.asArray()],'max_mm':[v*10 for v in box.maxPoint.asArray()],'body_name':b.name,'faces':b.faces.count,'edges':b.edges.count,'vertices':b.vertices.count})
 timeline=[]
 for i in range(design.timeline.count):
  item=design.timeline.item(i);entity=read(item,'entity')
  timeline.append({'index':i,'name':item.name,'is_suppressed':read(item,'isSuppressed'),'entity_type':entity.objectType if entity else None,'health':str(read(entity,'healthState')) if entity else None,'health_message':read(entity,'errorOrWarningMessage') if entity else None})
 attr=design.rootComponent.attributes.itemByName('VanDesign','spec_json');raw=attr.value if attr else None
 all_body_count=sum(design.allComponents.item(i).bRepBodies.count for i in range(design.allComponents.count))
 print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'documents_before':before,'documents_after':inventory(),'parameters':params,'counts':counts,'bodies':sorted(bodies,key=lambda b:b['stable_id'] or ''),'occurrences':occurrences,'all_component_body_count':all_body_count,'root_body_count':design.rootComponent.bRepBodies.count,'timeline_marker':design.timeline.markerPosition,'timeline':timeline,'stored_spec_json':raw,'stored_spec_sha256':hashlib.sha256(raw.encode()).hexdigest() if raw else None,'errors':errors}))
