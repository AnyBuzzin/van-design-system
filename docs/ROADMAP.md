# Roadmap and stage gates

## Version 5 delivery gates (authoritative V5 numbering)

The earlier starter roadmap accidentally used different G3/G4 labels. For **V5**, use the detailed `VanDesign_V5_System_Architecture` section 12 and [G3 Claude handover](ai/CLAUDE_V5_G3_HANDOVER_2026-10-14.md):

| Gate | Objective | State |
| --- | --- | --- |
| G0 — V4 exact baseline | Preserve hash/manifest/Fusion-tested final source | **Open:** provenance issue #1 |
| G1 — CAD-neutral domain core | Typed units, frames, specs, panels, IDs, expressions, tests | **Partial:** prototype exists; integration pending |
| G2 — Fusion adapter | Parametric panels, BRep checks, explicit cut participants | **Verified on smoke-test fixture:** A–E all PASS 58/58 and separate cut audit PASS; issue #2 closed |
| G3 — Three cabinet variants | Base, tall and overhead cabinet from **one** core | **Next, open:** issue #4; needs real Fusion verification |
| G4 — Change engine | Scalar/structural changes, owned IDs, divergence detection, preview and safe updates | Not started |
| G5 — Release candidate | Traceable reports/cut-list preview and formal release criteria | Not started |

**Scope warning:** G2 smoke-test verification is NOT manufacturing qualification or a general guarantee for other dimensions and assemblies. Exact V4 final-source provenance is unresolved.

## Later product development (not the V5 gate numbers)

- **V6 — furniture library:** beds, drawers, worktops, partitions using stable interfaces.
- **V7 — vehicle integration:** measured envelopes, datums, mounts, tolerances and access/collision volumes.
- **V8 — layout intelligence:** AI-proposed constrained designs reviewed by humans.
- **V9 — manufacturing pipeline:** approved BOM/cut lists, nesting, machining exports and CAM interfaces.
- **V10 — production orchestration:** controlled jobs, revisions and as-built evidence.

## Numbering reconciliation

The old starter roadmap used “G3 Change management / G4 Furniture library / G5 Vehicle / G6 Manufacturing and AI”, which conflicts with the detailed **V5 architecture gates**. That older coarse categorization is superseded **for V5 gate tracking only**; the broad long-term capabilities remain on the later product roadmap. See [Claude G3 handover](ai/CLAUDE_V5_G3_HANDOVER_2026-10-14.md), [G3 issue #4](https://github.com/AnyBuzzin/van-design-system/issues/4), and [G2 evidence](../prototypes/claude-v5/FUSION_TEST_PROTOCOL.md).
