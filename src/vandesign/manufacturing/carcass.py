"""Tab-and-slot cabinet carcass: joinery spec and module-local profiles.

Bottom and top tab flush through both sides (engagement = measured side
thickness); shelves keep their dados; doors and back are unchanged. Profiles
are computed in the cabinet's own frame: a part's cut shape does not change
when the cabinet is moved or rotated, only its frame does.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math

from ..core.expr import Expr
from ..modules.profile_fixture import feature_id
from .assembly import _assembly_profiles, _resolve, Tracked, expr_of, recording_decisions, tracked_box
from .joints import Sheet, TabSlot, apply_joints
from .profile import Arc, Line, Loop, Pocket, ProfileError, ThroughCut

_JOINERY_KEYS = {"sheet", "clearance_mm", "tabs_per_edge", "tab_width_mm", "tool_diameter_mm"}
_SHEET_KEYS = {"name", "nominal_mm", "measured_mm"}
SIDES = (("panel.left.001", "-x"), ("panel.right.001", "+x"))
TABBED = ("panel.bottom.001", "panel.top.001")


@dataclass(frozen=True)
class TabSlotJoinery:
    sheet: Sheet
    tool_diameter_mm: float
    clearance_mm: float = 0.2
    tabs_per_edge: int = 2
    tab_width_mm: float | None = None
    # ADR-0003: slots stop this deep inside the sides (None = through slots).
    blind_slot_depth_mm: float | None = None

    def __post_init__(self):
        b = self.blind_slot_depth_mm
        if b is not None and (type(b) not in (int, float) or not math.isfinite(b)
                              or b <= self.clearance_mm / 2):
            raise ProfileError("blind_slot_depth_mm must be a number greater than clearance_mm / 2")
        if type(self.sheet) is not Sheet:
            raise ProfileError("Joinery needs a Sheet")
        for name in ("tool_diameter_mm", "clearance_mm"):
            v = getattr(self, name)
            if type(v) not in (int, float) or not math.isfinite(v):
                raise ProfileError("%s must be a finite number" % name)
        if not 0 < self.tool_diameter_mm <= 25:
            raise ProfileError("tool_diameter_mm must be in (0, 25]")
        if not 0 <= self.clearance_mm <= 2:
            raise ProfileError("clearance_mm must be in [0, 2]")
        if type(self.tabs_per_edge) is not int or not 1 <= self.tabs_per_edge <= 6:
            raise ProfileError("tabs_per_edge must be 1-6")
        w = self.tab_width_mm
        if w is not None and (type(w) not in (int, float) or not math.isfinite(w) or w <= 0):
            raise ProfileError("tab_width_mm must be positive")

    @classmethod
    def from_json(cls, data):
        """Strict: exact keys (tab_width_mm may be null), plus optional
        blind_slot_depth_mm."""
        if not isinstance(data, dict) or not _JOINERY_KEYS <= set(data) <= _JOINERY_KEYS | {"blind_slot_depth_mm"}:
            raise ProfileError("joinery needs exactly: " + ", ".join(sorted(_JOINERY_KEYS))
                               + " (and optionally blind_slot_depth_mm)")
        sheet = data["sheet"]
        if not isinstance(sheet, dict) or set(sheet) != _SHEET_KEYS:
            raise ProfileError("sheet needs exactly: " + ", ".join(sorted(_SHEET_KEYS)))
        return cls(Sheet(sheet["name"], sheet["nominal_mm"], sheet["measured_mm"]), data["tool_diameter_mm"],
                   data["clearance_mm"], data["tabs_per_edge"], data["tab_width_mm"],
                   data.get("blind_slot_depth_mm"))


def cabinet_joints(boxes, joinery):
    """Four TabSlot joints for a cabinet's resolved panel boxes (module frame)."""
    depth = boxes["panel.bottom.001"].size[1]
    n = joinery.tabs_per_edge
    width = joinery.tab_width_mm if joinery.tab_width_mm is not None else min(120.0, depth / (2 * n))
    width = width if isinstance(width, Tracked) else float(width)   # keep depth provenance
    tabs = tuple(((k + 0.5) * depth / n - width / 2, width) for k in range(n))
    blind = joinery.blind_slot_depth_mm
    # Through: tabs flush with the outer face. Blind: tab tips stop clearance / 2 short of the slot floor.
    e = joinery.sheet.measured_mm if blind is None else blind - joinery.clearance_mm / 2
    return [TabSlot(panel, side, direction, tabs, e, joinery.clearance_mm, blind is not None)
            for panel in TABBED for side, direction in SIDES]


def cabinet_tab_slot_profiles(assembly, joinery, values=None):
    """Module-frame profiles of a cabinet assembly with tab-and-slot carcass joints.

    The cabinet's Cab_Ply must equal the sheet's measured thickness.
    Returns (profiles, joint results).
    """
    return _profiles(assembly, joinery, values, _resolve, None)


def _profiles(assembly, joinery, values, resolve, captures):
    env = assembly.parameters.resolve(values)
    if abs(env["Cab_Ply"] - joinery.sheet.measured_mm) > 1e-9:
        raise ProfileError("Cab_Ply %.3f mm must equal the measured sheet thickness %.3f mm"
                           % (env["Cab_Ply"], joinery.sheet.measured_mm))
    failed = [c.constraint_id for c, ok, _, _ in assembly.check_constraints(env) if not ok]
    if failed:
        raise ProfileError("Cabinet constraints fail: " + ", ".join(failed))
    boxes = {p.stable_id: resolve(p.box, env) for p in assembly.panels}
    overrides, cuts, results = apply_joints(cabinet_joints(boxes, joinery), boxes)
    profiles = _assembly_profiles(assembly, values, joinery.tool_diameter_mm, True, cuts, overrides,
                                  resolve, captures)
    t = joinery.sheet.measured_mm
    out = tuple(replace(p, notes=p.notes + (joinery.sheet.note,)) if abs(p.thickness - t) <= 1e-9 else p
                for p in profiles)
    return out, results


# --- Width bindings (#95): native Fusion width edits at fixed topology -------

WIDTH = "Cab_Width"
_TOL = 1e-9
# Ties are float noise (about 1e-12 mm here); decisions against the producer's own
# 1e-9 thresholds must not land on this tolerance.
_DECISION_TOL = 1e-10


def _point(p, q, tol):
    return math.dist(p, q) <= tol


@dataclass(frozen=True)
class LoopBinding:
    """A profile loop as Exprs: ``vertices`` are the polygon_loop input
    (local u, v); ``sources`` say how each segment is built from them
    (see ``profile.polygon_loop_with_sources``)."""
    vertices: tuple
    sources: tuple

    def resolve(self, env):
        pts = [(u.eval(env), v.eval(env)) for u, v in self.vertices]

        def at(src):
            i, (du, dv) = src
            return (pts[i][0] + du, pts[i][1] + dv)
        segments = []
        for s in self.sources:
            if s[0] == "line":
                segments.append(Line(at(s[1]), at(s[2])))
            else:
                segments.append(Arc(at(s[1]), s[2], s[3], s[4]))
        return Loop(tuple(segments))

    def rename(self, f):
        return replace(self, vertices=tuple((f(u), f(v)) for u, v in self.vertices))


@dataclass(frozen=True)
class FeatureBinding:
    feature_id: str            # profile_fixture.feature_id: <panel_id>.cut.NNN
    kind: str                  # "through" or "pocket"
    face: str | None
    depth: Expr | None
    loop: LoopBinding


@dataclass(frozen=True)
class PanelBinding:
    """One panel's profile with Expr provenance, valid for ``parameter`` in
    ``interval`` with every other parameter fixed. Trusted Python only: no
    schema, nothing serialised. The numeric PanelProfile stays the oracle."""
    panel_id: str
    parameter: str
    interval: tuple
    frame_origin: tuple        # three Exprs
    frame_axes: tuple          # fixed signed unit axes (u, v, w)
    thickness: Expr
    outline: LoopBinding
    features: tuple

    def mismatch(self, profile, env, tol=_TOL):
        """None when the binding at ``env`` reproduces ``profile``, else why not."""
        f = profile.frame
        if profile.panel_id != self.panel_id or f is None:
            return "panel or frame"
        if (f.u, f.v, f.w) != self.frame_axes or not all(
                abs(e.eval(env) - o) <= tol for e, o in zip(self.frame_origin, f.origin)):
            return "frame"
        if abs(self.thickness.eval(env) - profile.thickness) > tol:
            return "thickness"
        if len(self.features) != len(profile.features):
            return "feature count"
        pairs = [(self.outline, profile.outline)]
        for b, feature in zip(self.features, profile.features):
            kind = "pocket" if isinstance(feature, Pocket) else "through" if isinstance(feature, ThroughCut) else None
            if kind != b.kind or getattr(feature, "face", None) != b.face:
                return b.feature_id + " kind"
            if kind == "pocket" and abs(b.depth.eval(env) - feature.depth) > tol:
                return b.feature_id + " depth"
            pairs.append((b.loop, feature.loop))
        for binding, loop in pairs:
            mine = binding.resolve(env).segments
            if len(mine) != len(loop.segments):
                return "segment count"
            for a, b in zip(mine, loop.segments):
                if type(a) is not type(b):
                    return "segment kind"
                if isinstance(a, Line):
                    if not (_point(a.start, b.start, tol) and _point(a.end, b.end, tol)):
                        return "line"
                elif not (_point(a.center, b.center, tol) and abs(a.radius - b.radius) <= tol
                          and abs(a.start_angle - b.start_angle) <= tol and a.sweep == b.sweep):
                    return "arc"
        return None


def _loop_binding(captured):
    verts, sources = captured
    return LoopBinding(tuple((expr_of(u), expr_of(v)) for u, v in verts), sources)


def _sign(x):
    return 0 if abs(x) <= _DECISION_TOL else (1 if x > 0 else -1)


def check_decisions(decisions, here, ends):
    """Refuse unless every logged (Expr, Expr) comparison has the same sign
    (<, = or >, within 1e-10 mm) at ``here`` and at each env in ``ends``.
    The Exprs are affine, so equal signs at both ends hold in between."""
    for a, b in decisions:
        d = _sign(a.eval(here) - b.eval(here))
        if any(_sign(a.eval(env) - b.eval(env)) != d for env in ends):
            raise ProfileError("A geometry decision changes within the interval: %s vs %s"
                               % (a.render(), b.render()))


def cabinet_tab_slot_width_bindings(assembly, joinery, values=None, *, parameter=WIDTH,
                                    interval=(1000.0, 1100.0)):
    """Module-frame PanelBindings for a native cabinet-width edit (#95).

    The numeric producer runs once on Tracked boxes, so every coordinate
    keeps the Expr it was built from: no fitting, no second geometry formula.
    Every value-based decision it takes (selections, ties, notch and grid
    tests) must come out the same at both interval ends; all Exprs are affine
    in the parameters, so the code path, topology and bindings then hold on
    the whole interval. The bindings are also checked against the numeric
    producer at both ends. Anything else is refused. Returns {panel_id: PanelBinding}.
    """
    if parameter != WIDTH:
        raise ProfileError("Only %s bindings are supported" % WIDTH)
    base = {p.name: p.value_mm for p in assembly.parameters.base()}
    base.update(values or {})
    if (not isinstance(interval, (tuple, list)) or len(interval) != 2
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in interval)
            or not interval[0] < interval[1] or not interval[0] <= base[WIDTH] <= interval[1]):
        raise ProfileError("interval must be finite (lo, hi) with lo < hi containing the current width")
    captures = {}
    with recording_decisions() as decisions:
        tracked, _ = _profiles(assembly, joinery, base, tracked_box, captures)
    numeric, _ = cabinet_tab_slot_profiles(assembly, joinery, base)
    if tracked != numeric:
        raise ProfileError("Tracked producer differs from the numeric producer")
    out = {}
    for p in numeric:
        cap = captures[p.panel_id]
        if cap["loops"][0] is None:
            raise ProfileError("%s: rounded outlines have no width binding" % p.panel_id)
        features = tuple(
            FeatureBinding(feature_id(p, i), kind, face, None if depth is None else expr_of(depth),
                           _loop_binding(loop))
            for i, ((kind, face, depth), loop) in enumerate(zip(cap["features"], cap["loops"][1:])))
        out[p.panel_id] = PanelBinding(
            p.panel_id, parameter, tuple(float(x) for x in interval), tuple(expr_of(x) for x in cap["origin"]),
            (p.frame.u, p.frame.v, p.frame.w), expr_of(cap["thickness"]), _loop_binding(cap["loops"][0]),
            features)
    envs = [assembly.parameters.resolve(dict(base, **{WIDTH: float(x)})) for x in interval]
    check_decisions(decisions, assembly.parameters.resolve(base), envs)
    for x, env in zip(interval, envs):
        for p in cabinet_tab_slot_profiles(assembly, joinery, dict(base, **{WIDTH: float(x)}))[0]:
            problem = out[p.panel_id].mismatch(p, env)
            if problem:
                raise ProfileError("%s binding differs at %s=%g: %s" % (p.panel_id, WIDTH, x, problem))
    return out
