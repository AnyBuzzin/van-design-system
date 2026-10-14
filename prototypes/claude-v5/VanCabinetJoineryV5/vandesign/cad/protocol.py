"""Adapter contract and the shared pre-flight every adapter must run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol

from ..components.model import AssemblyDefinition, ConstraintViolation
from ..verification.geometry_source import GeometrySource


class CadError(RuntimeError):
    pass


@dataclass
class CompileReport:
    created_parameters: List[str] = field(default_factory=list)
    created_panels: List[str] = field(default_factory=list)
    created_operations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CadAdapter(Protocol):
    def compile(self, assembly: AssemblyDefinition) -> CompileReport: ...
    def geometry_source(self) -> GeometrySource: ...


def preflight(assembly: AssemblyDefinition) -> None:
    """Structure + nominal constraints.  Raises BEFORE any geometry exists."""
    assembly.validate_structure()
    env = assembly.parameters.resolve()
    bad = [
        "%s (%s)" % (c.constraint_id, c.description)
        for c, ok, _, _ in assembly.check_constraints(env) if not ok
    ]
    if bad:
        raise ConstraintViolation("constraints violated: " + "; ".join(bad))
