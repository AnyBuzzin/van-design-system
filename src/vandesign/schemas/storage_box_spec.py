"""Strict standalone storage contract; nominal geometry only, not a structural design."""
from dataclasses import dataclass, asdict
import hashlib
import json
import math

MODULE = "storage-box@1"
SCHEMA = "vandesign.storage-box/1"
NOTICE = ("UNQUALIFIED GEOMETRIC STORAGE FURNITURE: no load capacity, lateral stability, "
          "anchoring or manufacturing suitability established")


@dataclass(frozen=True)
class StorageBoxSpec:
    width_mm: float = 600.0
    length_mm: float = 800.0
    height_mm: float = 250.0  # external TOP above local Z=0
    ply_mm: float = 18.0

    def __post_init__(self):
        for name, value in asdict(self).items():
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not 0 < value <= 10000 or not math.isfinite(value)):
                raise ValueError(name + " must be finite positive mm, at most 10000")
            object.__setattr__(self, name, float(value))
        if self.ply_mm != 18:
            raise ValueError("Storage prototype supports nominal uniform 18 mm plywood only")

        if self.width_mm <= 2*self.ply_mm or self.length_mm <= 2*self.ply_mm or self.height_mm <= self.ply_mm:
            raise ValueError("Storage interior must have positive width, length and height")

    def to_json(self):
        return json.dumps({"schema_version": SCHEMA, "module": MODULE,
                           "parameters": asdict(self)}, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)

    def spec_hash(self):
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def load_storage_spec(text):
    """No cabinet schema migration or cabinet hash semantics are involved."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate storage specification key: " + key)
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("nonfinite JSON number: " + value)

    if not isinstance(text, (str, bytes)) or len(text) > 64 * 1024:
        raise ValueError("storage specification must be JSON text, at most 64 KiB")
    raw = json.loads(text, object_pairs_hook=unique, parse_constant=invalid)
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "module", "parameters"}:
        raise ValueError("storage specification requires exactly schema_version, module, parameters")
    if raw["schema_version"] != SCHEMA or raw["module"] != MODULE:
        raise ValueError("unsupported storage specification identity/version")
    params = raw["parameters"]
    if not isinstance(params, dict) or set(params) - set(StorageBoxSpec.__dataclass_fields__):
        raise ValueError("unknown storage parameter or invalid parameters object")
    return StorageBoxSpec(**params)

