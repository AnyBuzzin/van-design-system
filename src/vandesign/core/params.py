"""Ordered parameter graph.

Base parameters carry a value in mm; derived parameters carry an ``Expr``.
A derived parameter may only reference parameters defined BEFORE it, which
makes cycles and forward references impossible by construction (this is also
the order Fusion requires when the parameters are created).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple

from .expr import Expr

_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ParameterError(ValueError):
    pass


@dataclass(frozen=True)
class ParamDef:
    name: str
    value_mm: Optional[float] = None
    expr: Optional[Expr] = None
    comment: str = ""

    @property
    def is_base(self) -> bool:
        return self.expr is None


@dataclass(frozen=True)
class ParameterSet:
    params: Tuple[ParamDef, ...]

    def __post_init__(self):
        seen = set()
        for p in self.params:
            if not _NAME.match(p.name):
                raise ParameterError("invalid parameter name %r" % p.name)
            if p.name in seen:
                raise ParameterError("duplicate parameter %r" % p.name)
            if (p.value_mm is None) == (p.expr is None):
                raise ParameterError(
                    "%s: exactly one of value_mm / expr is required" % p.name
                )
            if p.value_mm is not None and not math.isfinite(p.value_mm):
                raise ParameterError("%s: value must be finite" % p.name)
            if p.expr is not None:
                missing = p.expr.refs() - seen
                if missing:
                    raise ParameterError(
                        "%s references undefined/later parameters: %s"
                        % (p.name, ", ".join(sorted(missing)))
                    )
            seen.add(p.name)

    def names(self):
        return tuple(p.name for p in self.params)

    def base(self):
        return tuple(p for p in self.params if p.is_base)

    def derived(self):
        return tuple(p for p in self.params if not p.is_base)

    def resolve(self, base_values: Optional[Mapping[str, float]] = None) -> Dict[str, float]:
        """Resolve every parameter to mm, optionally overriding base values
        (this is how a Fusion 'Change Parameters' edit is modelled)."""
        overrides = dict(base_values or {})
        base_names = {p.name for p in self.base()}
        unknown = set(overrides) - base_names
        if unknown:
            raise ParameterError(
                "overrides for non-base parameters: %s" % ", ".join(sorted(unknown))
            )
        env: Dict[str, float] = {}
        for p in self.params:
            if p.is_base:
                v = float(overrides.get(p.name, p.value_mm))
                if not math.isfinite(v):
                    raise ParameterError("%s: value must be finite" % p.name)
                env[p.name] = v
            else:
                env[p.name] = p.expr.eval(env)
        return env
