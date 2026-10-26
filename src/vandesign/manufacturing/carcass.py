"""Tab-and-slot cabinet carcass: joinery spec and module-local profiles.

Bottom and top tab flush through both sides (engagement = measured side
thickness); shelves keep their dados; doors and back are unchanged. Profiles
are computed in the cabinet's own frame: a part's cut shape does not change
when the cabinet is moved or rotated, only its frame does.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math

from ..core.expr import Expr, Param
from ..core.geometry import Box
from ..modules.profile_fixture import feature_id
from .assembly import _assembly_profiles, _resolve, Tracked, expr_of, recording_decisions, tracked_box
from .corner import CornerFixings, corner_holes
from .fronts import InsetFronts, add_hardware, hardware, inset_boxes
from .joints import MIN_SKIN_MM, Sheet, TabSlot, apply_joints
from .top import CarcassTop, fixing_holes, sink_opening
from .profile import Arc, Hole, Line, Loop, Pocket, ProfileError, ThroughCut

_JOINERY_KEYS = {"sheet", "clearance_mm", "tabs_per_edge", "tab_width_mm", "tool_diameter_mm"}
_OPTIONAL_KEYS = {"blind_slot_depth_mm", "dado_stop_mm", "back_rabbet_mm", "fronts", "top", "corner_fixings"}
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
    # ADR-0003: shelf dados stop this far behind the front edge (None = open at the front).
    dado_stop_mm: float | None = None
    # ADR-0003: the back sits in rabbets this deep in both sides (None = back butts between them).
    back_rabbet_mm: float | None = None
    # ADR-0003: inset doors with hidden hardware bores (None = the module's overlay doors).
    fronts: InsetFronts | None = None
    # ADR-0003: worktop fixing holes and an optional sink opening in the carcass top.
    top: CarcassTop | None = None
    # ADR-0003: clearance holes in a side that butts another cabinet's blind panel.
    corner_fixings: CornerFixings | None = None

    def __post_init__(self):
        if self.corner_fixings is not None and type(self.corner_fixings) is not CornerFixings:
            raise ProfileError("corner_fixings must be CornerFixings")
        if self.top is not None and type(self.top) is not CarcassTop:
            raise ProfileError("top must be CarcassTop")
        if self.fronts is not None and type(self.fronts) is not InsetFronts:
            raise ProfileError("fronts must be InsetFronts")
        b = self.blind_slot_depth_mm
        if b is not None and (type(b) not in (int, float) or not math.isfinite(b)
                              or b <= self.clearance_mm / 2):
            raise ProfileError("blind_slot_depth_mm must be a number greater than clearance_mm / 2")
        for name in ("dado_stop_mm", "back_rabbet_mm"):
            v = getattr(self, name)
            if v is not None and (type(v) not in (int, float) or not math.isfinite(v) or v <= 0):
                raise ProfileError("%s must be a positive number" % name)
        if self.back_rabbet_mm is not None and self.back_rabbet_mm <= self.clearance_mm / 2:
            raise ProfileError("back_rabbet_mm must be greater than clearance_mm / 2")
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
        """Strict: exact keys (tab_width_mm may be null), plus the optional
        ADR-0003 keys."""
        if not isinstance(data, dict) or not _JOINERY_KEYS <= set(data) <= _JOINERY_KEYS | _OPTIONAL_KEYS:
            raise ProfileError("joinery needs exactly: " + ", ".join(sorted(_JOINERY_KEYS))
                               + " (and optionally " + ", ".join(sorted(_OPTIONAL_KEYS)) + ")")
        sheet = data["sheet"]
        if not isinstance(sheet, dict) or set(sheet) != _SHEET_KEYS:
            raise ProfileError("sheet needs exactly: " + ", ".join(sorted(_SHEET_KEYS)))
        return cls(Sheet(sheet["name"], sheet["nominal_mm"], sheet["measured_mm"]), data["tool_diameter_mm"],
                   data["clearance_mm"], data["tabs_per_edge"], data["tab_width_mm"],
                   data.get("blind_slot_depth_mm"), data.get("dado_stop_mm"), data.get("back_rabbet_mm"),
                   None if data.get("fronts") is None else InsetFronts.from_json(data["fronts"]),
                   None if data.get("top") is None else CarcassTop.from_json(data["top"]),
                   None if data.get("corner_fixings") is None else CornerFixings.from_json(data["corner_fixings"]))


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
    fronts = inset_boxes(boxes, joinery.fronts) if joinery.fronts is not None else {}
    boxes.update(fronts)
    joint_overrides, cuts, results = apply_joints(cabinet_joints(boxes, joinery), boxes)
    more_overrides, more_cuts, dados = housings(assembly, boxes, joinery, env, resolve)
    overrides = dict(fronts, **joint_overrides)
    overrides.update(more_overrides)
    captures = {} if captures is None else captures       # hardware needs each frame's origin
    if joinery.top is not None:
        more_cuts += sink_opening(boxes, joinery.top)
    profiles = _assembly_profiles(assembly, values, joinery.tool_diameter_mm, True, cuts + more_cuts, overrides,
                                  resolve, captures, dados)
    holes = hardware(boxes, joinery.fronts) if joinery.fronts is not None else {}
    extra = [fixing_holes(boxes, joinery.top) if joinery.top is not None else {},
             corner_holes(boxes, joinery.corner_fixings) if joinery.corner_fixings is not None else {}]
    for more in extra:
        for pid, found in more.items():
            holes.setdefault(pid, []).extend(found)
    if holes:
        profiles = add_hardware(profiles, holes, captures)
    for p in profiles:
        _features_apart(p)
    t = joinery.sheet.measured_mm
    out = tuple(replace(p, notes=p.notes + (joinery.sheet.note,)) if abs(p.thickness - t) <= 1e-9 else p
                for p in profiles)
    return out, results


def _param(name, env, resolve):
    """A cabinet parameter value, Tracked when the boxes are (width bindings)."""
    return Tracked(env[name], Param(name)) if resolve is tracked_box else env[name]


def _inside(inner, outer, tol=1e-9):
    return all(o_lo - tol <= i_lo and i_hi <= o_hi + tol
               for i_lo, i_hi, o_lo, o_hi in zip(inner.lo, inner.hi, outer.lo, outer.hi))


def housings(assembly, boxes, joinery, env, resolve=_resolve):
    """ADR-0003 stopped dados and back rabbets (module frame).

    Stopped dado: the shelf groove starts ``dado_stop_mm`` behind the side's
    front edge; the shelf is notched at its front corners so its tongue stops
    Cab_End_Clearance short of the groove end. Back rabbet: the back grows
    ``back_rabbet_mm - clearance/2`` into each side, which gets a rabbet open
    only to its rear edge (clearance/2 on every closed face). With a rabbet,
    each dado also stops one tool diameter short of it (rear notches on the
    shelf), so no two machined features overlap. Every tongue is proved to lie
    inside its housing. Returns (box overrides, extra cuts, dado cut overrides).
    """
    stop, rabbet = joinery.dado_stop_mm, joinery.back_rabbet_mm
    over, cuts, dados = {}, [], {}
    if stop is None and rabbet is None:
        return over, (), dados
    c, land = joinery.clearance_mm, joinery.tool_diameter_mm
    ec = _param("Cab_End_Clearance", env, resolve)
    sides = {"left": boxes["panel.left.001"], "right": boxes["panel.right.001"]}
    rear = None
    if rabbet is not None:
        if rabbet > joinery.sheet.measured_mm - MIN_SKIN_MM + 1e-9:
            raise ProfileError("back_rabbet_mm leaves less than %g mm of side panel" % MIN_SKIN_MM)
        back = boxes["panel.back.001"]
        grow = rabbet - c / 2
        tongue = Box((back.lo[0] - grow, back.lo[1], back.lo[2]), (back.hi[0] + grow, back.hi[1], back.hi[2]))
        over["panel.back.001"] = tongue
        rear = back.lo[1] - c / 2
        for side, s in sides.items():
            x = (s.hi[0] - rabbet, s.hi[0]) if side == "left" else (s.lo[0], s.lo[0] + rabbet)
            cut = Box((x[0], rear, back.lo[2] - c / 2), (x[1], s.hi[1], back.hi[2] + c / 2))
            if not _inside(cut.intersection(tongue), cut):
                raise ProfileError("Back tongue leaves its rabbet")
            cuts.append(("panel.%s.001" % side, cut))
    for op in assembly.operations:
        cut, shelf, side = resolve(op.cut, env), boxes[op.mating_panel_id], sides[op.side]
        y0 = cut.lo[1] + stop if stop is not None else cut.lo[1]
        if stop is not None and y0 < shelf.lo[1] + land:
            y0 = shelf.lo[1]       # shelf already set back (inset doors): groove starts at its hidden front
        y1 = rear - land if rear is not None else cut.hi[1]
        if not y0 + ec < y1 - ec:
            raise ProfileError("%s: stopped dado leaves no groove" % op.operation_id)
        groove = Box((cut.lo[0], y0, cut.lo[2]), (cut.hi[0], y1, cut.hi[2]))
        dados[op.operation_id] = groove
        x = (shelf.lo[0], side.hi[0]) if op.side == "left" else (side.lo[0], shelf.hi[0])
        lo, hi = shelf.lo[1], shelf.hi[1]
        if y0 > shelf.lo[1]:
            lo = y0 + ec
            cuts.append((op.mating_panel_id, Box((x[0], shelf.lo[1], shelf.lo[2]), (x[1], lo, shelf.hi[2]))))
        if y1 < shelf.hi[1]:
            hi = y1 - ec
            cuts.append((op.mating_panel_id, Box((x[0], hi, shelf.lo[2]), (x[1], shelf.hi[1], shelf.hi[2]))))
        if not _inside(Box((x[0], lo, shelf.lo[2]), (x[1], hi, shelf.hi[2])), groove):
            raise ProfileError("%s: shelf tongue leaves its stopped dado" % op.operation_id)
    return over, tuple(cuts), dados


def _features_apart(profile):
    """Refuse machined features whose extents (relief included) overlap: each
    cut must remove exactly its own area, in CAM and in the live Fusion check."""
    bounds = [f.loop.bounds if hasattr(f, "loop") else
              ((f.center[0] - f.diameter / 2, f.center[1] - f.diameter / 2),
               (f.center[0] + f.diameter / 2, f.center[1] + f.diameter / 2)) for f in profile.features]
    for i, ((ax0, ay0), (ax1, ay1)) in enumerate(bounds):
        for (bx0, by0), (bx1, by1) in bounds[i + 1:]:
            if min(ax1, bx1) - max(ax0, bx0) > 1e-9 and min(ay1, by1) - max(ay0, by0) > 1e-9:
                raise ProfileError("%s: machined features overlap" % profile.panel_id)


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
    kind: str                  # "through", "pocket" or "hole"
    face: str | None
    depth: Expr | None
    loop: LoopBinding | None   # None for a hole
    center: tuple | None = None    # hole centre (Expr u, Expr v)
    diameter: float | None = None

    def rename(self, f, feature_id):
        return replace(self, feature_id=feature_id, depth=None if self.depth is None else f(self.depth),
                       loop=None if self.loop is None else self.loop.rename(f),
                       center=None if self.center is None else tuple(f(e) for e in self.center))


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
            kind = ("pocket" if isinstance(feature, Pocket) else "through" if isinstance(feature, ThroughCut)
                    else "hole" if isinstance(feature, Hole) else None)
            if kind != b.kind or getattr(feature, "face", None) != b.face:
                return b.feature_id + " kind"
            if kind == "hole" and (b.depth is None) != (feature.depth is None):
                return b.feature_id + " depth"
            if (kind == "pocket" or (kind == "hole" and b.depth is not None)) and abs(
                    b.depth.eval(env) - feature.depth) > tol:
                return b.feature_id + " depth"
            if kind == "hole":
                if b.diameter != feature.diameter or not _point(
                        tuple(e.eval(env) for e in b.center), feature.center, tol):
                    return b.feature_id + " hole"
                continue
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
        features += tuple(
            FeatureBinding(feature_id(p, len(features) + i), "hole", face,
                           None if depth is None else expr_of(depth), None,
                           (expr_of(a), expr_of(b)), float(diameter))
            for i, (a, b, diameter, depth, face) in enumerate(cap.get("holes", ())))
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
