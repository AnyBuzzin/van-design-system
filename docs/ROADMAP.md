# VanDesign product direction

Present capability and blockers belong in [PROJECT_STATUS.md](../PROJECT_STATUS.md); working rules belong in [AGENTS.md](../AGENTS.md). Milestones run in dependency order; each is done when it works in Fusion and, from M3, on real plywood.

**Strategy ([ADR-0002](decisions/ADR-0002-lined-interior-envelope.md)):** van shell → structural timber framework → plywood-lined interior → measured planar envelope → configurable furniture → verified joinery → CNC panel output → secure installation. Keep the core/adapter/Runner; extend, do not replace.

**Reference van:** until the target van is acquired, build and test against the published VW Crafter CR35 long wheelbase maxi, high roof: load length 4855 mm at floor level / 4606 mm minimum (use 4606 for full-height furniture), width 1832 mm, 1380 mm between arches, height 1961 mm; side door 1311 × 1822 mm, rear doors 1552 × 1840 mm. Arch length, height and position stay ASSUMED. All vehicle values are editable data, so retargeting is a data change. The Transit L2H3 fixtures (#51, #56, #61) remain historical evidence.

**Proven live (14–26 October 2026):** cabinets (base/tall/overhead, width and shelf edits), resizable bed, bed + cabinet composition with collision refusal, under-bed storage box, lined envelope B1 (flat ceiling), E1.1 rounded panel. Phase A (stabilisation, #60) and B1 (#61) are complete.

## M1 — Platform consolidation (bounded qualification complete)

Removes the bottlenecks found in the October review so new modules become mostly data.
1. **Manufacturing output from the core:** panel profiles (lines/arcs, through-cuts, pockets, holes), automatic dog-bone relief, per-panel DXF + cut list, independently re-read (PR #76).
2. **Arrangements:** any number of instances, per-instance parameter namespaces, positions, quarter-turns, cross-instance collision and B1 fit; verification in each module's frame (PR #77).
3. **One generic Runner entry point** (`BuildArrangement`): build any arrangement spec in a fresh owned document and verify it generically (bodies, cuts, probes, interference, census, exact restore); replaces per-feature entry points and hard-coded check counts. Fix misleading `runner_lost` heartbeats. One owner deployment approval.
4. **One tolerance policy:** shared readback comparator; offline fakes inject realistic float noise; Python 3.14 (Fusion's interpreter) in CI.

Accepted on installed Runner `7392a67`: the shipped four-instance Crafter request passed 684 live checks, width edit/restoration and unsafe-move refusal; 24 panel DXFs / 28 loops independently re-read against core profiles. Only the successful unsaved fixture was closed; the full four-document baseline was preserved. [Results](https://github.com/AnyBuzzin/van-design-system/issues/78#issuecomment-6418911961) / [Independent acceptance](https://github.com/AnyBuzzin/van-design-system/issues/78#issuecomment-6418934844). This is bounded evidence, not qualification of arbitrary arrangements, saved persistence, physical CNC assembly or vehicle fit; the original failed fixture remains protected.

## M2 — Joinery foundation (was E1)

E1.1 passed live (#70). Joinery is driven by the profile model: a reusable tab-and-slot generator with automatic dog-bones (including tab roots) from tool diameter, clearance and **measured** sheet thickness (#85); profile panels built and verified in Fusion (#84); then one hardware connector (Lamello Cabineo or confirmat) as cut geometry. Fit is proven virtually: exact clearance and zero assembled overlap offline, measured BRep bodies in Fusion, and DXF re-read against the core.

## M3 — First manufacturable module

A kitchen base cabinet run in the reference van: arrangement + tab-and-slot carcass + DXF pack, built and verified live in Fusion (bodies, joints, clearances, interference). The DXF pack is checked by importing it into CAM or nesting software. This is the virtual end-to-end demonstration, with no physical cut.

## M4 — Furniture library and materials (was D + E2, B2)

Only what a working van needs: overhead cabinets (with B2 angled upper-wall planes), drawer unit (one slide type), wardrobe/tall unit, bed variants. Per-panel thickness 5/10/12/15/18 mm (others only when justified), grain direction, hardware library.

## M5 — Layout workflow (was G)

Arrangement JSON in → build and verify → DXF pack and cut list out. Nesting and CAM use existing tools (deepnest or MapBoards nesting; VCarve or the CNC shop's CAM), not built here.

## M6 — Real vehicle (was C; when the van is acquired, always before M7)

Measure the finished lined interior; retarget the envelope data; build the arrangement and confirm 3–5 tape checks within tolerance. First real fit claim.

## M7 — Physical validation (was H)

**Owner decision (26 October 2026): no physical CNC cutting until the software is complete; all physical validation happens here.** Start with a joint test coupon (measured sheet, actual bit) before the full arrangement. Joinery fit on real plywood stays unproven until this point; conservative clearances are the mitigation meanwhile.

Cut, assemble and install one complete arrangement in the van. Measure panels against DXF, joinery fit, assembly sequence and installed clearances. Each heavy item has a documented load path into vehicle structure, reviewed by a competent person; capacities come from tests or calculation.

## M8 — First usable release (was I)

Accepted when:
1. A completed measurement sheet produces a Fusion envelope matching every entered value (±0.1 mm).
2. Bed, kitchen base, overhead cabinet and storage are configurable; envelope and collision violations are refused before mutation.
3. Every furniture panel exports as DXF + cut list with stable IDs; reference geometry excluded; round-trip check PASS.
4. The M7 arrangement is installed: panels within ±0.5 mm of export, joinery assembles without re-cutting, installed clearances within ±3 mm of the model.
5. The full design saves and reopens unchanged; the owner approves the release to `main`.

## Owner gates (outside software)

Fusion commercial licence before selling designs or kits; structural review of fixings before heavy items are installed; repository privacy and licence; seats and seat-belt mounts stay on dedicated tested hardware.

## Later (not blockers)

Per-model framing and lining templates, generated battens and lining panels, nesting optimisation, costing, more modules, layout automation.
