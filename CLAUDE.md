# Claude guidance — VanDesign V5

Start with [AGENTS.md](AGENTS.md), [PROJECT_STATUS.md](PROJECT_STATUS.md), [docs/ROADMAP.md](docs/ROADMAP.md), and [engineering precision/ownership rules](docs/standards/precision-and-ownership.md).

## Current baseline — 2026-10-15

- **Integrated development branch:** `develop` at merge `b799db8a73309a9d47a355ec37c955f5e4dc7850` (PR #14, containing PR #13 and the original stacked development). `main` was deliberately left unchanged.
- **One maintained Python runtime:** `src/vandesign`, installable as a wheel version 0.5.0; historical `prototypes/claude-v5` is preserved as comparison evidence, not the active import root. Existing `DadoShelf` interface remains supported.
- **G2:** real Fusion A–E validation 58/58 each, and correct exclusive left/right dado cut ownership. **G3:** base, tall and overhead variants exist; some F0/overhead F3 test obligations remain open ([issue #4](https://github.com/AnyBuzzin/van-design-system/issues/4)). **G4:** safe width-only update demonstrated (not a complete structural/manual-divergence engine). **G5:** engineering release criteria and cut-list preview outstanding.
- **Proven new runtime:** installed-wheel offline tests and GitHub Python 3.10/3.12 CI passed; targeted real Fusion `base@1` PR14 checkpoint passed 59/59 at original, width edit and restore, correct two-cut ownership and exact eight-body restoration. [Raw evidence](docs/integration/pr14-checkpoint-evidence/live-20261015/FINAL_REVIEW.md).
- **Demonstrations:** first interior, configurable bed/kitchen and simplified vehicle/wheel-arch constraints have real Fusion evidence, but **are not** measured vehicle fit, production engineering or manufacturing clearance.
- **G0:** the exact V4 source/manifest actually executed during the original test remains UNVERIFIED ([issue #1](https://github.com/AnyBuzzin/van-design-system/issues/1)).
- **Runner:** the last inspected live Fusion installation used historical G3/demo paths. The code supports reviewed wheel-built bundles, but **do not silently update a live pinned runner**; any config switch/reload needs safeguards and owner approval.

## Next task policy

The authoritative next work is in PROJECT_STATUS.md and the V5 gate roadmap. The G3 C0–C5 implementation was already completed; **do not rerun that old implementation task** or start work from `feature/v5-g3-cabinet-variants`.

The [2026-10-14 complete G3 handover](docs/ai/CLAUDE_G3_IMPLEMENTATION_HANDOVER_2026-10-14.md) and [earlier proposal handover](docs/ai/CLAUDE_V5_G3_HANDOVER_2026-10-14.md) are immutable historical decisions/results, **not live instructions**. Retain frozen source, verified geometry, `Cab_*` expressions and historical evidence. Apply the milestone-first review, safety and evidence rules in AGENTS.md.
