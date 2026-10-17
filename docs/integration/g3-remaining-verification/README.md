# G3 remaining overhead verification — 2026-10-17

**G3 remains OPEN.** Depth, height, expected invalid-height detection/restoration and exact cut ownership PASS. Cabinet persistence comparison PASS, but the overall persistence safety test **FAILS**: after reopening the dedicated fixture, the previously open empty, unmodified `Untitled` document reference was invalid and only the dedicated fixture remained open. Do not call this full acceptance.

## Contract and scope

Based on integrated `develop` `7508f45840b5400da9ec0435d92f574e17969825`, following [Jack's instructions](https://github.com/AnyBuzzin/van-design-system/issues/4#issuecomment-6205063240). Objective: only missing overhead F3 checks and F0 evidence disposition. Changed files: this evidence directory, the small accepted-#17 correction in `PROJECT_STATUS.md`, and Jack's requested retention of future material/anchoring requirements in `docs/ROADMAP.md` (planning only, issue #20). No production code, G4/G5 implementation, release, merge, new infrastructure or deployment-package changes.

The owner explicitly approved, in this chat, saving the newly created fixture in Default Project's root folder, temporarily allowlisting only its new cloud identity, performing the parameter tests, saving the restored baseline and closing/reopening only that fixture once. Existing designs were outside that authorization. The original runner configuration was backed up before changing the allowlist and restored byte-for-byte after testing. No restart was needed: the existing runner reloads configuration for each job.

## Results and original evidence

| Criterion | Observed result | Evidence |
| --- | --- | --- |
| Installed configuration/bundles | PASS: accepted config hash; 31/31 files in each bundle; 15 installed runner files equal migration backup | [Preflight](preflight.json) |
| Live connection/source | PASS after owner started Fusion: runner ping; 24 loaded cabinet modules at permanent deployment, each hash matched | [Ping](runner/vd-20261017T011556-8f86bc/result.json), [module provenance](live-module-provenance.json) |
| Fresh overhead baseline | PASS 62/62, zero FAIL/UNKNOWN | [Original JSON](report_20261017_011732_786085_build.json), [TXT](report_20261017_011732_786085_build.txt) |
| Depth 350 → 400 → 350 mm | PASS 62/62 at changed and restored values | [Batch result with raw-report paths](runner/g3-overhead-remaining-20261017-001/result.json) |
| Height 400 → 450 → 400 mm | PASS 62/62 at changed and restored values | Same batch result |
| Height 800 → 400 mm | Expected raw FAIL: exactly `profile.overhead.height_range`, 61 PASS, 1 FAIL, 0 UNKNOWN; restore 62/62 PASS | Same batch result; negative raw report is retained |
| Baseline restoration | PASS: all 16 parameter records, counts, stored hash equal; entire named validation records equivalent within absolute 1e-6 | [Comparison summary](verification-summary.json) |
| Overhead dado participants | PASS 2/2: each cut has exactly its intended side-panel body, shelf excluded; marker28 restored; counts unchanged | [Audit JSON](overhead-cut-audit-retry.json), [TXT](overhead-cut-audit-retry.txt) |
| Cabinet save/reopen | PASS for same cloud-identity digest, version2, stored spec, expressions/parameters, counts, eight solid-body bounding boxes/volumes and named validation results | [Persistence record](persistence.json), [execution script](persistence-check.py) |
| Other-document preservation during reopen | **FAIL**: original empty unsaved `Untitled` reference invalid after reopen; only dedicated fixture remains | [Post-operation inspection](post-persistence-inspection.json) |
| Configuration rollback/queue | PASS: exact original bytes restored; temporary permission removed; three journals empty, two historical journals unchanged; inbox/claimed empty | [Rollback](configuration-restored.json), [summary](verification-summary.json) |

The 800 mm result is a validator refusal of an out-of-profile live edit, not a claim that Fusion refused to construct any 800 mm geometry. Existing runner expectations explicitly require that single named FAIL, then a separate PASS expectation for restoration. Unexpected failure stops the batch. No failed state was saved.

The new baseline measurement was necessary to establish a fresh, dedicated test fixture without adopting a protected historical file. The later baseline/restore and pre/post-reopen measurements verify this fixture's restoration and persistence; they do not replay the accepted base/tall campaigns.

## Failure and recovery details

1. Initially Fusion was not running. Owner opened it; runner ping and inspection passed. The preflight records the earlier disconnected state, not the final live state. The prior API session was expired; a new session was initialized using the existing local helper. No software was installed.
2. First cut audit in a read-only API script returned **UNKNOWN** because timeline rolling failed. [Original result](overhead-cut-audit.json) remains intact. Retried the same verified audit with timeline movement enabled, restricted by the exact newly created document object; it passed and restored marker/counts. No historical successful audit was repeated.
3. Persistence opened the same saved version successfully and all cabinet comparisons passed, but the other-document preservation assertion failed. Before fixture creation, runner inspection showed the original `Untitled` was empty (zero parameters/occurrences/timeline items), unsaved and unmodified. It was still valid with unchanged flags before the restored-baseline save. After close/reopen it was invalid. The script explicitly closes only the clean dedicated fixture; automatic removal of the empty tab by Fusion is a plausible explanation, **not independently proven**. We cannot claim the original document was preserved or recreate its exact identity. No saved or modified pre-existing design was open in this session.
4. Stopped further mutation; restored original configuration and made a read-only inspection. The dedicated test file remains open, saved and unmodified at version2. No second persistence attempt, replacement blank tab, further save, close, deployment change or manual journal clearing occurred.

This safety failure requires Jack's review and an owner decision before any further persistence operation. Do not silently waive it because the original tab was empty. Recommended next step: review this evidence and agree a narrow persistence precondition that prevents implicit disposal of other documents; only retest that safety gap if required and separately authorized. No new infrastructure is proposed.

## Source, fixture and reproducibility

- Fusion `2705.1.30`, runner `0.4.0`, installed canonical package `0.5.0`. Permanent cabinet source: `%USERPROFILE%\Documents\VanDesign-Runner\deployments\vandesign-0.5.0\VanCabinetJoineryV5`; demo bundle is the sibling `FirstInteriorDemo` directory and was not exercised again.
- Both deployment manifests and all covered file hashes are in preflight. Config before/after SHA-256: `70bf4288f224cef35efc1760aae594c54cf39d1676a298aa10956621d81d8378`.
- Audit source is the separately configured `%USERPROFILE%\Documents\VanDesign-G3\4d4345b\VanDesignCutAuditG3\VanDesignCutAuditG3.py`, SHA-256 `3f9426842a110768da0a0ca0ba6eecda27e4054fb7a20dd70867450efe59efb0`, byte-identical to immutable `4d4345b6cde6084b1731c5298fa50d70759ef061`. Its Windows checkout differs only by line endings. This historical audit is not a second production cabinet runtime.
- Fixture: `VanDesign-G3-overhead-remaining-20261017`, new schema0.2 `overhead@1`, 1000 × 400 × 350 mm, one shelf/two doors; design-spec hash `6c15b5e34fdedbff55f796d416f4c3dc89a3109b58b71d264df668a4d322c2b2`. Counts: 16 parameters, 8 occurrences, 9 components, 28 timeline items. Private cloud ID is consistently hashed in publication, allowing identity comparison without publishing the identifier.
- [Fixture script](create-overhead-fixture.py) invokes the existing verified adapter/generator, not the historical runtime. It retains a process-local reference to the newly created document and snapshots other-document flags. It does not adopt the existing blank tab. The saved target used by runner jobs is the cloud identity subsequently assigned to that exact object.
- [Batch arguments](parameter-batch-args.json) were validated with existing `vdrunner.schema.validate_args`; the [submitted job](runner/g3-overhead-remaining-20261017-001/job.json) has its private cloud target hashed and is **publication evidence, not an executable job**. Original private job was submitted using the existing `vdrunner ... submit ... --wait` CLI. Do not rerun published scripts without fresh authorization, source/identity verification and unique artifact names.
- Persistence uses the supported Python API because existing `verify_demo_persistence` is specific to FirstInteriorDemo. It explicitly checks dedicated identity, completed cloud save and clean state before the sole close/open call. The owner authorized that exact operation; no demo-policy bypass or new queue command was introduced.

[Publication manifest](publication.json) records original and published SHA-256 plus transformations. Original raw cabinet reports and audit outputs are byte-preserved. Cloud IDs are hashed and local home paths sanitized where necessary; the module API wrapper is unwrapped. Original private configuration, cloud identifiers, API session and save requests remain local under `%USERPROFILE%\Documents\VanDesign-Runner\issue4-live-20261017`. Never publish the entire private directory.

## Reused evidence and F0 recommendation

- F1 base functional acceptance: [review](https://github.com/AnyBuzzin/van-design-system/issues/4#issuecomment-6178616946). No repeat.
- F2 tall and accepted F3 partial: [independent review](https://github.com/AnyBuzzin/van-design-system/issues/4#issuecomment-6179321734), [preserved original archive](../evidence/G3-F2-F3-partial-evidence.zip), [summary](../evidence/G3-F2-F3-partial-summary.md). Archive SHA remains `3463781dc1c959652a2f83dee56c154da51e06944584b0e6c923cdf7bac5cf42`. Accepted overhead dado/ply/width changes were not repeated.
- F0 legacy copy: [first measurement](https://github.com/AnyBuzzin/van-design-system/issues/4#issuecomment-6177429274), [repeatability](https://github.com/AnyBuzzin/van-design-system/issues/4#issuecomment-6177513713), [default build](https://github.com/AnyBuzzin/van-design-system/issues/4#issuecomment-6177651797). Accepted original-report hashes are in those reviews; this turn did not independently retrieve/re-parse those originals. The first two already cover live ply15/dado8/shelf1185.4 under the G3 loader.
- Original G2 A–E: [protocol](../../../prototypes/claude-v5/FUSION_TEST_PROTOCOL.md). Installed-wheel compatibility and PR14 canonical base: [package migration](../ONE_PACKAGE_MIGRATION.md), [live review](../pr14-checkpoint-evidence/live-20261015/FINAL_REVIEW.md). #17 accepted deployment: [evidence](../issue17-runner-cutover-20261016/README.md).

**Recommendation to Jack:** accept F0 by this combined evidence for its documented compatibility scope. There is no newly identified missing parameter combination justifying a full replay; the often-cited E combination already has accepted actual G3 legacy measurement evidence. This does not assert that A–E were all freshly executed under the current wheel, and is not a unilateral acceptance decision. Jack must record the disposition.

## Handover

Remaining decisions: Jack's F0 evidence-equivalence assessment and the persistence safety failure disposition. No G3 closure or merge requested without approval. No manufacturing, mounting-strength, vehicle-fit or road-legal qualification is implied. Production source is unchanged, so no broad offline suite was repeated; proportionate checks are the real-Fusion evidence, argument-schema validation, evidence hashes and document/link review.
