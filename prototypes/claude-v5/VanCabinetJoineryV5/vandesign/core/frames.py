"""Coordinate conventions.

Cabinet-local frame (right-handed, millimetres):
    X = width         left outer face X = 0, increasing to the right
    Y = front-to-back door front face Y = 0, increasing toward the back
    Z = height        cabinet base Z = 0

In V5 the cabinet-local frame equals the Fusion world frame (identity
placement).  Vehicle datums, rotations and module placement are NOT
implemented yet - see NOT_IMPLEMENTED.md.
"""

CABINET_LOCAL_FRAME = "cabinet-local:X=width,Y=front-to-back,Z=height,origin=left-front-base"
