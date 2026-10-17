import adsk.core,adsk.fusion,json,sys,types,pathlib
from vandesign.cad.fusion.runner import FusionAdapter,load_design_spec,build_variant,validate,profile_limits,_raw_sha256,_write_report
def run(context):
 app=adsk.core.Application.get()
 assert '_vandesign_g3_fixture_20261017' not in sys.modules, 'Fixture already exists; do not duplicate'
 ds=load_design_spec('{\n  "module": "cabinet@1",\n  "parameters": {\n    "back_mm": 6.0,\n    "cabinet_id": "cabinet.001",\n    "dado_depth_mm": 6.0,\n    "depth_mm": 350.0,\n    "door_count": 2,\n    "end_clearance_mm": 0.3,\n    "gap_mm": 3.0,\n    "height_mm": 400.0,\n    "material_ref": "ply_main",\n    "ply_mm": 18.0,\n    "shelf_count": 1,\n    "slot_clearance_mm": 0.5,\n    "width_mm": 1000.0\n  },\n  "profile_version": 1,\n  "schema_version": "0.2",\n  "variant": "overhead"\n}\n')
 assert ds.design_spec_hash=='6c15b5e34fdedbff55f796d416f4c3dc89a3109b58b71d264df668a4d322c2b2'
 assembly=build_variant(ds.resolved_params,ds.profile)
 state=types.ModuleType('_vandesign_g3_fixture_20261017')
 state.protected=[(app.documents.item(i),app.documents.item(i).name,app.documents.item(i).isSaved,app.documents.item(i).isModified) for i in range(app.documents.count)]
 sys.modules[state.__name__]=state
 state.document=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
 state.document.name='VanDesign-G3-overhead-remaining-20261017'
 assert app.activeDocument==state.document and not state.document.isSaved
 design=adsk.fusion.Design.cast(app.activeProduct);adapter=FusionAdapter(design)
 adapter.compile(assembly);adapter.store_spec_json(ds.canonical_stored_spec_json)
 report=validate(assembly,adapter.geometry_source(),profile_limits=profile_limits(ds.profile),profile_variant=ds.variant)
 folder=str(pathlib.Path.home()/'Documents/VanDesign-Runner/issue4-live-20261017')
 paths=_write_report(folder,app,design,ds.resolved_params,assembly,report,'build',design_spec=ds,stored={'raw_sha256_before':None,'raw_sha256_after':_raw_sha256(adapter.stored_spec_json()),'unchanged':None})
 protected_ok=all(doc.isValid and doc.name==name and doc.isSaved==saved and doc.isModified==modified for doc,name,saved,modified in state.protected)
 print(json.dumps({'reports':paths,'validation':report.to_dict(),'protected_documents_unchanged':protected_ok,'new_document':state.document.name,'saved':state.document.isSaved}))
