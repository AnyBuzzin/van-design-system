"""Dimension-checked length expressions.

An ``Expr`` is a length in millimetres built from named parameters.  It has
exactly ONE definition and two projections:

    expr.eval(env)   -> float mm   (pure Python, used by validation)
    expr.render()    -> string     (written into Fusion as a parameter
                                    expression, so Fusion stays the editing
                                    environment)

Dimension rules: lengths may be added/subtracted only with other lengths and
scaled/divided only by plain numbers.  ``Expr * Expr`` and ``Expr + 5`` are
rejected, so a dimensionless slip cannot reach the CAD model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Mapping, Tuple


class ExprError(ValueError):
    pass


def _fmt(x: float) -> str:
    x = float(x)
    if x.is_integer():
        return str(int(x))
    return repr(x)


def _as_expr(other) -> "Expr":
    if isinstance(other, Expr):
        return other
    raise ExprError(
        "bare number %r in a length expression; wrap lengths in Mm(...)" % (other,)
    )


def _as_number(k):
    if isinstance(k, Expr) or isinstance(k, bool) or not isinstance(k, (int, float)):
        raise ExprError(
            "can only scale/divide a length by a plain number, got %r" % (k,)
        )
    return k


class Expr:
    def eval(self, env: Mapping[str, float]) -> float:
        raise NotImplementedError

    def render(self) -> str:
        raise NotImplementedError

    def refs(self) -> FrozenSet[str]:
        raise NotImplementedError

    def __add__(self, other):
        return Sum(((1, self), (1, _as_expr(other))))

    def __sub__(self, other):
        return Sum(((1, self), (-1, _as_expr(other))))

    def __mul__(self, k):
        return Scale(_as_number(k), self)

    __rmul__ = __mul__

    def __truediv__(self, k):
        return Div(self, _as_number(k))

    def __neg__(self):
        return Scale(-1, self)


@dataclass(frozen=True)
class Param(Expr):
    name: str

    def eval(self, env):
        try:
            return float(env[self.name])
        except KeyError:
            raise ExprError("unknown parameter %r" % self.name) from None

    def render(self):
        return self.name

    def refs(self):
        return frozenset((self.name,))


@dataclass(frozen=True)
class Mm(Expr):
    value: float

    def eval(self, env):
        return float(self.value)

    def render(self):
        return "%s mm" % _fmt(self.value)

    def refs(self):
        return frozenset()


@dataclass(frozen=True)
class Sum(Expr):
    terms: Tuple[Tuple[int, Expr], ...]

    def eval(self, env):
        return sum(sign * t.eval(env) for sign, t in self.terms)

    def render(self):
        parts = []
        for i, (sign, t) in enumerate(self.terms):
            r = t.render()
            if i == 0:
                parts.append(r if sign > 0 else "-" + r)
            else:
                parts.append(("+ " if sign > 0 else "- ") + r)
        return "(" + " ".join(parts) + ")"

    def refs(self):
        out = frozenset()
        for _, t in self.terms:
            out |= t.refs()
        return out


@dataclass(frozen=True)
class Scale(Expr):
    k: float
    e: Expr

    def eval(self, env):
        return self.k * self.e.eval(env)

    def render(self):
        return "(%s * %s)" % (_fmt(self.k), self.e.render())

    def refs(self):
        return self.e.refs()


def substitute(expr: Expr, mapping: Mapping[str, Expr]) -> Expr:
    """Copy of ``expr`` with parameters replaced (e.g. per-instance renaming)."""
    if isinstance(expr, Param):
        return mapping.get(expr.name, expr)
    if isinstance(expr, Mm):
        return expr
    if isinstance(expr, Sum):
        return Sum(tuple((s, substitute(t, mapping)) for s, t in expr.terms))
    if isinstance(expr, Scale):
        return Scale(expr.k, substitute(expr.e, mapping))
    if isinstance(expr, Div):
        return Div(substitute(expr.e, mapping), expr.k)
    raise ExprError("cannot substitute into %r" % (expr,))


@dataclass(frozen=True)
class Div(Expr):
    e: Expr
    k: float

    def __post_init__(self):
        if self.k == 0:
            raise ExprError("division by zero in length expression")

    def eval(self, env):
        return self.e.eval(env) / self.k

    def render(self):
        return "(%s / %s)" % (self.e.render(), _fmt(self.k))

    def refs(self):
        return self.e.refs()
