# G4 shelf-count candidate — independent review requested

Issue [#20](https://github.com/AnyBuzzin/van-design-system/issues/20), based on integrated develop `a2aba70a7e1824cc823f83ffb2ede7483802b1b7`. **G4 remains OPEN pending independent acceptance.** Owner-approved [bounded live qualification](live-20261017/README.md) has now completed on reviewed source50c1955:1→2→1, refusal/recovery and exact original-installation restoration observed PASS. The candidate/offline report below is retained as the pre-live checkpoint; its pending-test statements are superseded by the linked live evidence.

## Implementation

The default schema0.2 base@1 cabinet can preview and request shelf_count1→2→1 through the existing Runner job API. All other inputs remain fixed. The preview lists changed parameters, added/removed panels and explicit cut targets. Target identity, allowlist/protection policy and a completely clear restore journal are required for mutation. The operation checks actual baseline geometry and exact cut ownership before deletion, then verifies the reconstructed result. Desired counts are8/9/28 (panels/components/timeline) at1shelf and9/10/35 at2shelves; cuts2/2 and4/4 respectively.

The [recovery contract](CONTRACT.md) was committed as `9564d2a` before mutation code. A fresh fixture must be generated explicitly through `ShelfFixtureAdapter`; normal G3 launchers do not create or adopt ownership receipts. The subclass retains canonical generation, sketch, extrusion and explicit participant assignment. It captures each new occurrence before further construction can fail. The original G3 adapter, canonical maths, archived prototypes, golden fixtures, schema/generator identities and existing public parameter names are unchanged.

Preview reads an ownership receipt and live inventory without moving the timeline. Missing receipt, non-default spec, changed expressions/values, ambiguous/missing/duplicate entities, extra root geometry/parameters, unhealthy/suppressed features, linked/nested occurrences or changed recorded structure cause refusal. Token identities are resolved through Fusion, not compared as historical strings. Pre/post mutation cut audits reuse the existing audited workflow that restores its timeline marker.

The existing per-design journal stores original spec, parameters, body bounds/volume/topology, sketch/model-parameter signatures and document identity before mutation. Caught failures reconstruct only captured owned entities. Verified recovery clears the journal but the job remains FAIL. Failed/unknown recovery leaves a blocking journal. A process crash is not automatically recoverable. Reconstructed entity tokens/internal parameter names can change; arbitrary metadata/appearance edits and external references are outside supported scope. No save/close/discard operation is part of either command.

## Evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Package, ownership inventory and cleanup boundaries | PASS,22 tests | [raw log](evidence/root-tests-v3.log) |
| Runner planning, refusal,1→2→1, partial failure, rollback, unknown recovery, identity drift, journal-write failure | PASS,79 tests across Runner suite | [raw log](evidence/runner-tests-v3.log) |
| Existing G3/core/width/product regression suite | PASS,119 tests; original golden checks unchanged | [raw log](evidence/g3-regression-v3.log) |
| Final job-schema checks | PASS,7 tests | [raw log](evidence/schema-final.log) |
| Isolated installed wheel; source/bundle hashes | PASS | [runtime](evidence/installed-runtime.json), [integrity](evidence/candidate-integrity.json), deployment manifests |
| Real Fusion geometry, groove removal,4/4→2/2 ownership, orphan cleanup and recovery | **UNKNOWN — not executed; owner approval required** | Proposed protocol below |
| Existing live installation/configuration | Unchanged | [read-only configuration identity](evidence/live-config-readonly.json) |

The offline backend and API doubles prove control flow and failure boundaries, **not CAD correctness**. Initial development failures are preserved in [negative outcomes](evidence/development-negative-outcomes.json) and the [original G3 rejection log](evidence/g3-regression-v2.log). The first approach touched protected adapter methods; it was discarded in favor of the opt-in subclass. No golden test was loosened to obtain PASS. The original successful G3 live campaign is reused from [PR21 evidence](../g3-remaining-verification/README.md), not rerun.

Candidate wheel SHA256: `6985f3e7ffcb2ed0a7f01553ca8498a22c6062da9acecacc293ed03ad54346eb`. Local development candidate root: `C:\Users\Buzz\Documents\VanDesign-G4-offline-20261017`. Cabinet bundle: `candidate-bundles\VanCabinetJoineryV5`. Runner source candidate: `candidate-runner\VanDesignRunner` (no config included). Both are staged files only. The original version0.5.0/generator identity is retained; identify this unreleased candidate by commit and hashes, not by version alone. No release claim is made.

Reproduce with a wheel installed into a separate development environment: `python -I tools/check_installed.py`; `python -m unittest discover -s tests -v`; `python -m unittest discover -s automation/tests -v`; and from `prototypes/claude-v5/tests`, `python -m unittest discover -v`. Generate a new nonexistent bundle directory with `python tools/deploy_fusion.py <new-output>`. Generic CLI `validate`/`submit` already supports the new commands. Args are `{"new_shelf_count":2}` or `1`; no expectation override can weaken structural verification.

## Next approval boundary — one disposable live qualification

Jack should independently review the recovery limitations, refusal boundary and candidate source before live execution. Owner approval is required for this bounded protocol:

1. Verify installed paths, active modules, pending queue/journals and all open document identities. Back up the exact installed Runner folder/configuration with hashes. Abort on unexpected pending work. Do not close, modify or save existing documents.
2. Temporarily load the hashed candidate Runner code and point only `g3_script_dir` to the candidate cabinet bundle. Preserve audit/demo paths, protected IDs, queue and historical records. Reload through the established native add-in lifecycle. Restore the exact original code/config if loading fails.
3. Create only `VanDesign-G4-base-shelf-count-20261017` as a new dedicated design. Build default base@1 through `ShelfFixtureAdapter`, validate baseline, then save only this fixture in the Fusion **Default Project root** so the existing target policy has a cloud ID. Temporarily restrict the edit allowlist to that exact new ID. A save approval is needed because existing Runner target checks intentionally refuse unsaved designs.
4. Preview then run1→2→1 once, retaining actual before/after BRep, groove probes/interference, exact cut participants, parameter/spec identities and full ownership/topology inventory. Verify no additional shelf, groove, component or feature remains after restoration. Do not repeat accepted G3 campaigns.
5. On this same dedicated fixture, use a one-shot in-process test fault during partial construction; require a failed job, measured reconstruction of the original state and a cleared journal only after verified recovery. Exercise invalid/no-op/ownership-drift refusal with before/after evidence. No production fault flag or new automation service is introduced. Unverified recovery immediately stops further mutation and preserves the journal.
6. Restore exact original Runner files/configuration, verify backup hashes and report all outcomes in this PR. Do not save test mutations, close documents, clear unresolved journals, merge or release. Leave the dedicated test document/evidence for inspection if a failure occurs.

This is a request for a future bounded test, **not permission already granted**. Integration and G5 remain separate decisions.
