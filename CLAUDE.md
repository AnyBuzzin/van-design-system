# Claude guidance — VanDesign V5

Follow [AGENTS.md](AGENTS.md), [PROJECT_STATUS.md](PROJECT_STATUS.md), [docs/ROADMAP.md](docs/ROADMAP.md), and the **[complete, approved G3 implementation handover](docs/ai/CLAUDE_G3_IMPLEMENTATION_HANDOVER_2026-10-14.md)**. The [earlier G3 handover](docs/ai/CLAUDE_V5_G3_HANDOVER_2026-10-14.md) is historical context.

**Current factual state (2026-10-14):**
- G2 Fusion smoke test **was executed by the user** in Fusion v2705.1.30: A–E all 58/58 PASS, plus separate real-Fusion API audit confirming both dado cuts target exactly their own side-panel body and exclude the shelf. See [the protocol](prototypes/claude-v5/FUSION_TEST_PROTOCOL.md) and [audit](prototypes/claude-v5/docs/test-results/cut_audit_20261014_174320_047406.txt). Do not falsely call Fusion untested.
- These results verify only the observed fixture, not manufacturing suitability or arbitrary variants.
- The next gate **G3 is three cabinet variants** with one generator. **G4** is safe incremental structural changes and regeneration (not started).
- Work on `feature/v5-g3-cabinet-variants`, [issue #4](https://github.com/AnyBuzzin/van-design-system/issues/4). Keep G2 PR #3 draft/unmerged and the V4 archive untouched.
- Pure Python module logic must not import `adsk`; every subtractive Fusion feature must specify exact `participantBodies`; validation must fail closed. Keep `Cab_*` expressions stable for the existing base fixture.
- The V5 prototype package under `prototypes/claude-v5/` is not integrated into `src/vandesign`; propose a safe migration rather than duplicating business formulas.

**G3 proposal v2 is reviewed and conditionally approved. Begin implementation at C0 and continue C1–C5 without requesting another architecture approval for each step**, maintaining green tests. Protect byte-identical G2 geometry, 0.1 compatibility, real G2 evidence, and fail-closed validation. Deliver the completed implementation + tests + separate user-run Fusion protocol for review. G3 remains NOT FUSION-VERIFIED until the user executes those tests.
