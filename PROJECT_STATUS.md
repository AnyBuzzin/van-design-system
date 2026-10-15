# Project status

Updated: 2026-10-14. Development branch: `feature/v5-g3-cabinet-variants`.

Product demonstration update (2026-10-15): autonomous interior save/reopen verified
on the dedicated demo; configurable rear-bed dimensions and kitchen placement
demonstrated in real Fusion with one successful layout and one preflight-refused
overlap. See [scope, evidence and remaining checks](automation/evidence/configurable-layouts/STATUS.md).
This product milestone does not close the historical engineering gates below.

Vehicle usable-space demonstration (2026-10-15): configurable envelope and wheel
arches, structural/cabinet intrusion refusal and measured aisle check demonstrated
in Fusion. Prior configured-demo reopen PASS; focused CRLF fix tracked in issue #11.
See [actual evidence and limitations](automation/evidence/vehicle-usable-space/STATUS.md).

| Milestone | Status | Evidence / limitation |
| --- | --- | --- |
| Working V4 joinery | User-verified in Fusion | Golden exact local `.py`/`.manifest` provenance still unresolved |
| G0 — preserve exact V4 source | **OPEN** | [Issue #1](https://github.com/AnyBuzzin/van-design-system/issues/1) |
| G1 — CAD-neutral domain core | **PARTIAL** | 30/30 initial offline tests rerun successfully; 31-test expanded prototype and separate foundation CI passed; duplicated prototype/foundation packages not reconciled |
| G2 — Fusion adapter smoke-test | **PASS for verified fixture** | Fusion v2705.1.30, scenarios A–E **58/58 PASS each**, explicit two-cut participant audit **PASS**; [Issue #2 CLOSED](https://github.com/AnyBuzzin/van-design-system/issues/2) |
| G3 — base/tall/overhead variants | **OPEN / NEXT** | [Issue #4](https://github.com/AnyBuzzin/van-design-system/issues/4); no variant built or tested in Fusion yet |
| G4 — structural change engine | **NOT STARTED** | Incremental regeneration, manual override conflicts and ownership-safe updates not implemented |
| G5 — release candidate | **NOT STARTED** | No approved manufacturing export/CAM release |

G2 test details: [FUSION_TEST_PROTOCOL.md](prototypes/claude-v5/FUSION_TEST_PROTOCOL.md), [real cut audit](prototypes/claude-v5/docs/test-results/cut_audit_20261014_174320_047406.txt). The original JSON reports are not yet archived in-repo; user-run save/reopen action is based on user workflow and `measure` report evidence.

## Immediate next steps

1. Review [G3 Claude handover](docs/ai/CLAUDE_V5_G3_HANDOVER_2026-10-14.md) and issue #4; confirm the variant design proposal.
2. Implement G3 on `feature/v5-g3-cabinet-variants` without changing verified V5 default behavior.
3. Offline tests, then one *new empty Fusion design per variant*, validation and save/reopen reports before declaring G3 PASS.
4. Reconcile the isolated V5 prototype with `src/vandesign` through a separate reviewed migration plan; keep G2 PR #3 in draft until the integration decision.
5. Still obtain exact V4 proven file hashes for G0.

**Tests only count when performed and evidenced. No manufacturing approval is implied.**
