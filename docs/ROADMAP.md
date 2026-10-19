# VanDesign product direction

Present capability and blockers belong in [PROJECT_STATUS.md](../PROJECT_STATUS.md); working rules belong in [AGENTS.md](../AGENTS.md). Work top to bottom; each item is done when it works in Fusion (and, from Phase H, in the real van).

**Adopted first-product strategy (19 October 2026, [ADR-0002](decisions/ADR-0002-lined-interior-envelope.md)):** van shell → structural timber framework → plywood-lined interior → measured planar design envelope → parametric furniture → CNC panel output → secure installation. VanDesign models the finished lined interior as a few measurable planes and obstructions, not the curved metal shell. Keep the existing core/adapter/Runner; extend, do not replace.

Already proven in live Fusion (2026-10-14 to 10-19): cabinets (base/tall/overhead, width/shelf edits), resizable bed, bed + cabinet composition, guarded cabinet placement with collision refusal, an *unmeasured* development envelope with assumed arches (Issue #51), and an under-bed storage box (Issue #56).

## Phase A — Stabilise the existing furniture system (current)

1. Done: Issue #56 storage box accepted live (452/452) after the PR #58 volume-noise fix.
2. Issue #60: regression-check the shared Fusion adapter change from PR #49 on base/tall/overhead cabinets (offline oracle merged in PR #63; one live base checkpoint).
3. Issue #60: combined scene save → reopen → re-measure unchanged.

Done when every existing module resizes, moves, restores and validates in Fusion and the combined design survives save/reopen.

## Phase B — Parametric lined-interior envelope

Generalise the Issue #51 test envelope into a measured-envelope spec, in two steps: B1 ([#61](https://github.com/AnyBuzzin/van-design-system/issues/61)) flat planes and keep-outs; B2 angled upper-wall planes, which need non-axis-aligned reference bodies in the adapter. Contents: floor plane, lower walls, angled upper-wall planes (B2), flat or segmented ceiling, front/rear limits, wheel arches and obstructions as boxes, door openings with clearance keep-out volumes, an installation tolerance inset, and mounting points/rails as geometric data only. Editable `Env_*` Fusion parameters; reference-only bodies never enter cut lists. Fit check: every furniture panel corner inside all planes (exact for the convex usable space) and no positive-volume overlap between any panel box and any keep-out box; violations refused before CAD mutation.

## Phase C — Real vehicle qualification

Owner measures the finished lined interior of the current van. Enter it as an envelope spec, build bed + cabinet + storage inside it in Fusion, and confirm 3–5 physical tape checks match the model within tolerance. First real fit claim; still no load claim.

## Phase D — Essential furniture library

Only modules a working van needs, in this order: overhead cabinets on angled walls, kitchen base run (worktop, sink/hob cut-outs), drawer unit (one slide type), wardrobe/tall unit, bed variants. Each a parametric module with stable IDs on the common composition and fit check.

## Phase E — Materials and interlocking joinery

Per-panel thickness 5, 10, 12, 15, 18 mm (others only when justified), driven by **measured actual sheet thickness**. CNC-compatible joinery (existing dados, tab-and-slot, dog-bone relief) parameterised by tool diameter, fit clearance and thickness. Validate with physically cut test coupons before use in furniture.

## Phase F — Manufacturing output

Per-panel flat geometry (DXF) with stable part IDs, outer contour, thickness, joinery features by depth/layer, orientation/grain where needed, plus cut list and quantities. Round-trip check: re-read exports and compare with Fusion BRep. This is manufacturing geometry, **not toolpaths**; CAM happens downstream (CNC shop software or a separately licensed tool). Do not assume Fusion Personal CAM.

## Phase G — Complete interior workflow

One input (envelope + chosen modules + sizes/positions) → Runner build → validation report → panel exports. JSON/CLI first. Automated layout suggestions only after geometry, fit checks and exports are trustworthy.

## Phase H — Physical manufacturing validation

Cut, assemble and install one complete arrangement in the real van. Measure panels against exports, joinery fit, assembly sequence and time, installed clearances. Each heavy item has a documented load path into vehicle structure, reviewed by a competent person; mounting capacities come from tests or calculation, never assumption.

## Phase I — First usable release

Measure lined van → enter measurements → select furniture → customise → validate → generate panels → CNC preparation → assemble and install. Accepted when:

1. A completed measurement sheet produces a Fusion envelope matching every entered value (±0.1 mm).
2. Bed, kitchen base, overhead cabinet and storage are configurable; envelope and collision violations are refused before mutation.
3. Every furniture panel exports as DXF + cut list with stable IDs; reference geometry excluded; round-trip check PASS.
4. Phase H arrangement installed: panels within ±0.5 mm of export, joinery assembles without re-cutting, installed clearances within ±3 mm of the model.
5. Full design saves and reopens unchanged; owner approves the release to `main`.

## Later (not blockers)

Repeatable framing/lining templates per van model, generated battens and lining panels, nesting/cutting optimisation, hardware library and costing, more modules, layout automation.

Load-bearing claims, seat and seat-belt mounting, and vehicle-registration compliance are outside the software's claims; seats stay on dedicated tested mounts.
