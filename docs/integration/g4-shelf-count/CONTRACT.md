# G4 shelf-count contract and recovery decision

Owner-authorized issue #20; branch from develop `a2aba70a7e1824cc823f83ffb2ede7483802b1b7`. Written before mutation implementation. Scope: one new dedicated schema0.2 base@1 fixture, default1200×850×550, ply18/dado6, two doors; shelves1→2→1 only. No G5, general reconciliation, live installation changes or protected-design operations.

## Recovery mechanism

Reconstruct exclusively owned cabinet entities using the existing canonical generator and Fusion adapter. A fresh fixture must opt in at compile time to an ownership receipt. Existing G3 designs without that receipt are refused, never adopted. Preview compares the receipt against current structure, resolves recorded entity identities, checks all user-parameter expressions/values and rejects unmanaged/manual divergence. Before mutation, require passing existing geometry validation and exact cut audit, then recheck the read-only inventory.

Implementation refinement: `ShelfFixtureAdapter` is an opt-in subclass in `cad/fusion/shelf_regeneration.py`. The original G3 adapter and every golden fixture remain unchanged. The small panel allocation wrapper adds immediate tracking; an AST equivalence test checks that its remaining construction exactly matches G3. No existing design receives a receipt through the normal launcher.

Before deleting anything, persist the original spec, parameters and measured inventory in the existing per-design restore journal. Delete only captured owned occurrence references (including their dependent features), then delete unreferenced owned user parameters in dependency order. Require an empty root/timeline and no orphan components before compiling the desired assembly. Do not delete arbitrary timeline ranges or call global Undo. Record newly created occurrence references immediately so partial construction can be cleaned up within the same synchronous call.

On a caught failure, remove only those captured old/new owned entities and rebuild the old canonical assembly. Clear the journal only after original spec/expressions, actual measured body bounds/volumes, topology census and exact cut audit have verified. A failure remains a failed job even if recovery succeeds. Any cleanup, rebuild, API read or recovery verification failure retains a blocking journal; no retry, automatic save, close, discard or journal clearing. A process crash interrupts recovery: the persisted journal blocks future edits and requires investigation; it is NOT an automatic crash-recovery guarantee.

Autodesk documents that deleting the last [Occurrence](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_Occurrence_deleteMe.htm) deletes its Component, and that [UserParameter deletion](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_UserParameter.htm) requires no remaining references. These are API contracts, not live proof of this sequence. Live deletion/orphan cleanup and recovery remain UNKNOWN until separately authorized Fusion tests.

## Identity and limitations

Semantic panel/cut IDs and parameter/schema/generator names remain unchanged. Reconstructed Fusion entity tokens, internal parameter names and timeline ordering may differ; external references are unsupported. A fresh ownership receipt deliberately rejects adoption of pre-existing owner designs. No promise to preserve arbitrary manual features, appearance edits or metadata. Unsafe/unknown topology or ownership causes refusal before deletion. No general multi-document lifecycle operation is introduced.

## Interfaces and checks

CAD-neutral planner beside `width_change.py`; `preview_shelf_count_change` and `update_shelf_count` with integer `new_shelf_count`1or2, through existing job validation/target/allowlist/journal controls. Adapter changes only for ownership capture, owned reconstruction and partial-failure cleanup. Generic CLI `validate`/`submit` reused. No new service, queue or framework.

Offline: deterministic preview, parameter/spec/ID drift, malformed/no-op/out-of-scope input, missing/duplicate/unmanaged entities, blocking journal, target/allowlist refusal, successful1→2→1 and failure/recovery orchestration. Adapter mocks verify deletion boundaries and partial-failure handling, not CAD correctness. Installed-wheel regressions and Python3.10/3.12 CI remain required.

Live proof is separately gated: one new dedicated fixture, actual BRep/probe/interference verification,4/4 owned cuts at2shelves, restored2/2 at1shelf, topology census, controlled mid-mutation failure and refusal without change. No existing designs, runner settings or deployments will be changed without explicit owner approval. No default save/reopen campaign.
