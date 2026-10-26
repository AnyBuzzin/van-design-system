"""One fixed coupon: blank scaffold plus seven owned cuts, not dado semantics."""
from dataclasses import dataclass
import math

from ..cad.protocol import preflight
from ..components.model import AssemblyDefinition, Panel
from ..core.expr import Mm, Param
from ..core.geometry import BoxExpr
from ..core.params import ParameterSet, ParamDef
from ..core.tab_slot import TabSlotGeometry, RECEIVER, UPRIGHT
from ..schemas.tab_slot_spec import TabSlotSpec, NOTICE

NAMES = ('Joint_Tab_Width','Joint_Engagement','Joint_Clearance','Joint_Tool_Diameter')
CUT_IDS = ('coupon.shoulder.left','coupon.shoulder.right','coupon.slot',
           'coupon.relief.1','coupon.relief.2','coupon.relief.3','coupon.relief.4')
OWNERS = (UPRIGHT,UPRIGHT,RECEIVER,RECEIVER,RECEIVER,RECEIVER,RECEIVER)


@dataclass(frozen=True)
class TabSlotCoupon:
    spec: TabSlotSpec
    blanks: AssemblyDefinition  # Explicitly NOT the finished joint or its net volumes.
    shoulders: tuple
    slot: BoxExpr
    centres: tuple
    radius: object

    def geometry(self, values=None):
        return geometry_from_parameters(self.blanks.parameters.resolve() if values is None else values)


def geometry_from_parameters(values):
    if not isinstance(values,dict) or set(values)!=set(NAMES):
        raise ValueError('Complete known coupon parameter snapshot required')
    return TabSlotGeometry(*(values[n] for n in NAMES))


def build_tab_slot(spec):
    if type(spec) is not TabSlotSpec:
        raise ValueError('TabSlotSpec required')
    parameters=ParameterSet(tuple(ParamDef(n,value_mm=v,comment=NOTICE) for n,v in zip(NAMES,
        (spec.tab_width_mm,spec.engagement_mm,spec.clearance_mm,spec.tool_diameter_mm))))
    t,e,c,d=map(Param,NAMES); zero=Mm(0); r=d/2; a=r/math.sqrt(2)
    x=Mm(100)-t/2; sx=Mm(100)-(t+c)/2; sy=Mm(60)-(Mm(18)+c)/2
    slot=BoxExpr((sx,sy,zero),(t+c,Mm(18)+c,Mm(18)))
    shoulders=(BoxExpr((Mm(40),Mm(51),Mm(18)-e),(x-Mm(40),Mm(18),e)),
               BoxExpr((Mm(100)+t/2,Mm(51),Mm(18)-e),(Mm(60)-t/2,Mm(18),e)))
    centres=((sx+a,sy+a),(sx+t+c-a,sy+a),(sx+t+c-a,sy+Mm(18)+c-a),(sx+a,sy+Mm(18)+c-a))
    panels=(Panel(RECEIVER,'Coupon receiver','coupon_receiver','ply_18_nominal',
                  BoxExpr((zero,zero,zero),(Mm(200),Mm(120),Mm(18)))),
            Panel(UPRIGHT,'Coupon upright','coupon_upright','ply_18_nominal',
                  BoxExpr((Mm(40),Mm(51),Mm(18)-e),(Mm(120),Mm(18),Mm(100)+e))))
    blanks=AssemblyDefinition('coupon.blank.scaffold.001',spec.spec_hash(),parameters,panels,())
    preflight(blanks)
    coupon=TabSlotCoupon(spec,blanks,shoulders,slot,centres,r)
    coupon.geometry()  # Full joint preflight before any CAD writes.
    return coupon


def preview_tab_slot(values):
    g=geometry_from_parameters(values)
    spec=TabSlotSpec(*(values[n] for n in NAMES))
    return dict(spec_hash=spec.spec_hash(),notice=NOTICE,panel_ids=[RECEIVER,UPRIGHT],
                enclosing_blanks_mm={RECEIVER:[200,120,18],UPRIGHT:[120,18,100+g.engagement]},
                finished_volume_mm3=g.volumes,slot_bounds_mm=[g.slot.lo,g.slot.hi],
                relief_centres_mm=g.centres,tool_radius_mm=g.radius,
                clearance_per_face_mm=g.clearance/2,engagement_mm=g.engagement,
                cut_ids=list(CUT_IDS),cut_owners=list(OWNERS),removed_volumes_mm3=g.cut_volumes)
