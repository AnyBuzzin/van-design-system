## Summary

Extend the existing Fusion runner so a new campervan demonstration can be created,
built, verified, saved and pictured through queue jobs. FirstInteriorDemo is the
only approved build entry point; no new service, UI or arbitrary-Python command.
Targets feature/first-interior-demo to keep this runner extension separate from
the existing interior geometry PR.

## Safety and contracts

Demo jobs reference live documents created by this runner session. Existing tabs
cannot be adopted. Build refuses saved, modified or non-empty designs. Save
requires successful build evidence, fresh BRep validation, restored baseline
parameters/counts, explicit project/folder IDs and an unused filename. SaveAs
is attempted once; uncertain saves and failed verification cannot be retried.
No existing document is saved, closed, discarded or made read-only/editable.
Existing names/saved/modified/valid flags are checked throughout the workflow.
Restart intentionally forgets session ownership. The schema remains job/1 with
additive commands; new jobs require runner 0.2.0. The old runner must be restarted
once after installation; routine demo jobs then require no Fusion UI steps.

## Tests and actual Fusion evidence

- 64 offline runner tests PASS; five foundation tests PASS. Logs attached in repo.
- Real Fusion 2705.1.30 / runner 0.2.0: project lookup, create, approved build,
  fresh verification, save, viewport capture and separate saved inspection PASS.
- Build: 95/95 real-BRep checks across five baseline/edit/restore stages;
  presave verification: 19/19; zero interference throughout.
- Saved VanDesign-Autonomous-Interior-Demo-20261015 in Default Project root,
  version 1, cloud complete, no unsaved changes; 24 parameters, 15 panel
  occurrences, 16 components including root, 49 timeline items.
- Existing document snapshot flags remained unchanged, including modified v5-g3-tall.
- See automation/evidence/demo-workflow/STATUS.md, original job reports,
  viewport.png and the existing packager's ZIP/SHA-256 manifest.

## Limits and review

Save/reopen persistence, wider parameter ranges and explicit cut-participant
readback on the combined interior remain unverified. BRep reports record bounds
verdicts rather than raw corners. No real van-fit, structural or manufacturing
qualification is claimed. Draft for integration/safety review; do not merge
without review. Revert this branch and restore the installed runner backup to
roll back code; never alter existing designs as part of rollback.
