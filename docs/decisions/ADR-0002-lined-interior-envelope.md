# ADR-0002: Design to a measured plywood-lined interior

Status: Accepted by the owner as the first-product strategy, 2026-10-19

## Decision
Furniture is designed for the finished, plywood-lined interior, not the bare metal shell. A timber framework (currently 2×1 battens on M8 rivnuts into vehicle structure) gives straight reference surfaces; flat lining covers most of the interior. VanDesign models that lined space as a small number of measured planes plus obstructions.

## Envelope model (CAD-neutral core)
- **Frame:** keep the Issue #51 convention. Origin at the left-front corner of the finished floor; X across the van, Y along it, Z up from the finished floor. Measure distances from these lined surfaces, never from gravity, so a parked van need not be level.
- **Usable space:** the intersection of half-spaces `n·p ≤ d`: floor, left/right lower walls, optional angled upper-wall planes (start height and inset at ceiling), flat or segmented ceiling, front/rear limits.
- **Keep-outs:** axis-aligned boxes for wheel arches, obstructions, service cavities and door-opening clearance volumes.
- **Mounting points/rails:** position, surface normal and type only. Capacity is recorded as unqualified until tested or calculated.
- **Tolerance:** one installation inset applied to all planes.
- **Fit check:** furniture panels stay axis-aligned boxes. A panel fits when all 8 corners satisfy every plane (exact for convex envelopes) and it misses every keep-out. Refuse before any CAD mutation.

## Fusion representation
`Env_*` user parameters drive reference-only bodies, as the Issue #51 guides and arches already do. They never enter cut lists or exports.

## Engineering constraints
- Lining and battens locate furniture; they are not assumed to carry crash loads. Heavy items need load paths into vehicle structure, reinforced points or rails. M8 rivnut capacity is unqualified.
- Use 15 mm only where needed (mounting zones and strips). Thinner lining elsewhere protects payload.
- Allow access to structural fixings, wiring and plumbing; control condensation behind the lining.
- Seats and seat-belt mountings are out of scope.

## Consequences
Removes shell scanning, surface reconstruction and curved-panel generation from the first product. What remains: planar envelope plus keep-out checks, measured tolerances, mounting data, and separately qualified fastening. Extend `src/vandesign/modules/test_envelope.py` and the existing fit guard; no new architecture.
