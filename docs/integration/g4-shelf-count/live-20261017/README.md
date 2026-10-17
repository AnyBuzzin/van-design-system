# G4 bounded live qualification — observed PASS, awaiting independent acceptance

Owner approved [Jack's review and limited procedure](https://github.com/AnyBuzzin/van-design-system/pull/22#pullrequestreview-5560140946). Executed reviewed source **50c195593ca4d32702d17a502bf56baffe9d445f**, candidate wheel SHA256 `6985f3e7ffcb2ed0a7f01553ca8498a22c6062da9acecacc293ed03ad54346eb`, Fusion2705.1.30/Python3.14, on2026-10-17. This evidence-only addition changes no runtime source. PR22 remains draft; Issue20 open; no merge, release, permanent deployment or G5.

## Actual results

| Stage | Observed result | Evidence |
| --- | --- | --- |
| Initial preflight | STOP while Fusion closed; no deployment/design change | [original stop](preflight.json) |
| Resumed preflight | Runner ping PASS; exact reviewed sources/hashes; Default Project available; unique fixture name;9/10 editable-file capacity; no pending/claimed jobs or unresolved journal | [live inspection](preflight-live.json), [capacity](capacity-check.json), [source proof](candidate-source-proof.json) |
| New default base@1 fixture |59/59 geometry PASS;2/2 exact dado targets | [baseline](baseline-build.json) |
| Single first save | Unique `VanDesign-G4-base-shelf-count-20261017`, Default Project root, version1, cloud-complete and clean | [save](first-save.json) |
| Preview1→2 and update | Preview PASS;85/85 geometry PASS;4/4 exact cuts; parameters/panels/components/timeline18/9/10/35 | [preview](jobs/g4-live-20261017-preview-two/result.json), [update with raw report/audit links](jobs/g4-live-20261017-to-two/result.json) |
| Preview2→1 and restore | Preview PASS;59/59 geometry PASS;2/2 exact cuts; counts16/8/9/28; original stored spec and measured inventory restored | [preview](jobs/g4-live-20261017-preview-one/result.json), [update](jobs/g4-live-20261017-to-one/result.json) |
| Obsolete grooves/orphans | Original body bounds/volumes/topology, sketch/model-parameter signatures and census equal;108/108 interior material probes at all four obsolete two-shelf cut locations PASS; added shelf/cuts absent | [restoration proof](restoration-extra-proof.json) |
| No-op refusal | Expected FAIL job, refused before mutation; measured baseline unchanged | [original failed result](jobs/g4-live-20261017-no-op/result.json), [before/sentinel setup proof](refusal-before.json) |
| Unrelated empty sentinel | Expected FAIL/ERROR for unexpected timeline entities; exact before/after fingerprints unchanged; removed only the captured test sentinel, verified baseline restored | [original failed result](jobs/g4-live-20261017-sentinel/result.json), [fingerprints](sentinel-refusal-proof.json) |
| One-shot partial-construction failure | Expected FAIL job after first replacement panel was captured/built; recovery PASS59/59 and2/2 cuts; original inventory restored; journal clear; hook removed in finally | [original failed job and recovery](controlled-recovery-result.json), [execution confirmation](controlled-recovery-api.json), [hook removal](controlled-hook-removal.json), [journal](fixture-journal.json) |
| Original installation restoration | Exact26-file set and bytes restored; original configuration hash; historical journal hashes unchanged; original Runner ping PASS and24 permanent-bundle modules verified | [restoration](installation-restored.json), [loaded source/document proof](final-state.json), [ping](jobs/vd-20261017T223608-ba3b25/result.json) |

No unexpected CAD, recovery, document or configuration failure occurred after prerequisites were established. The two refusal jobs and one injected-failure job **remain FAIL in original evidence**; their expected refusal/recovery behavior passed. Session startup initially returned “not initialized” until the standard initialization notification completed; this was connection setup only, before deployment or CAD work. The earlier Fusion-closed stop is retained.

## Scope and safety record

The existing G3 overhead document stayed open, saved at version2 and clean, with its original cloud identity and flags unchanged. No existing owner design was modified, saved, closed or discarded. The new G4 fixture was saved **once** before structural tests and remains open at version1 with unsaved test changes after measured restoration. No second save/reopen or persistence campaign occurred. Accepted G3 campaigns were not repeated.

Temporary installation changes were only `fusion_backend.py`, `vdrunner/executor.py`, `journal.py`, `schema.py`, new `vdrunner/shelf_change.py`, and the two approved config fields (`g3_script_dir`, fixture-only `allowed_design_ids`). Native Fusion Scripts stop/start was used. Audit/demo/permanent bundle paths, protected IDs, queue/history remained intact. Full original file/config backup and a separate queue snapshot were preserved. Restoration copied back original changed bytes/cache files and removed only the added shelf module and its identified cache; no queue snapshot was restored over new results.

Original/restored configuration SHA256: `70bf4288f224cef35efc1760aae594c54cf39d1676a298aa10956621d81d8378`. [Original installation manifest](original-installation-manifest.json). The final active implementation is the original Runner, **not a permanent G4 deployment**.

The [one-shot helper](helpers/controlled-recovery.py) was pinned and inspected before execution: SHA256 `f68a43f130286063f00c7dcb97b80920956ae4f4ae416e5847d7d8fb3b46d0c8`. It changes only one backend/adapter instance, injects once after a captured panel, executes the installed Runner Executor with its normal journal, and removes instance overrides in finally. It exposes no arbitrary queue Python command or persistent production switch. [Pin/review record](controlled-helper-pin.json).

## Evidence handling and handover

Original reports, failed-job records, scripts, backup and journals remain under the local `VanDesign-Runner/issue20-live-20261017T212117Z` checkpoint and existing queue. This publication contains cloud-ID-redacted copies; private configuration, credentials and project/customer IDs are excluded. [Publication manifest](PUBLICATION-MANIFEST.json) records original and published SHA256 for every copied artifact. Raw measured values, statuses and negative outcomes are preserved; formatting may differ. Entity tokens concern the disposable fixture only and remain evidence of that bounded run.

Jack: independently review the actual reports, ownership/obsolete-groove proof, one-shot recovery and exact installation restoration. **G4 acceptance is pending your review and the owner's integration decision.** General reconciliation, arbitrary manual content/metadata, external references, process-crash recovery, manufacturing qualification and later-roadmap work remain unsupported. No further owner action is needed to complete this approved live run; any additional test, save/close, permanent deployment or merge requires its own authorization.
