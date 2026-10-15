"""CabinetSpec: the typed, versioned design intent for one base cabinet.

All lengths are millimetres.  ``shelf_count`` and ``door_count`` are
structural: changing them means re-generating (see NOT_IMPLEMENTED.md).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, fields
from typing import Any, Dict

from .. import SCHEMA_VERSION


class SpecError(ValueError):
    pass


@dataclass(frozen=True)
class CabinetSpec:
    cabinet_id: str = "cabinet.001"
    material_ref: str = "ply_main"
    width_mm: float = 1200.0
    height_mm: float = 850.0
    depth_mm: float = 550.0
    ply_mm: float = 18.0
    back_mm: float = 6.0
    gap_mm: float = 3.0
    dado_depth_mm: float = 6.0
    slot_clearance_mm: float = 0.5
    end_clearance_mm: float = 0.3
    shelf_count: int = 1
    door_count: int = 2

    def __post_init__(self):
        problems = []
        for f in fields(self):
            v = getattr(self, f.name)
            if f.name.endswith("_mm") and (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)):
                problems.append("%s must be a finite number" % f.name)
        if not isinstance(self.shelf_count, int) or isinstance(self.shelf_count, bool) or not 0 <= self.shelf_count <= 4:
            problems.append("shelf_count must be an integer 0-4")
        if not isinstance(self.door_count, int) or isinstance(self.door_count, bool) or self.door_count not in (1, 2):
            problems.append("door_count must be 1 or 2")
        if problems:
            raise SpecError("invalid CabinetSpec: " + "; ".join(problems))

    def to_dict(self) -> Dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "module": "base_cabinet@1", "parameters": asdict(self)}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def spec_hash(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CabinetSpec":
        if data.get("schema_version") != SCHEMA_VERSION:
            raise SpecError("unsupported schema_version %r (expected %r)" % (data.get("schema_version"), SCHEMA_VERSION))
        if data.get("module") != "base_cabinet@1":
            raise SpecError("unsupported module %r" % data.get("module"))
        params = data.get("parameters")
        if not isinstance(params, dict):
            raise SpecError("'parameters' object missing")
        known = {f.name for f in fields(cls)}
        unknown = set(params) - known
        if unknown:
            raise SpecError("unknown parameters: %s" % ", ".join(sorted(unknown)))
        return cls(**params)

    @classmethod
    def from_json(cls, text: str) -> "CabinetSpec":
        try:
            return cls.from_dict(json.loads(text))
        except json.JSONDecodeError as e:
            raise SpecError("invalid JSON: %s" % e) from None
