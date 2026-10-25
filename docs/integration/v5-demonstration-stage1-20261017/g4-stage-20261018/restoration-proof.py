import adsk.core,adsk.fusion,sys,json,pathlib,itertools
from fusion_backend import FusionBackend
from vdrunner.shelf_change import equivalent
def run(context):
 app=adsk.core.Application.get();st=sys.modules['_vandesign_v5_demo_g4'];out=pathlib.Path(r'C:\Users\Buzz\Documents\VanDesign-V5-demonstration-g4-20261018')
 assert app.activeDocument==st.document and st.document.dataFile.id==st.design_id and st.document.dataFile.versionNumber==1
 assert [st.info(d) for d in st.protected]==st.before and app.documents.count==len(st.protected)+1
 cfg=json.loads((pathlib.Path(r'C:\Users\Buzz\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns\VanDesignRunner')/'config.json').read_text());b=FusionBackend(app,cfg)
 current=b.shelf_state();assert current['stored_text']==st.original_spec
 equal=equivalent(st.baseline,current['inventory']);assert equal,'Restored measured inventory differs'
 g=b.g3_modules();raw=json.loads(st.original_spec);raw['parameters']['shelf_count']=2
 ds=g['design_spec'].load_design_spec(json.dumps(raw));asm=g['variants'].build_variant(ds.resolved_params,ds.profile);env=asm.parameters.resolve()
 src=g['adapter'].FusionAdapter(adsk.fusion.Design.cast(app.activeProduct)).geometry_source();probes=[]
 for op in asm.operations:
  box=op.cut.resolve(env)
  for ratios in itertools.product((.25,.5,.75),repeat=3):
   pt=tuple(box.lo[i]+ratios[i]*(box.hi[i]-box.lo[i]) for i in range(3))
   material=src.point_in_material(op.target_panel_id,pt)
   probes.append({'obsolete_cut':op.operation_id,'target':op.target_panel_id,'point_mm':pt,'material':material})
 result={'baseline_inventory_equal':equal,'obsolete_groove_probes':probes,'all_material_restored':all(p['material'] is True for p in probes),'existing_documents_unchanged':True,'fixture_version':1,'fixture_modified':st.document.isModified}
 (out/'restoration-extra-proof.json').write_text(json.dumps(result,indent=2))
 assert result['all_material_restored'],'Obsolete groove material not restored'
 st.noop_before=current
 print(json.dumps({'baseline_inventory_equal':equal,'obsolete_groove_material_probes_passed':len(probes),'existing_documents_unchanged':True}))

