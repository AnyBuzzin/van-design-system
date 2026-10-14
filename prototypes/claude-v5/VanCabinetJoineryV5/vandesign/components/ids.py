"""Stable machine identifiers.

IDs never depend on a Browser display name or creation order.  They are
stored on Fusion components as attributes and are the only lookup key.
"""

import re

_ID = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$")


class IdError(ValueError):
    pass


def make_id(*parts) -> str:
    s = ".".join(str(p) for p in parts)
    if not _ID.match(s):
        raise IdError("invalid stable id %r" % s)
    return s


def panel_id(role: str, index: int = 1) -> str:
    return make_id("panel", role, "%03d" % index)


def dado_id(shelf_index: int, side: str) -> str:
    return make_id("dado", "shelf%d" % shelf_index, side)
