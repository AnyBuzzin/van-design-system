# VanDesign current status

**19 October 2026.** Adopted strategy: design to a measured plywood-lined interior ([ADR-0002](docs/decisions/ADR-0002-lined-interior-envelope.md)). `main` is unchanged. Rules: [AGENTS.md](AGENTS.md). Next work: [ROADMAP.md](docs/ROADMAP.md) Phase A.

## Works today

| Capability | Where it was proven |
| --- | --- |
| Base, tall and overhead cabinets; width and shelf-count edits; shelves sit in side-panel grooves | Live Fusion: [G3](https://github.com/AnyBuzzin/van-design-system/issues/4), [G4](https://github.com/AnyBuzzin/van-design-system/pull/22), [G5](https://github.com/AnyBuzzin/van-design-system/pull/25) |
| Three-panel bed, resizable in width, length and height | Live Fusion: [PR #30](https://github.com/AnyBuzzin/van-design-system/pull/30) |
| Bed + cabinet: 11 solids, exact two-side dado ownership, zero interference; both widths edit/restore; test closes unsaved with original document baseline preserved | Live Fusion: 95/95 checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/43#issuecomment-6255609683), [independent acceptance](https://github.com/AnyBuzzin/van-design-system/pull/45#pullrequestreview-5565186671) |
| Cabinet placement (1500,0) to (1600,100) and back: doors follow, cuts/volumes/interference verified; overlapping (100,100) refused without mutation; both existing documents preserved | Live Fusion: 140/140 stage checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/46#issuecomment-6256189001), [independent acceptance](https://github.com/AnyBuzzin/van-design-system/pull/49) |
| Bed + cabinet in an UNMEASURED Transit test envelope with assumed wheel arches; 382 mm deck/arch clearance, 634 mm nominal right strip; unsafe move refused unchanged | Live Fusion: 176/176 checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/51#issuecomment-6257218503); four existing documents preserved |
| Nominal cut lists (CSV/JSON) | Offline; not CNC toolpaths |

## Now

Phase A. Issue [#56](https://github.com/AnyBuzzin/van-design-system/issues/56) storage box: offline merged ([PR #57](https://github.com/AnyBuzzin/van-design-system/pull/57)). The live run passed 339/339 stage checks but FAILED exact restoration on 2.65e-8 mm³ volume readback noise; fix in draft [PR #58](https://github.com/AnyBuzzin/van-design-system/pull/58). Redeploy and live rerun need owner approval. The Issue #51 envelope ([accepted](https://github.com/AnyBuzzin/van-design-system/issues/51#issuecomment-6257222265)) remains an unmeasured development fixture, not real vehicle fit.

## Owner to-do

- Measure the finished lined interior of the current van once lining is complete (ROADMAP Phase C).
- Decide whether the repository should be private.
- Check which Fusion licence is needed for commercial use.

## Not yet proven

General signed-coordinate/zero-crossing placement, combined save/reopen, measured vehicle fit, loads and anchoring, CNC output. The exact V4 source file ([#1](https://github.com/AnyBuzzin/van-design-system/issues/1)) is unknown and blocks nothing.
