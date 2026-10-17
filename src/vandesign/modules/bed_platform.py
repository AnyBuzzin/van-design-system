"""Three-panel unqualified geometric bed, X across / Y along / Z up (mm)."""
from ..cad.protocol import preflight
from ..components.model import AssemblyDefinition, Panel, Constraint
from ..core.expr import Mm, Param
from ..core.geometry import BoxExpr
from ..core.params import ParameterSet, ParamDef
from ..schemas.bed_platform_spec import BedPlatformSpec, NOTICE


def build_bed_platform(spec: BedPlatformSpec) -> AssemblyDefinition:
    if not isinstance(spec, BedPlatformSpec):
        raise TypeError("BedPlatformSpec required")
    params = ParameterSet(tuple(ParamDef(name, value_mm=value, comment=NOTICE) for name, value in (
        ("Bed_Width", spec.width_mm), ("Bed_Length", spec.length_mm),
        ("Bed_Height", spec.height_mm), ("Bed_Ply", spec.ply_mm))) + (
        ParamDef("Bed_Support_Height", expr=Param("Bed_Height") - Param("Bed_Ply")),))
    w, l, h, t, sh = map(Param, ("Bed_Width", "Bed_Length", "Bed_Height",
                                "Bed_Ply", "Bed_Support_Height"))
    zero = Mm(0)
    panels = (
        Panel("bed.deck.001", "Bed deck", "bed_deck", "ply_18_nominal",
              BoxExpr((zero, zero, sh), (w, l, t))),
        Panel("bed.front.001", "Front support", "bed_support", "ply_18_nominal",
              BoxExpr((zero, zero, zero), (w, t, sh))),
        Panel("bed.rear.001", "Rear support", "bed_support", "ply_18_nominal",
              BoxExpr((zero, l-t, zero), (w, t, sh))),
    )
    constraints = (
        Constraint("bed.width", "Width exceeds plywood thickness", w, ">", t),
        Constraint("bed.length", "Separate front/rear supports", l, ">", 2*t),
        Constraint("bed.height", "Positive support height below deck", h, ">", t),
        Constraint("bed.ply_min", "V6.1 nominal plywood is 18 mm", t, ">=", Mm(18)),
        Constraint("bed.ply_max", "V6.1 nominal plywood is 18 mm", Mm(18), ">=", t),
    )
    assembly = AssemblyDefinition("bed.platform.001", spec.spec_hash(), params, panels, (), constraints)
    preflight(assembly)
    return assembly
