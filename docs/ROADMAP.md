# VanDesign product direction

Present capability and blockers belong in [PROJECT_STATUS.md](../PROJECT_STATUS.md); working rules belong in [AGENTS.md](../AGENTS.md). Work order: A → B1 → E1 → D with E2 → B2 when needed by D → F → G; C when the van is acquired, always before H → H → I. Each item is done when it works in Fusion (and, from Phase H, in the real van).

**Adopted first-product strategy (19 October 2026, [ADR-0002](decisions/ADR-0002-lined-interior-envelope.md)):** van shell → structural timber framework → plywood-lined interior → measured planar design envelope → parametric furniture → CNC panel output → secure installation. VanDesign models the finished lined interior as a few measurable planes and obstructions, not the curved metal shell. Keep the existing core/adapter/Runner; extend, do not replace.

Already proven in live Fusion (2026-10-14 to 10-19): cabinets (base/tall/overhead, width/shelf edits), resizable bed, bed + cabinet composition, guarded cabinet placement with collision refusal, an *unmeasured* development envelope with assumed arches (Issue #51), and an under-bed storage box (Issue #56).

## Phase A — Stabilise the existing furniture system (complete, 19 October 2026)

1. Done: Issue #56 storage box accepted live (452/452) after the PR #58 volume-noise fix.
2. Done (Issue #60): PR #49 adapter regression: offline pre-#49 trace parity for base/tall/overhead/bed; live base checkpoint 1200 → 1210 → 1200.
3. Done (Issue #60, owner-revised scope): combined scene saved and reopened clean with unchanged geometry and affected-body ownership; configured participant-list persistence remains UNKNOWN.

## Phase B — Parametric lined-interior envelope (B1 complete, 26 October 2026; B2 when Phase D needs it)

B1 accepted live for the default flat-ceiling envelope (Issue #61); stepped ceilings and door keep-outs are offline-tested only.

Generalise the Issue #51 test envelope into a measured-envelope spec, in two steps: B1 ([#61](https://github.com/AnyBuzzin/van-design-system/issues/61)) flat planes and keep-outs; B2 angled upper-wall planes, which need non-axis-aligned reference bodies in the adapter. Contents: floor plane, lower walls, angled upper-wall planes (B2), flat or segmented ceiling, front/rear limits, wheel arches and obstructions as boxes, door openings with clearance keep-out volumes, an installation tolerance inset, and mounting points/rails as geometric data only. Editable `Env_*` Fusion parameters; reference-only bodies never enter cut lists. Fit check: every furniture panel corner inside all planes (exact for the convex usable space) and no positive-volume overlap between any panel box and any keep-out box; violations refused before CAD mutation.

**Reference van (owner decision, 19 October 2026; changed 26 October 2026):** until the target van is acquired, build and test every feature against the published VW Crafter CR35 long wheelbase maxi, high roof, load compartment: length 4855 mm at floor level and 4606 mm minimum (use 4606 for full-height furniture), width 1832 mm, 1380 mm between wheel arches (≈226 mm per arch), height 1961 mm; side sliding door 1311 W × 1822 H mm; rear wing doors 1552 W × 1840 H mm. Arch length, height and position remain ASSUMED. The accepted Transit L2H3 fixtures (Issues #51, #56, #61) stay as historical evidence and are not relabelled. A lining-allowance parameter derives the lined interior from the bare load space. Every value stays an editable parameter labelled PUBLISHED-NOMINAL, so retargeting to the acquired van is a data change, not new code.

## Phase E1 — Joinery foundation (current; owner decision: next after B1, before most of Phase D)

Progress: E1.1 rounded-corner panel passed live (Issue #70); E1.2 tab-and-slot coupon with dog-bone relief in progress (Issue #73).

New modules must be born with real joinery rather than retrofitted from butt joints. In order:
1. **2D panel outlines:** a flat panel defined by a profile of lines and arcs (not only an axis-aligned box) in the core and Fusion adapter, verified against real BRep bodies. This is the base for tabs, slots, notches, cut-outs and radiused edges.
2. **Tab-and-slot carcass joints with dog-bone corner relief,** parameterised by tool diameter, fit clearance and measured sheet thickness; applied to the existing cabinet carcass; exact cut ownership and zero interference verified in Fusion.
3. **One hardware connector as cut geometry** (for example Lamello Cabineo or confirmat), with insertion points and exact target bodies.
4. **Physical test pieces:** cut coupons on a CNC router and record measured fit before the joint is used in furniture.

## Phase C — Real vehicle qualification (when the van is acquired)

Phases D–G proceed on the reference van; Phase C must be complete before Phase H. Owner measures the finished lined interior of the acquired van. Enter it as an envelope spec, build bed + cabinet + storage inside it in Fusion, and confirm 3–5 physical tape checks match the model within tolerance. First real fit claim; still no load claim.

## Phase D — Essential furniture library

Only modules a working van needs, in this order: overhead cabinets on angled walls, kitchen base run (worktop, sink/hob cut-outs), drawer unit (one slide type), wardrobe/tall unit, bed variants. Each a parametric module with stable IDs on the common composition and fit check.

## Phase E2 — Materials and joinery completion

Builds on E1 alongside Phase D. Per-panel thickness 5, 10, 12, 15, 18 mm (others only when justified), driven by **measured actual sheet thickness**. CNC-compatible joinery (existing dados, tab-and-slot, dog-bone relief) parameterised by tool diameter, fit clearance and thickness. Validate with physically cut test coupons before use in furniture.

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
