"""Separate versioned E1.2 geometric coupon contract; nominal stock only."""
from dataclasses import asdict, dataclass
import hashlib
import json

from ..core.tab_slot import TabSlotGeometry

SCHEMA = 'vandesign.tab-slot-coupon/1'
NOTICE = 'UNQUALIFIED GEOMETRIC COUPON; nominal stock/tool/fit, not CNC or load qualification'


@dataclass(frozen=True)
class TabSlotSpec:
    tab_width_mm: float = 60
    engagement_mm: float = 18
    clearance_mm: float = 0.5
    tool_diameter_mm: float = 6
    thickness_mm: float = 18

    def __post_init__(self):
        TabSlotGeometry(self.tab_width_mm,self.engagement_mm,self.clearance_mm,self.tool_diameter_mm)
        if type(self.thickness_mm) not in (int,float) or self.thickness_mm != 18:
            raise ValueError('E1.2 requires nominal 18 mm stock')
        for name,value in asdict(self).items():
            object.__setattr__(self,name,float(value))

    def to_json(self):
        return json.dumps(dict(schema_version=SCHEMA,parameters=asdict(self)),
                          sort_keys=True,separators=(',',':'),allow_nan=False)

    def spec_hash(self):
        return hashlib.sha256(self.to_json().encode()).hexdigest()


def load_tab_slot_spec(text):
    def unique(pairs):
        result={}
        for k,v in pairs:
            if k in result:raise ValueError('Duplicate coupon key: '+k)
            result[k]=v
        return result
    if not isinstance(text,(str,bytes)) or len(text)>65536:
        raise ValueError('Coupon JSON required, at most 64 KiB')
    raw=json.loads(text,object_pairs_hook=unique)
    if (not isinstance(raw,dict) or set(raw)!={'schema_version','parameters'} or raw['schema_version']!=SCHEMA
            or not isinstance(raw['parameters'],dict) or set(raw['parameters'])!=set(TabSlotSpec.__dataclass_fields__)):
        raise ValueError('Complete known coupon schema required')
    return TabSlotSpec(**raw['parameters'])
