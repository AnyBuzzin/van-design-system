# VanDesign — outcome-based roadmap

**Current accepted baseline:** [PROJECT_STATUS.md](../PROJECT_STATUS.md). **Live task and delegated authority:** [owner plan / Issue #36](https://github.com/AnyBuzzin/van-design-system/issues/36). Keep this page about next capabilities; source of truth for present status is the single short status page.

## Verified foundations — preserved, not repeated

- **V5 G1–G5:** one Python runtime and Fusion adapter; base/tall/overhead cabinet family; explicit owned dado cuts, bounded structural edits, deterministic nominal panel previews and accepted engineering candidate. Historical live evidence remains at [G3](https://github.com/AnyBuzzin/van-design-system/issues/4), [G4](https://github.com/AnyBuzzin/van-design-system/pull/22), [G5](https://github.com/AnyBuzzin/van-design-system/pull/25). **G0 exact tested V4 source is still open** ([issue #1](https://github.com/AnyBuzzin/van-design-system/issues/1)). Nothing is manufacturing-qualified.
- **V6.1:** accepted independent three-panel bed [offline](https://github.com/AnyBuzzin/van-design-system/pull/28) and seven-state [live Fusion geometry/edit/restore qualification](https://github.com/AnyBuzzin/van-design-system/pull/30). Nominal 18 mm plywood; structural strength not qualified.
- **V6.2:** accepted conservative, fixed-pair **CAD-neutral** placement/collision refusal [PR #32](https://github.com/AnyBuzzin/van-design-system/pull/32).
- **V6.3:** accepted fixed-pair **symbolic offline composition**, 11 panels/2 owned cabinet dados and preserved source expressions [PR #35](https://github.com/AnyBuzzin/van-design-system/pull/35). **No live combined Fusion model has been measured.**

## Near-term deliverables, ordered by visible utility

1. **First reusable combined Fusion model.** Prepare/review bounded safe helper offline, establish a clean *trusted* current protected-document baseline under existing activation requirements, then execute **one new unsaved bed + cabinet** build when enabled. Verify 11 actual BRep bodies, net post-dado volumes, precise two cabinet cut targets, bed contacts and 100 mm nominal X gap. No repeated old cabinet campaigns or unreviewed Runner changes.
2. **Combined parametric editing.** After baseline qualification, make a *separate* minimal width/position edit+restoration demonstration with collision revalidation and actual BRep checks. Later edits may invalidate the original offline layout; do not claim persistent automatic reconciliation.
3. **Measured vehicle layout.** Confirm the owner's actual vehicle identity and dimensions, including apertures/arch intrusions/access. Place qualified furniture in a measured van envelope, not the historical simplified box.
4. **One useful storage component.** A basic drawer or storage unit is the next proposed furniture feature; include independent panel identity, joinery/collision and nominal cut previews. Confirm bounded scope before implementation; no generic new framework.
5. **Plywood thickness variants.** Support owner-requested 5, 10, 12, 15 and 18 mm options where appropriate, including mixed thicknesses, dimensional tolerances and valid joinery; do not equate nominal fit with strength.
6. **Panel-outline/CNC readiness.** Export individual deterministic panel contours, then validate tool diameters, fit allowances, nesting, joints, fasteners, anchoring and physical assembly under separate qualification.

**Longer-term:** V7 measured vehicle integration; V8 constrained AI layout proposals; V9 CNC/manufacturing pipeline; V10 production/workflow traceability. Advance only with evidence; no manufacturing, vehicle fit, load-bearing or road-legal claim yet.

## How to advance

Reuse the existing Python core, Fusion adapter and Runner. Make **one small reviewable milestone at a time** with focused test evidence, preserve negative outcomes, avoid duplicate status PRs and do not pivot to extra orchestration or architecture. Offline work continues under [Issue #36](https://github.com/AnyBuzzin/van-design-system/issues/36); delegated merges and disposable live Fusion work wait until their existing activation requirements are verified. Protect unsaved G4/bed fixtures and keep historical tab/capacity uncertainty, [GitHub guardrails](https://github.com/AnyBuzzin/van-design-system/issues/16), provenance and published-ID exposure visible.
