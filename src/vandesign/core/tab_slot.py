"""Fixed E1.2 T coupon, in millimetres; not a general joint/profile engine."""
from dataclasses import dataclass
from itertools import combinations
import math

from .geometry import Box

RECEIVER = 'coupon.receiver.001'
UPRIGHT = 'coupon.upright.001'


@dataclass(frozen=True)
class TabSlotGeometry:
    tab_width: float
    engagement: float
    clearance: float
    tool_diameter: float

    def __post_init__(self):
        values = (self.tab_width, self.engagement, self.clearance, self.tool_diameter)
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError('Finite numeric coupon dimensions required')
        if not (0 < self.tab_width < 120 and 0 < self.engagement <= 18
                and 0 <= self.clearance <= 100 and 0 < self.tool_diameter <= 100):
            raise ValueError('Invalid tab width, engagement, clearance or tool diameter')
        slot, r = self.slot, self.radius
        if self.tab_width+self.clearance >= 120:
            raise ValueError('Clearance removes the supporting shoulders')
        for x, y in self.centres:
            if not (slot.lo[0] < x < slot.hi[0] and slot.lo[1] < y < slot.hi[1]):
                raise ValueError('Relief centre must be inside the slot')
            if not (0 < x-r and x+r < 200 and 0 < y-r and y+r < 120):
                raise ValueError('Relief must preserve positive receiver edge margins')
        if not (0 < slot.lo[0] < slot.hi[0] < 200 and 0 < slot.lo[1] < slot.hi[1] < 120):
            raise ValueError('Slot outside receiver edge margins')
        if any(math.dist(a, b) <= 2*r for a, b in combinations(self.centres, 2)):
            raise ValueError('Relief circles overlap or touch')

    @property
    def radius(self):
        return self.tool_diameter / 2

    @property
    def slot(self):
        w, h = self.tab_width+self.clearance, 18+self.clearance
        return Box((100-w/2, 60-h/2, 0), (100+w/2, 60+h/2, 18))

    @property
    def centres(self):
        s, a = self.slot, self.radius/math.sqrt(2)
        return ((s.lo[0]+a,s.lo[1]+a), (s.hi[0]-a,s.lo[1]+a),
                (s.hi[0]-a,s.hi[1]-a), (s.lo[0]+a,s.hi[1]-a))

    @property
    def tab(self):
        return Box((100-self.tab_width/2,51,18-self.engagement), (100+self.tab_width/2,69,18))

    @property
    def shoulders(self):
        t = self.tab
        return (Box((40,51,t.lo[2]), (t.lo[0],69,18)),
                Box((t.hi[0],51,t.lo[2]), (160,69,18)))

    @property
    def contact_x(self):
        return ((40+self.slot.lo[0])/2, (160+self.slot.hi[0])/2)

    @property
    def bounds(self):
        return {RECEIVER: Box((0,0,0),(200,120,18)),
                UPRIGHT: Box((40,51,18-self.engagement),(160,69,118))}

    @property
    def relief_extra_area(self):
        # Each circle adds two segments outside the rectangle; no double count.
        return self.radius**2 * (math.pi/2-1)

    @property
    def volumes(self):
        return {RECEIVER: 200*120*18-self.slot.volume-4*self.relief_extra_area*18,
                UPRIGHT: (120*100+self.tab_width*self.engagement)*18}

    @property
    def cut_volumes(self):
        return tuple(s.volume for s in self.shoulders) + (self.slot.volume,) + (self.relief_extra_area*18,)*4

    def contains(self, panel_id, point):
        """Pure ideal geometry for offline checks, never actual Fusion evidence."""
        if panel_id == UPRIGHT:
            x,y,z=point
            return (self.bounds[UPRIGHT].contains_point(point,eps=0)
                    and (z>18 or self.tab.lo[0]<x<self.tab.hi[0]))
        if panel_id != RECEIVER:
            raise ValueError('Unknown coupon panel')
        x,y,z = point
        return (self.bounds[RECEIVER].contains_point(point,eps=0)
                and not self.slot.contains_point(point,eps=0)
                and not any((x-cx)**2+(y-cy)**2 < self.radius**2 for cx,cy in self.centres))
