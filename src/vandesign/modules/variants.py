"""Data-only cabinet variant profiles (G3).

A profile is IMMUTABLE DATA per ``variant@profile_version``: default resolved
parameters, allowed shelf/door counts and provisional live-range limits.  It
contains no panels, expressions or geometry.  Every variant is built by the one
generator, ``build_cabinet`` (see :func:`build_variant`).

The sizes are TEST FIXTURES demonstrating code reuse.  They are not engineering
sign-off, not van-fit, structural, load or fixing limits.  A future change to a
profile must be a new ``profile_version``; existing versions never change.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional, Tuple

from ..components.model import AssemblyDefinition
from ..schemas.cabinet_spec import CabinetSpec
from .cabinet import build_cabinet

SUPPORTED_VARIANTS = ("base", "tall", "overhead")
SUPPORTED_PROFILE_VERSION = 1

_COMMON = (
    ("cabinet_id", "cabinet.001"),
    ("material_ref", "ply_main"),
    ("ply_mm", 18.0),
    ("back_mm", 6.0),
    ("gap_mm", 3.0),
    ("dado_depth_mm", 6.0),
    ("slot_clearance_mm", 0.5),
    ("end_clearance_mm", 0.3),
)


@dataclass(frozen=True)
class Limit:
    """Inclusive provisional range for one live Fusion parameter (mm)."""
    min_mm: float
    max_mm: float


@dataclass(frozen=True)
class VariantProfile:
    variant: str
    profile_version: int
    defaults: Mapping[str, object]          # every CabinetSpec field, fully resolved
    shelf_range: Tuple[int, int]            # inclusive
    door_range: Tuple[int, int]             # inclusive
    limits: Mapping[str, Limit]             # keyed by Fusion parameter name; empty for base

    @property
    def key(self) -> str:
        return "%s@%d" % (self.variant, self.profile_version)


def _profile(variant, w, h, d, shelves, doors, shelf_range, door_range, limits):
    defaults = dict(_COMMON)
    defaults.update(width_mm=float(w), height_mm=float(h), depth_mm=float(d),
                    shelf_count=shelves, door_count=doors)
    return VariantProfile(variant, 1, MappingProxyType(defaults), shelf_range, door_range,
                          MappingProxyType(dict(limits)))


_PROFILES = {
    ("base", 1): _profile("base", 1200, 850, 550, 1, 2, (0, 4), (1, 2), {}),
    ("tall", 1): _profile("tall", 600, 1900, 550, 3, 1, (1, 4), (1, 2), {
        "Cab_Width": Limit(300.0, 900.0),
        "Cab_Height": Limit(1400.0, 2200.0),
        "Cab_Depth": Limit(300.0, 650.0)}),
    ("overhead", 1): _profile("overhead", 1000, 400, 350, 1, 2, (0, 2), (1, 2), {
        "Cab_Width": Limit(300.0, 1500.0),
        "Cab_Height": Limit(250.0, 700.0),
        "Cab_Depth": Limit(250.0, 450.0)}),
}


class UnknownProfile(ValueError):
    pass


def get_profile(variant: str, profile_version: int) -> VariantProfile:
    if isinstance(profile_version, bool) or not isinstance(profile_version, int):
        raise UnknownProfile("profile_version must be an integer")
    try:
        return _PROFILES[(variant, profile_version)]
    except (KeyError, TypeError):
        raise UnknownProfile("unknown profile %r version %r (supported: %s)" % (
            variant, profile_version,
            ", ".join(sorted(p.key for p in _PROFILES.values())))) from None


def profile_defaults_spec(profile: VariantProfile) -> CabinetSpec:
    return CabinetSpec(**dict(profile.defaults))


def out_of_range_reasons(profile: VariantProfile, spec: CabinetSpec) -> list:
    """Reasons a resolved spec lies outside the profile (empty list = inside)."""
    reasons = []
    lo, hi = profile.shelf_range
    if not lo <= spec.shelf_count <= hi:
        reasons.append("shelf_count %d outside %s allowed range %d-%d" % (spec.shelf_count, profile.key, lo, hi))
    lo, hi = profile.door_range
    if not lo <= spec.door_count <= hi:
        reasons.append("door_count %d outside %s allowed range %d-%d" % (spec.door_count, profile.key, lo, hi))
    field_for = {"Cab_Width": spec.width_mm, "Cab_Height": spec.height_mm, "Cab_Depth": spec.depth_mm}
    for name, limit in profile.limits.items():
        v = field_for[name]
        if not limit.min_mm <= v <= limit.max_mm:
            reasons.append("%s %.1f mm outside %s range %.1f-%.1f mm" % (name, v, profile.key, limit.min_mm, limit.max_mm))
    return reasons


def profile_limits(profile: VariantProfile) -> Mapping[str, Tuple[float, float]]:
    """Plain (min, max) mapping handed to ``validate(profile_limits=...)``."""
    return {k: (v.min_mm, v.max_mm) for k, v in profile.limits.items()}


def build_variant(spec: CabinetSpec, profile: Optional[VariantProfile] = None) -> AssemblyDefinition:
    """The single generator call.  Profiles add metadata/limits only."""
    return build_cabinet(spec)
