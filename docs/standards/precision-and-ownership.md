# Geometry precision and ownership

Canonical input lengths: millimetres. Fusion API internal lengths: centimetres. Conversions occur only at the adapter boundary.

Each component has a stable ID, role, local coordinate frame and parametric specification.

Boolean cut operations MUST resolve a single explicit permitted target body (or an explicitly enumerated set), set participantBodies appropriately, and verify only intended body volume changed. Fail if the target is absent or ambiguous.

Dimensional correctness of a sketch does not imply that the resulting BRep extrusion is correct. Always compare solid-body dimensions, groove emptiness, shelf insertion and interference.

Joint allowances distinguish nominal thickness, measured stock thickness, end clearance, groove clearance, cutter/tool allowances and assembly tolerances.

Any missing measurement, failed API call or skipped verification must produce UNKNOWN or FAIL. It cannot produce PASS.

Real-world vans require measured vehicle geometry, datums and engineering margins; nominal vehicle dimensions alone are not a fitment guarantee.
