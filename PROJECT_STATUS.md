# VanDesign — current project status

**Verified integration baseline: 18 October 2026 — develop at 6f942c39b51a6e1b596c67316d21a783b5169ce4.** Main remains separate; no production or CNC/manufacturing release. This is the short **current** status; [Issue #36](https://github.com/AnyBuzzin/van-design-system/issues/36) has the owner's latest work direction and activation requirements. Prior milestone evidence remains in its original issues, PRs, and integration folders.

## What actually works

| Capability | Qualification |
| --- | --- |
| **V5 cabinets** — base, tall, overhead, editable Fusion parameters and exact side-panel dado ownership | Bounded real-Fusion acceptance (G2–G5). [G3](https://github.com/AnyBuzzin/van-design-system/issues/4), [G4](https://github.com/AnyBuzzin/van-design-system/pull/22), [G5](https://github.com/AnyBuzzin/van-design-system/pull/25) |
| **V6.1 standalone 3-panel bed** — 1400 × 1900 × 700 mm finished deck top, nominal 18 mm | [Offline implementation](https://github.com/AnyBuzzin/van-design-system/pull/28); [seven-state real-Fusion geometry/edit/restore PASS](https://github.com/AnyBuzzin/van-design-system/pull/30). Persistence, load and anchoring unqualified |
| **V6.2 layout** — one bed and one base cabinet, independent XYZ placement, conservative collision refusal | [Accepted OFFLINE](https://github.com/AnyBuzzin/van-design-system/pull/32); not a live Fusion assembly |
| **V6.3 symbolic composition** — one 11-panel assembly definition with 2 explicitly owned cabinet dado operations | [Accepted OFFLINE, PR #35 merged](https://github.com/AnyBuzzin/van-design-system/pull/35); 252 installed/offline checks and Python 3.10/3.12 CI reported PASS. The **combined assembly has NOT been built/measured in Fusion** |
| **Historical fixed interior demonstrations** | Simplified bed/kitchen/van envelopes were tested in Fusion, but are **not** qualification of the reusable V6.3 composition or measured vehicle fit |

The maintained runtime is **src/vandesign**; archived prototype and V4 sources are historical. Fusion runs through the existing adapter and Runner, with measured BRep verification for specifically tested fixtures. No CNC-ready contours, qualified furniture strength, measured vehicle fit or commercial manufacturing claim.

## Active work and next useful outcome

1. **Now:** reconcile stale instructions in one reviewable documentation PR; retain old evidence.
2. **In parallel, OFFLINE:** Astra prepares the bounded, source-pinned combined bed/cabinet test helper; Jack independently reviews. Use existing architecture. See [owner plan](https://github.com/AnyBuzzin/van-design-system/issues/36) and [combined-test proposal](https://github.com/AnyBuzzin/van-design-system/issues/34#issuecomment-6244685316).
3. **Next visible result:** one fresh unsaved Fusion document containing the default bed at (0,0,0) and base cabinet at (1500,0,0): **11 measured BRep panel solids, 2 correctly targeted cabinet dados, 100 mm nominal X gap**. Then, as a *separate* focused increment, test combined edits/restoration. Neither step is a qualified live PASS yet.
4. **After that:** use confirmed vehicle identity and measurements; add useful storage, nominated material thicknesses (5/10/12/15/18 mm), and ultimately panel-outline exports. [Roadmap](docs/ROADMAP.md).

## Current blockers and boundaries

- **GitHub:** [Issue #16](https://github.com/AnyBuzzin/van-design-system/issues/16) still open. Both develop and main are unprotected; no rulesets were enabled at the latest check. Agents share the AnyBuzzin GitHub login, so their role labels do not constitute independently enforceable GitHub approvals. **Autonomous merges to develop remain inactive until the requirements in Issue #36 are met and evidenced.**
- **Live Fusion:** the current complete protected open-document/dirty/read-only/capacity baseline has not been verified in this session. **No live Fusion/API/socket operation is yet authorised under the staged activation policy.** Preserve both dirty G4 fixtures and the unsaved bed; no close/save/discard or Runner change. Historical six→three tab and editable-capacity discrepancies remain **UNKNOWN**, not assumed solved by a future clean baseline.
- **Other open history:** [G0 exact V4 source provenance](https://github.com/AnyBuzzin/van-design-system/issues/1) unresolved; historical public cloud document IDs remain exposed in old GitHub commits. No history rewrite authorised. Repository visibility and commercial Fusion licensing require business decisions, not new CAD architecture.
- **Limits:** correct parametric geometry or offline arithmetic is **not** manufacturing suitability. Combined live BRep, cut participation, persistence, access, loads, mounting, vehicle fit and CNC remain **UNKNOWN / NOT RUN** for the new composition.

**Working roles:** Astra implements/tests; Jack checks evidence; Vision coordinates; Jill sets technical direction. Keep one primary implementation PR and proportionate independent review. Report PASS/FAIL/UNKNOWN and a short next action; preserve raw negative evidence without copying reports across documents. [Operating instructions](AGENTS.md).
