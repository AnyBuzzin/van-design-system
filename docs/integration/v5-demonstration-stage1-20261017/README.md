# V5 hands-on demonstration — stage 1

**Subsequent owner-approved stage:** [G4 demonstration completed on 18 October](g4-stage-20261018/README.md). The stage-one observations and stop boundary below remain preserved as recorded; the new report documents the separate approval and execution.

Astra — developer verification for Jack's independent assessment. Validation only, from accepted develop `4c82a0ae3cf1e142c7d299e446629eb53d50864b`; no production code changes, new milestone, merge, release or V6. Owner approved backups, temporary Runner changes, one new project and three fixture saves, with an explicit stop before a new G4 fixture. Live work crossed midnight 17–18 October 2026 (Europe/Dublin); approved names retain 20261017.

## Evidence matrix

| Capability | Expected and observed | Result | Evidence |
|---|---|---|---|
| Source/deployment preflight | Reviewed installed G5 wheel matches current runtime; generated bundle verified. Original Runner lacks structural commands. | PASS | [Source identities](source-preflight.json), [temporary files](temporary-deployment.json) |
| New isolated project | Unique `VanDesign-V5-Demonstration-20261017-01` created empty; exactly three new fixture saves, each version 1. | PASS | [Creation](project-created.json), [final document inventory](stage1-final-documents.json) |
| Base generation | 1200×850×550 mm; 1 shelf, 2 doors, 8 panels; 59/59 actual checks and 2/2 correct cut participants. | PASS | [Baseline](base/baseline.json), [screenshot](base/restored.png) |
| Tall generation | 600×1900×550 mm; 3 shelves, 1 door, 9 panels; 112/112 actual checks and 6/6 correct cut participants. | PASS | [Baseline](tall/baseline.json), [screenshot](tall/restored.png) |
| Overhead generation | 1000×400×350 mm; 1 shelf, 2 doors, 8 panels; 62/62 actual checks and 2/2 correct cut participants. | PASS | [Baseline](overhead/baseline.json), [screenshot](overhead/restored.png) |
| Guarded base width | Preview then 1200→1100→1200; spec updated by guarded command; 59/59 and 2/2 after changes. | PASS | [Narrow job](runner-results/v5demo-base-narrow-20261017-01/result.json), [restore job](runner-results/v5demo-base-restore-20261017-01/result.json) |
| Tall raw scalar edits | Width 600→700→600; depth 550→600→550; height 1900→2000→1900. Each measured 112/112, cuts 6/6, restored. These are raw parameter edits, not guarded specification migrations. | PASS | [15-step job](runner-results/v5demo-tall-resize-20261017-01/result.json) |
| Overhead raw scalar edits | Depth 350→400→350 and height 400→450→400. Each measured 62/62, cuts 2/2, restored. | PASS | [10-step job](runner-results/v5demo-overhead-resize-20261017-01/result.json) |
| Full baseline restoration | Original measured bounds/volumes, parameters, spec identity and counts recovered for each new cabinet. | PASS | [Base](base/restored.json), [tall](tall/restored.json), [overhead](overhead/restored.json) |
| G5 preview against restored reports | CSV/JSON historical consistency PASS for all three; 25 stable panel IDs and axis-specific dimensions match separately recorded actual BRep sizes within 0.01 mm; quantity 1, backs 6 mm/main panels 18 mm. | PASS | [Cross-check](cut-list-crosscheck.json); [base CSV](base/preview/panels.csv)/[JSON](base/preview/panels.json), [tall CSV](tall/preview/panels.csv)/[JSON](tall/preview/panels.json), [overhead CSV](overhead/preview/panels.csv)/[JSON](overhead/preview/panels.json) |
| Raw-edit evidence/spec consistency | Stored original spec differs from raw width/depth edits. Historical consistency correctly refuses PASS; CAD geometry measurements themselves passed. | FAIL (expected consistency result) | [Tall width](tall/preview-raw-width-divergence/panels.json), [overhead depth](overhead/preview-raw-depth-divergence/panels.json) |
| Specification-only preview | No measurement report; must not claim verified CAD. | UNKNOWN (expected) | [Spec-only output](base/preview-spec-only/panels.json) |
| Protected documents | Original G3 remains clean saved v2; original G4 remains dirty saved v1. No existing document saved, closed, discarded or altered; five document identities retained. | PASS | [Before](protected-before.json), [after](stage1-final-state.json) |
| Exact original Runner restoration | Native stop/start; original 33-file set and hashes/config restored; 24 active cabinet modules verified; ping PASS; historical journals unchanged. | PASS | [Restoration](installation-restored.json), [active source](stage1-final-state.json), [ping](restored-ping.txt) |
| Editable-file capacity | Observed 7/10 before, 10/10 after third save, then 7/10 after restoration; all five open docs still read-write. No editable-status changes by Astra. Cause not established. | UNKNOWN | [Preflight](live-inventory.json), [after saves](stage1-final-documents.json), [final reading](capacity-final.json) |
| New G4 1→2→1/refusal demonstration | Explicit owner stop before fourth fixture; none created. | NOT RUN | Next-stage owner decision required |
| New save/reopen persistence or fault injection | Not included in this stage; no second save, reopen or fault injection. Structural persistence remains unverified. | NOT RUN | Accepted historical evidence below; no upgraded claim |
| Earlier bed/kitchen/layout/vehicle demos | Outside first-stage approval; installed original demo source retained, no rerun or configuration expansion. | NOT RUN | Separate reviewed stage required; nominal demos do not prove van fit |

## State left for the owner

The three NEW fixtures are `V5-Demo-Base-20261017-01`, `V5-Demo-Tall-20261017-01`, and `V5-Demo-Overhead-20261017-01`. Each was saved only once, before resizing. Each is now geometrically restored but has unsaved test changes; no further save or close was performed. The overhead fixture is active for viewing. Screenshots show actual Fusion model views; closed doors obscure internal joinery, which is supported by the separate BRep and cut reports, not inferred from images.

Original Runner configuration SHA256: `70bf4288f224cef35efc1760aae594c54cf39d1676a298aa10956621d81d8378`. Exact backup retained locally. Four Runner files were temporarily replaced, one module added, cabinet source temporarily selected from the verified candidate bundle, and edit permission restricted to the current NEW fixture's exact cloud ID. Original settings/files/allowlist restored. Two temporary added files were preserved outside the installation, not deleted. An automatic approval review blocked a combined restore/delete command; restoration completed safely by preserving those files instead. No unresolved recovery state or failed live cabinet check occurred.

Wheel SHA256: `55d9530da10866d08a2e0c84e6c7083d9aef5044278648f62e78ef183eb10e50`. G5 previews ran offline through the accepted installed package; no new framework or production edit. CSV/JSON reports remain nominal engineering previews: `material_ref=ply_main` is a shared reference even on the separate 6 mm back; thickness comes from the explicit numeric field, not the material-reference label. No stock, grain, machining, manufacturing, structural or vehicle-fit certification.

The extractor labels its own result **historical report consistency**, with cut ownership/saved state UNKNOWN where that input report cannot establish them. This demonstration adds separate timestamped live measurements, identity snapshots and cut audits; it does not overwrite those honest UNKNOWN fields or imply ongoing live monitoring.

## Review and next decision

Jack: independently review these published measurements, restoration and preservation records. The bounded G5 acceptance is unchanged. Accepted [G3 evidence](../g3-remaining-verification/final-guarded-persistence/README.md), [G4 evidence](../g4-shelf-count/live-20261017/README.md), and [G5 tests/reproducibility](../g5-candidate-evidence/numeric-review-fix/README.md) are reused for unchanged regression behaviour; no broad replay or new CI qualification is claimed for this evidence-only change.

Stop before G4. Owner decision: whether to authorize the separate new G4 fixture stage after a fresh read-only capacity check. No existing document may be changed to create capacity. That stage needs its own temporary backed-up Runner cutover, exact new fixture ID permission and first save, followed by restoration; no fault injection, second save/reopen, permanent deployment or expansion is included. The capacity discrepancy must be resolved or shown non-blocking by a fresh observation before proceeding.

## Artifact integrity and privacy

[Publication manifest](PUBLICATION-MANIFEST.json) records original and published SHA256 for every copied artifact. Originals, private exact backups/configuration and journals remain locally preserved. Cloud/project/folder identifiers are replaced with deterministic hashes in publication copies; numeric observations, statuses and negative outcomes are retained. JSON preview report hashes refer to original report bytes. Source paths describe the actual Windows installation. No credentials/session/configuration contents are published.

