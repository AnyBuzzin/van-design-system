"""Backend-neutral view of ACTUAL CAD geometry, as read back from the model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from ..core.geometry import Box, Vec


@dataclass(frozen=True)
class MeasuredBody:
    box: Box            # axis-aligned bounding box, mm
    volume_mm3: float


class GeometrySource(Protocol):
    """Every method returns None when the evidence is unavailable."""

    diagnostics: list

    def parameter_value(self, name: str) -> Optional[float]:
        """Current value of a user parameter in mm."""

    def body(self, panel_id: str) -> Optional[MeasuredBody]:
        """The single BRep body owned by this stable id."""

    def point_in_material(self, panel_id: str, point_mm: Vec) -> Optional[bool]:
        """True = inside solid material, False = outside, None = unknown/on boundary."""

    def interference_count(self, panel_ids: Sequence[str]) -> Optional[int]:
        """Number of interfering body pairs among the given panels."""
