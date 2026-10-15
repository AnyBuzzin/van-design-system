# Real-Fusion baseline report review — 2026-10-15

## Actual captured result

The user launched the generated cabinet script in a new unsaved Untitled document. Its complete raw JSON and text reports are preserved here without editing. Fusion version 2705.1.30; build base@1; 59 PASS, 0 FAIL, 0 UNKNOWN; no diagnostics.

Measured geometry validation: PASS for this baseline. Eight managed panel components (nine including root), sixteen user parameters and twenty-eight timeline items. Nominal cabinet width/height/depth 1200/850/550 mm; shelf length 1175.4 mm. Both side volumes 8,354,616 mm3, shelf volume 11,509,516.8 mm3. All eight panel bounding-box/volume checks passed. Each dado has measured 5.7 mm shelf penetration, 0.3 mm end gap, 0.25 mm clearance above/below; empty-groove and surrounding-material probes passed. Joined interference count is zero. These are actual Fusion adapter measurements in the captured report, not newly executed checks by this review session.

Explicit dado participant ownership: UNKNOWN. The report's unmodified shelf volumes and correct side volumes support the intended cut effect, but do not enumerate feature participantBodies. A separate live audit remains required.

Parameter edit/restore: UNKNOWN / NOT RUN. Baseline Cab_Width expression is exactly `1200 mm`. No parameter or document mutation was attempted by the assistant.

## Package evidence and limitations

All 31 manifest-covered cabinet deployment files still match their recorded SHA-256 values (artifact-review.json). DEPLOYMENT.json is preserved alongside the report; its prior manifest hash and wheel parity audit are in the parent evidence folder. New reports and Fusion-created .vscode/launch.json are additional files beside the deployment, not changed runtime files. The strict pristine-inventory audit now refuses those extra files as designed; that refusal is not a source-hash mismatch.

PR14 in-process runtime identity: UNVERIFIED. The output location, user's selected generated launcher and matching file hashes support the deployment attribution. However, the report records generator/spec hashes, not imported module __file__ paths or loaded-code hashes. The historical runtime has the same generator identity. Do not treat the spec hash as a source hash or historical runner output as deployment proof.

## Remaining live blocker

The computer-use skill found a single Fusion window titled Untitled*. Initial capture failed with `FrameArrived timed out: timed out waiting on channel`; refreshed selection/activation and one capture recovery failed with `window capture timed out: timed out waiting on channel`. No blind inputs or alternate Windows automation were attempted. The runner heartbeat remains stale/marked stopped and still targets historical packages; installation/configuration/queue were untouched.

The user has been asked for one action: dismiss the results dialog with OK and leave the new unsaved Untitled design visible and active. After access recovers, capture actual loaded module origins, run the existing participant audit, measure Cab_Width at 1210 mm, restore the exact original expression, and compare baseline/restored BRep. Restore must be attempted even if the edited validation fails; never touch other designs or save this one.

This baseline advances the checkpoint but does not close it. Jill should review these raw results and source-integrity evidence; deployment identity, explicit ownership and edit/restore remain integration blockers. No merges, production code changes or full G3/G4 campaigns were performed.

## Follow-up after results dialog dismissal

The user dismissed the dialog and left Untitled active. Screen capture again timed out, but accessibility-only inspection succeeded. Fusion exposed a sparse tree without reliable script/parameter controls. A Scripts and Add-Ins shortcut and the documented Text Commands shortcut were attempted; neither produced readable controls. No parameter, geometry, saved-document or runner changes were made.

Prepared `fusion/PR14CompatibilityCheckpoint` as a one-shot Fusion test script, outside the reviewed deployment. It does not reload/import a substitute runtime: it first requires the existing loaded VanDesign modules to originate in the reviewed bundle and match its fixed manifest hash and each file hash. It refuses saved/non-Untitled documents and mismatched baseline counts, width or stored spec. It reuses the existing validator, BRep reader and preserved cut audit; checks baseline, edited and restored geometry; and restores the exact original width expression in finally even when edited measurement raises. Raw reports and detailed stage snapshots are written here. No runner, production runtime or historical source changes were made.

Four focused offline safety tests PASS, plus script compilation. These establish the guard/restoration logic only, not live checkpoint success. The user was asked for one manual script launch. Until its raw evidence is produced and independently reviewed, package identity remains UNVERIFIED, explicit cut participants UNKNOWN and edit/restore UNKNOWN. This is not a new furniture feature or automation framework.
