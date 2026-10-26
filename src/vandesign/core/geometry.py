"""Axis-aligned box primitives (mm) and their parametric (Expr) form."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Optional, Tuple

from .expr import Expr

Vec = Tuple[float, float, float]


class GeometryError(ValueError):
    pass


@dataclass(frozen=True)
class RoundedCornerOutline:
    """Fixed CCW upper-right quarter-circle family in local XY millimetres."""
    width: float
    length: float
    radius: float

    def __post_init__(self):
        if (any(type(v) not in (int, float) or not 0 < v <= 10000 or not math.isfinite(v)
                for v in (self.width, self.length, self.radius))
                or self.radius >= min(self.width, self.length)):
            raise GeometryError('Require finite positive W,L and 0 < R < min(W,L)')

    @property
    def vertices(self):
        w,l,r = self.width,self.length,self.radius
        return ((0,0),(w,0),(w,l-r),(w-r,l),(0,l))

    @property
    def lines(self):
        a,b,c,d,e = self.vertices
        return ((a,b),(b,c),(d,e),(e,a))

    @property
    def arc(self):
        return dict(center=(self.width-self.radius,self.length-self.radius),
                    start=self.vertices[2],end=self.vertices[3],sweep_radians=math.pi/2)

    @property
    def area_mm2(self):
        return self.width*self.length-(1-math.pi/4)*self.radius**2


@dataclass(frozen=True)
class Box:
    lo: Vec
    hi: Vec

    @property
    def size(self) -> Vec:
        return tuple(h - l for l, h in zip(self.lo, self.hi))

    @property
    def volume(self) -> float:
        sx, sy, sz = self.size
        return sx * sy * sz

    def intersection(self, other: "Box") -> Optional["Box"]:
        lo = tuple(max(a, b) for a, b in zip(self.lo, other.lo))
        hi = tuple(min(a, b) for a, b in zip(self.hi, other.hi))
        if any(h - l <= 1e-9 for l, h in zip(lo, hi)):
            return None
        return Box(lo, hi)

    def overlap_volume(self, other: "Box") -> float:
        i = self.intersection(other)
        return i.volume if i else 0.0

    def contains_box(self, other: "Box", eps: float = 1e-9) -> bool:
        return all(
            s_lo - eps <= o_lo and o_hi <= s_hi + eps
            for s_lo, s_hi, o_lo, o_hi in zip(self.lo, self.hi, other.lo, other.hi)
        )

    def contains_point(self, p: Vec, eps: float = 1e-9) -> bool:
        return all(l + eps < c < h - eps for l, h, c in zip(self.lo, self.hi, p))

    def max_deviation(self, other: "Box") -> Tuple[float, str]:
        """Largest absolute corner difference and the axis/side it is on."""
        worst, label = 0.0, "-"
        for axis, name in enumerate("XYZ"):
            for side, (a, b) in (("min", (self.lo, other.lo)), ("max", (self.hi, other.hi))):
                d = abs(a[axis] - b[axis])
                if d > worst:
                    worst, label = d, name + side
        return worst, label


@dataclass(frozen=True)
class BoxExpr:
    """Box given by origin (bottom-left-front corner) and size, as Exprs."""

    origin: Tuple[Expr, Expr, Expr]
    size: Tuple[Expr, Expr, Expr]

    def resolve(self, env: Mapping[str, float]) -> Box:
        lo = tuple(e.eval(env) for e in self.origin)
        sz = tuple(e.eval(env) for e in self.size)
        if any(s <= 0 for s in sz):
            raise GeometryError("non-positive box size %r" % (sz,))
        return Box(lo, tuple(l + s for l, s in zip(lo, sz)))

    def refs(self):
        out = frozenset()
        for e in self.origin + self.size:
            out |= e.refs()
        return out
