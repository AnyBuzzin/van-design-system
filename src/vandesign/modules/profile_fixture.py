"""Trusted #84 fixture: fixed XY profiles, editable geometric thickness only.

No material/joint qualification at 20 mm. No serialized expressions or producer
schema: the handoff remains resolved PanelProfile with Python-owned bindings.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import math

from ..components.ids import make_id
from ..core.expr import Mm, Param
from ..core.geometry import Box
from ..core.params import ParamDef, ParameterSet
from ..manufacturing.profile import (Arc, Hole, Loop, PanelProfile, Pocket, ThroughCut,
                                     polygon_loop, rect_vertices, rounded_corner_outline)

FIXTURE = 'profile-panels/1'
PARAMETER = 'Profile_Thickness'
PARAMETERS = ParameterSet((ParamDef(PARAMETER, value_mm=18.0),))
THICKNESS = Param(PARAMETER)


@dataclass(frozen=True)
class ProfilePanel:
    profile: PanelProfile
    origin: tuple = (0.0, 0.0, 0.0)

    @property
    def box(self):
        lo, hi = self.profile.outline.bounds
        x, y, z = self.origin
        return Box((x+lo[0], y+lo[1], z), (x+hi[0], y+hi[1], z+self.profile.thickness))


def feature_loop(feature):
    if isinstance(feature, Hole):
        r = feature.diameter/2
        return Loop((Arc(feature.center, r, 0, math.pi), Arc(feature.center, r, math.pi, math.pi)))
    return feature.loop


def feature_depth(feature, thickness=THICKNESS):
    return thickness if isinstance(feature, ThroughCut) or feature.depth is None else Mm(feature.depth)


def feature_start(feature, thickness=THICKNESS):
    if isinstance(feature, (Pocket, Hole)) and feature.depth is not None and feature.face == 'top':
        return thickness-Mm(feature.depth)
    return Mm(0)


def feature_id(profile, index):
    return profile.panel_id+'.cut.%03d' % (index+1)


def validate_panels(panels):
    """Conservatively reject overlapping feature bounds/placed panels pre-CAD.

    Even disjoint contours whose bounding rectangles overlap are unsupported.
    This keeps additive profile volumes valid without a new boolean engine.
    """
    ids = [p.profile.panel_id for p in panels]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Unique nonempty profile IDs required')
    for panel in panels:
        p = panel.profile
        make_id(*p.panel_id.split('.'))
        if len(panel.origin) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) for v in panel.origin):
            raise ValueError('Finite profile placement required')
        # Reconstruct immutable core records to run their containment/depth checks.
        PanelProfile(p.panel_id, p.display_name, p.material_ref, p.thickness, p.outline, p.features)
        if p.volume_mm3 <= 0:
            raise ValueError('Positive finished volume required')
        bounds = [feature_loop(f).bounds for f in p.features]
        for i, (lo, hi) in enumerate(bounds):
            for low, high in bounds[:i]:
                if all(min(hi[k], high[k]) >= max(lo[k], low[k]) for k in (0, 1)):
                    raise ValueError('Overlapping/touching feature bounds unsupported')
    for i, p in enumerate(panels):
        for other in panels[:i]:
            if all(min(p.box.hi[k], other.box.hi[k]) > max(p.box.lo[k], other.box.lo[k]) for k in range(3)):
                raise ValueError('Overlapping profile panels')
    return panels


def resolve_profiles(values=None):
    env = PARAMETERS.resolve(values)
    t = env[PARAMETER]
    if not 6 < t <= 30:
        raise ValueError('Thickness must exceed blind depth 6 mm and be at most 30 mm')
    rounded = PanelProfile('profile.rounded.001', 'Rounded panel', 'geometry-only', t,
                           rounded_corner_outline(600, 800, 50))
    outline = polygon_loop(rect_vertices(0, 0, 200, 120), waste_inside=False)
    slot = polygon_loop(rect_vertices(70, 50, 130, 70), waste_inside=True, relief_radius=3)
    pocket = polygon_loop(rect_vertices(10, 10, 30, 30), waste_inside=True)
    relieved = PanelProfile('profile.relieved.001', 'Relieved slot panel', 'geometry-only', t,
                            outline, (ThroughCut(slot), Pocket(pocket, 6, 'top'),
                                      Hole((170, 100), 8, 4, 'bottom')), reliefs=4)
    return validate_panels((ProfilePanel(rounded), ProfilePanel(relieved, (800, 0, 0))))


def request_valid(request):
    if not isinstance(request, dict) or request != {'fixture': FIXTURE}:
        raise ValueError('Only the fixed profile-panels/1 fixture is supported')


def inventory(panels):
    cuts = sum(len(p.profile.features) for p in panels)
    return dict(user_parameters=len(PARAMETERS.params), root_occurrences=len(panels),
                all_components=len(panels)+1, timeline_items=3*len(panels)+2*cuts)


def spec_hash():
    data = dict(fixture=FIXTURE, panels=[asdict(p) for p in resolve_profiles()])
    return hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()
