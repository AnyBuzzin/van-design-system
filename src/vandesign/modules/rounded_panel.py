"""One fixed parametric shape family. Enclosing blank is NOT its contour."""
from ..cad.protocol import preflight
from ..components.model import AssemblyDefinition, Constraint, Panel
from ..core.expr import Mm, Param
from ..core.geometry import BoxExpr, RoundedCornerOutline
from ..core.params import ParamDef, ParameterSet
from ..schemas.rounded_panel_spec import RoundedPanelSpec, NOTICE

PANEL_ID = 'panel.rounded.001'


def build_rounded_panel(spec):
    if type(spec) is not RoundedPanelSpec:raise ValueError('RoundedPanelSpec required')
    params=ParameterSet(tuple(ParamDef(k,value_mm=v,comment=NOTICE) for k,v in (
        ('Panel_Width',spec.width_mm),('Panel_Length',spec.length_mm),('Panel_Radius',spec.radius_mm))))
    w,l,r=map(Param,params.names());z=Mm(0)
    panel=Panel(PANEL_ID,'E1.1 rounded panel','rounded_panel','ply_18_nominal',
                BoxExpr((z,z,z),(w,l,Mm(18))),corner_radius=r)
    constraints=(Constraint('radius.positive','Positive radius',r,'>',z),
                 Constraint('radius.width','Radius below width',w,'>',r),
                 Constraint('radius.length','Radius below length',l,'>',r))
    assembly=AssemblyDefinition('rounded.panel.001',spec.spec_hash(),params,(panel,),(),constraints)
    preflight(assembly)
    return assembly


def preview_rounded_panel(values):
    if not isinstance(values,dict) or set(values)!={'Panel_Width','Panel_Length','Panel_Radius'}:
        raise ValueError('Complete known rounded panel parameters required')
    spec=RoundedPanelSpec(values['Panel_Width'],values['Panel_Length'],values['Panel_Radius'])
    outline=RoundedCornerOutline(spec.width_mm,spec.length_mm,spec.radius_mm)
    return dict(panel_id=PANEL_ID,spec_hash=spec.spec_hash(),notice=NOTICE,
                enclosing_blank_mm=[spec.width_mm,spec.length_mm,18],
                contour=dict(lines=outline.lines,arc=outline.arc),
                finished_area_mm2=outline.area_mm2,finished_volume_mm3=outline.area_mm2*18)
