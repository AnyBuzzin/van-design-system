"""Standalone E1.1 contract, not an extension of cabinet/bed schemas."""
from dataclasses import asdict, dataclass
import hashlib
import json
from ..core.geometry import RoundedCornerOutline

SCHEMA = 'vandesign.rounded-panel/1'
NOTICE = 'UNQUALIFIED GEOMETRIC PANEL; no CNC, load or manufacturing qualification'


@dataclass(frozen=True)
class RoundedPanelSpec:
    width_mm: float = 600
    length_mm: float = 800
    radius_mm: float = 50
    thickness_mm: float = 18

    def __post_init__(self):
        RoundedCornerOutline(self.width_mm,self.length_mm,self.radius_mm)
        if type(self.thickness_mm) not in (int,float) or self.thickness_mm != 18:
            raise ValueError('E1.1 supports nominal 18 mm only')
        for k,v in asdict(self).items():object.__setattr__(self,k,float(v))

    def to_json(self):
        return json.dumps(dict(schema_version=SCHEMA,parameters=asdict(self)),
                          sort_keys=True,separators=(',',':'),allow_nan=False)

    def spec_hash(self):
        return hashlib.sha256(self.to_json().encode('utf-8')).hexdigest()


def load_rounded_panel_spec(text):
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise ValueError('Duplicate panel key: '+k)
            result[k]=v
        return result
    if not isinstance(text,(str,bytes)) or len(text)>65536:
        raise ValueError('Panel JSON required, at most 64 KiB')
    raw=json.loads(text,object_pairs_hook=unique)
    if (not isinstance(raw,dict) or set(raw)!={'schema_version','parameters'}
            or raw['schema_version']!=SCHEMA or not isinstance(raw['parameters'],dict)
            or set(raw['parameters'])!=set(RoundedPanelSpec.__dataclass_fields__)):
        raise ValueError('Complete known rounded-panel schema fields required')
    return RoundedPanelSpec(**raw['parameters'])
