import json,csv,hashlib
from pathlib import Path
R=Path(r'C:\Users\Buzz\Documents\VanDesign-V5-demonstration-preflight')
summary={}
for v in ('base','tall','overhead'):
    proof=json.loads((R/v/'restored.private.json').read_text())
    preview=json.loads((R/v/'preview/panels.json').read_text())
    rows=list(csv.DictReader((R/v/'preview/panels.csv').open()))
    assert {r['panel_id'] for r in rows} == set(proof['bodies'])
    checks=[]
    for r in rows:
        size=proof['bodies'][r['panel_id']]['size_mm']
        for field,axis in [('blank_1_mm','blank_axis_1'),('blank_2_mm','blank_axis_2'),('nominal_thickness_mm','thickness_axis')]:
            observed=size['XYZ'.index(r[axis])]
            assert abs(float(r[field])-observed)<0.01,(v,r,observed)
        assert float(r['nominal_thickness_mm']) == (6 if r['role']=='back' else 18)
        assert r['quantity']=='1' and r['label']
        checks.append({'panel_id':r['panel_id'],'label':r['label'],'dimensions_match_measured_brep':'PASS','nominal_thickness_mm':float(r['nominal_thickness_mm']),'quantity':1})
    summary[v]={'status':'PASS','panel_count':len(rows),'tolerance_mm':0.01,'checks':checks,'preview_sha256':hashlib.sha256((R/v/'preview/panels.json').read_bytes()).hexdigest(),'measured_proof_sha256':hashlib.sha256((R/v/'restored.private.json').read_bytes()).hexdigest()}
(R/'cut-list-crosscheck.json').write_text(json.dumps(summary,indent=2)+'\n')
print({v:(s['status'],s['panel_count']) for v,s in summary.items()})
print('preview keys',preview['evidence'].keys())
