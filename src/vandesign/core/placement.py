"""Quarter-turn placement about the vertical (Z) axis.

Quarter-turns keep every panel and cut an axis-aligned box, so placed modules
stay inside the existing BoxExpr/adapter model with no new CAD primitives.
Turn k rotates module-local (x, y) by k * 90 degrees counter-clockwise seen
from above: k=1 maps local -Y (a cabinet front) to world +X.
"""
from __future__ import annotations

from .expr import Expr
from .geometry import Box, BoxExpr


def _check_turns(k):
    if type(k) is not int or k not in (0, 1, 2, 3):
        raise ValueError("quarter_turns must be 0, 1, 2 or 3")
    return k


def rotate_xy(x, y, k):
    k = _check_turns(k % 4 if type(k) is int else k)
    return ((x, y), (-y, x), (-x, -y), (y, -x))[k]


def place_box(box: BoxExpr, k: int, footprint_w: Expr, footprint_d: Expr,
              position) -> BoxExpr:
    """Rotate a module-local box by k quarter-turns within its footprint
    [0, w] x [0, d], re-anchor the rotated footprint at its minimum corner,
    then translate by ``position`` (three Exprs)."""
    _check_turns(k)
    (ox, oy, oz), (sx, sy, sz) = box.origin, box.size
    w, d = footprint_w, footprint_d
    if k == 0:
        origin, size = (ox, oy), (sx, sy)
    elif k == 1:
        origin, size = (d - oy - sy, ox), (sy, sx)
    elif k == 2:
        origin, size = (w - ox - sx, d - oy - sy), (sx, sy)
    else:
        origin, size = (oy, w - ox - sx), (sy, sx)
    px, py, pz = position
    return BoxExpr((px + origin[0], py + origin[1], pz + oz), (size[0], size[1], sz))


def box_to_local(box: Box, k: int) -> Box:
    """Rotate a world box by -k quarter-turns about the world origin."""
    corners = [rotate_xy(x, y, (4 - _check_turns(k)) % 4)
               for x in (box.lo[0], box.hi[0]) for y in (box.lo[1], box.hi[1])]
    xs, ys = [c[0] for c in corners], [c[1] for c in corners]
    return Box((min(xs), min(ys), box.lo[2]), (max(xs), max(ys), box.hi[2]))


def point_to_world(point, k: int):
    x, y = rotate_xy(point[0], point[1], _check_turns(k))
    return (x, y, point[2])
