import json
from pathlib import Path
from vandesign.panel_preview import make_preview
raw=next(Path('docs/integration/g4-shelf-count/live-20261017/jobs/g4-live-20261017-to-two/evidence/00_update_shelf_count/post/reports').glob('*.json')).read_bytes()
original=json.loads(raw);out={}
for label,value in [('missing',None),('contradictory',123)]:
 d=json.loads(raw); c=next(c for c in d['validation']['checks'] if c['check_id']=='panel.left.001.volume');c['observed']=value
 out[label]={'record':c,'result':make_preview(d['design_spec_canonical_json'],json.dumps(d).encode())['evidence']}
print(json.dumps(out,indent=2))
