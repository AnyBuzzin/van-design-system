"""Versioned, strict design-spec loader (G3) wrapped around the unchanged G2 core.

    schema 0.1 / 0.2 JSON text
        -> load_design_spec()  (strict: no duplicate/unknown keys, size cap, no NaN)
        -> CabinetDesignSpec   (resolved CabinetSpec + canonical text + hashes)
        -> build_variant()     (the one generator call, in modules/variants.py)

Hash policy (never mixed):
  * ``assembly_legacy_spec_hash`` == ``CabinetSpec.spec_hash()`` == the value the
    unchanged generator puts in ``AssemblyDefinition.spec_hash``.
  * ``design_spec_hash`` identifies the versioned document actually stored; its
    meaning is named by ``hash_scheme``.  For schema 0.1 it equals the legacy
    hash (scheme ``legacy-0.1-canonical-sha256``), for 0.2 it is the hash of the
    canonical 0.2 JSON (scheme ``g3-0.2-canonical-sha256``).
  * ``raw_sha256`` hashes the exact input bytes (used for stored attributes).

Stored 0.1 text is never rewritten; a 0.1 document re-emits through the
untouched G2 serialiser (``CabinetSpec.to_json``).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, fields
from typing import Any, Dict, List, Union

from ..modules.variants import (
    SUPPORTED_PROFILE_VERSION, SUPPORTED_VARIANTS, UnknownProfile, VariantProfile,
    get_profile, out_of_range_reasons, profile_defaults_spec)
from .cabinet_spec import CabinetSpec, SpecError

MAX_SPEC_BYTES = 64 * 1024
MAX_ABS_MM = 10000.0

HASH_SCHEME_LEGACY = "legacy-0.1-canonical-sha256"
HASH_SCHEME_V02 = "g3-0.2-canonical-sha256"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_FIELDS = tuple(f.name for f in fields(CabinetSpec))
_STR_FIELDS = ("cabinet_id", "material_ref")
_INT_FIELDS = ("shelf_count", "door_count")
_MM_FIELDS = tuple(n for n in _FIELDS if n.endswith("_mm"))

# Frozen G2 defaults for sparse schema-0.1 input.  Literal on purpose: they must
# never follow later edits to anything else.
LEGACY_DEFAULTS = {
    "cabinet_id": "cabinet.001", "material_ref": "ply_main",
    "width_mm": 1200.0, "height_mm": 850.0, "depth_mm": 550.0,
    "ply_mm": 18.0, "back_mm": 6.0, "gap_mm": 3.0, "dado_depth_mm": 6.0,
    "slot_clearance_mm": 0.5, "end_clearance_mm": 0.3,
    "shelf_count": 1, "door_count": 2,
}

_TOP_KEYS_01 = {"schema_version", "module", "parameters"}
_TOP_KEYS_02 = {"schema_version", "module", "variant", "profile_version", "parameters"}


@dataclass(frozen=True)
class CabinetDesignSpec:
    variant: str
    profile_version: int
    original_schema: str
    resolved_params: CabinetSpec
    canonical_stored_spec_json: str
    design_spec_hash: str
    hash_scheme: str
    migrated_in_memory: bool
    raw_sha256: str

    @property
    def assembly_legacy_spec_hash(self) -> str:
        return self.resolved_params.spec_hash()

    @property
    def profile(self) -> VariantProfile:
        return get_profile(self.variant, self.profile_version)

    def metadata(self) -> Dict[str, Any]:
        return {
            "design_schema_version": self.original_schema,
            "variant": self.variant,
            "profile_version": self.profile_version,
            "hash_scheme": self.hash_scheme,
            "design_spec_hash": self.design_spec_hash,
            "assembly_legacy_spec_hash": self.assembly_legacy_spec_hash,
            "migrated_in_memory": self.migrated_in_memory,
            "input_spec_raw_sha256": self.raw_sha256,
        }


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise SpecError("duplicate JSON key %r" % k)
        out[k] = v
    return out


def _reject_constant(name):
    raise SpecError("non-finite number %s is not allowed" % name)


def _parse(text: Union[str, bytes]):
    if isinstance(text, (bytes, bytearray)):
        if len(text) > MAX_SPEC_BYTES:
            raise SpecError("spec larger than %d bytes" % MAX_SPEC_BYTES)
        raw = bytes(text)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise SpecError("spec is not valid UTF-8") from None
    elif isinstance(text, str):
        try:
            raw = text.encode("utf-8")
        except UnicodeEncodeError:
            raise SpecError("spec contains invalid unicode") from None
        if len(raw) > MAX_SPEC_BYTES:
            raise SpecError("spec larger than %d bytes" % MAX_SPEC_BYTES)
    else:
        raise SpecError("spec must be text")
    if text.startswith("﻿"):
        raise SpecError("spec starts with a byte-order mark; save the file as UTF-8 without BOM")
    try:
        data = json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    except SpecError:
        raise
    except json.JSONDecodeError as e:
        raise SpecError("invalid JSON: %s" % e) from None
    except RecursionError:
        raise SpecError("spec nesting too deep") from None
    except ValueError as e:  # e.g. absurdly long integer literals
        raise SpecError("invalid JSON number: %s" % e) from None
    if not isinstance(data, dict):
        raise SpecError("spec must be a JSON object")
    return data, hashlib.sha256(raw).hexdigest()


def _check_params(params: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(params, dict):
        raise SpecError("'parameters' must be an object")
    unknown = sorted(set(params) - set(_FIELDS))
    if unknown:
        raise SpecError("unknown parameters: %s (allowed: %s)" % (", ".join(unknown), ", ".join(_FIELDS)))
    merged = dict(defaults)
    merged.update(params)
    problems: List[str] = []
    for name in _STR_FIELDS:
        v = merged[name]
        if not isinstance(v, str) or not _ID_RE.match(v):
            problems.append("%s must be 1-64 chars of letters, digits, '.', '_' or '-' (got %r)" % (name, v))
    for name in _INT_FIELDS:
        v = merged[name]
        if isinstance(v, bool) or not isinstance(v, int):
            problems.append("%s must be an integer (got %r)" % (name, v))
    for name in _MM_FIELDS:
        v = merged[name]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            problems.append("%s must be a number in mm (got %r)" % (name, v))
        elif not math.isfinite(v) or abs(v) > MAX_ABS_MM:
            problems.append("%s must be finite and within +/-%g mm (got %r)" % (name, MAX_ABS_MM, v))
    if problems:
        raise SpecError("invalid parameters: " + "; ".join(problems))
    return merged


def _build_spec(merged: Dict[str, Any]) -> CabinetSpec:
    try:
        return CabinetSpec(**merged)
    except SpecError:
        raise
    except (TypeError, ValueError) as e:
        raise SpecError(str(e)) from None


def _prove_buildable(spec: CabinetSpec) -> None:
    """Reject geometrically impossible nominal specs before any CAD call."""
    from ..modules.cabinet import build_cabinet  # local: avoid import-time cycle
    try:
        build_cabinet(spec)
    except ValueError as e:
        raise SpecError("spec cannot be built: %s" % e) from None


def canonical_v02_json(variant: str, profile_version: int, spec: CabinetSpec) -> str:
    params = {}
    for name in _FIELDS:
        v = getattr(spec, name)
        params[name] = float(v) if name in _MM_FIELDS else v
    doc = {"schema_version": "0.2", "module": "cabinet@1", "variant": variant,
           "profile_version": profile_version, "parameters": params}
    return json.dumps(doc, sort_keys=True, separators=(",", ":"))


def load_design_spec(text: Union[str, bytes]) -> CabinetDesignSpec:
    """Strictly load a schema 0.1 or 0.2 spec.  Raises SpecError; never touches CAD."""
    data, raw_hash = _parse(text)
    version = data.get("schema_version")
    if not isinstance(version, str):
        raise SpecError("schema_version must be the string \"0.1\" or \"0.2\" (got %r)" % (version,))
    if version == "0.1":
        return _load_01(data, raw_hash)
    if version == "0.2":
        return _load_02(data, raw_hash)
    raise SpecError("unsupported schema_version %r (supported: \"0.1\", \"0.2\")" % version)


def _load_01(data, raw_hash) -> CabinetDesignSpec:
    extra = sorted(set(data) - _TOP_KEYS_01)
    if extra:
        raise SpecError("unknown top-level field(s) for schema 0.1: %s" % ", ".join(extra))
    if data.get("module") != "base_cabinet@1":
        raise SpecError("schema 0.1 requires module \"base_cabinet@1\" (got %r)" % (data.get("module"),))
    if "parameters" not in data:
        raise SpecError("'parameters' object missing")
    merged = _check_params(data["parameters"], LEGACY_DEFAULTS)
    spec = _build_spec(merged)
    profile = get_profile("base", 1)
    bad = out_of_range_reasons(profile, spec)
    if bad:
        raise SpecError("; ".join(bad))
    _prove_buildable(spec)
    canonical = spec.to_json()  # untouched G2 serialiser
    return CabinetDesignSpec("base", 1, "0.1", spec, canonical, _sha(canonical),
                             HASH_SCHEME_LEGACY, True, raw_hash)


def _load_02(data, raw_hash) -> CabinetDesignSpec:
    extra = sorted(set(data) - _TOP_KEYS_02)
    if extra:
        raise SpecError("unknown top-level field(s) for schema 0.2: %s" % ", ".join(extra))
    if data.get("module") != "cabinet@1":
        raise SpecError("schema 0.2 requires module \"cabinet@1\" (got %r)" % (data.get("module"),))
    variant = data.get("variant")
    if not isinstance(variant, str) or variant not in SUPPORTED_VARIANTS:
        raise SpecError("variant must be one of %s (got %r)" % (", ".join(SUPPORTED_VARIANTS), variant))
    pv = data.get("profile_version")
    if isinstance(pv, bool) or not isinstance(pv, int):
        raise SpecError("profile_version must be an integer (supported: %d)" % SUPPORTED_PROFILE_VERSION)
    try:
        profile = get_profile(variant, pv)
    except UnknownProfile as e:
        raise SpecError(str(e)) from None
    params = data.get("parameters", {})
    merged = _check_params(params, dict(profile.defaults))
    spec = _build_spec(merged)
    bad = out_of_range_reasons(profile, spec)
    if bad:
        raise SpecError("; ".join(bad))
    _prove_buildable(spec)
    canonical = canonical_v02_json(variant, pv, spec)
    return CabinetDesignSpec(variant, pv, "0.2", spec, canonical, _sha(canonical),
                             HASH_SCHEME_V02, False, raw_hash)


def default_design_spec() -> CabinetDesignSpec:
    """No spec file: the exact legacy G2 default (schema 0.1 base cabinet)."""
    text = CabinetSpec().to_json()
    return load_design_spec(text)
