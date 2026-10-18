# VanDesign agent rules

**Owner standing instruction, 18 October 2026. This replaces the Tier A–D policy, the Issue #36 mandate and all earlier approval gates.**

Goal: visible progress in Fusion every session. Judge every task by one question: can the owner open Fusion and see something new that works?

## How to work

1. **Task board = GitHub labels.** Jack labels the next task issue `ready`. Astra takes the oldest `ready` issue, switches it to `in-progress`, and to `review` when the PR is open. `blocked` means the owner or an outside fix is needed. One `in-progress` task at a time.
2. **Done criteria first.** Before labelling a task `ready`, Jack writes 3–5 checkable done criteria in the issue (for example "bed and cabinet both resize from Fusion's parameter table with no overlap"). Jack reviews against those criteria only.
3. Branch from `develop`, one branch per task. **Only Astra pushes to her branch;** Jack reviews and comments but never edits it. Jack merges to `develop` after his review when CI is green. Never touch `main`, releases or tags.
4. **Two review rounds maximum for minor issues.** After the second round, minor points become a new issue instead of blocking the merge. A real defect (wrong geometry, failing check, safety rule broken) always blocks the merge, however many rounds it takes.
5. Run live Fusion tests whenever useful, through the **existing Runner** (extend its demo commands; don't build a separate test tool).
   - **Session baseline.** At the start of each working session, Jack runs the Runner's `inspect` and posts the list of open Fusion documents once in the active issue. If that list changes in a way no agent caused, stop and tell the owner.
   - **Only Runner-created documents.** Agents may close only documents the Runner created in that session, identified by its job ID, never by title. Never open, edit, save, close or discard any other document.
   - **One live Fusion job at a time.** Before starting, confirm no other Runner job is running; if one is, wait for it.
   - **Fusion personal-use limit: 10 editable documents.** At the end of every test, close the documents you created **without saving**; unsaved documents don't count toward the limit.
   - If a document must be saved (only when the owner asks), mark it **read-only** before you finish. If you can't do that through the API, tell the owner the document name in one line so they can mark it.
   - Before starting a test, check the editable-document count; if it is 9 or more, stop and tell the owner.
6. **Running** reviewed Runner jobs is autonomous. **Replacing or reconfiguring** the installed Runner needs a one-line yes from the owner, and only from code merged to `develop` with green CI. Back up the current installation first so it can be rolled back.
7. If an hour passes with no working geometry, stop and report why in one line.

## Writing rules

- A PR description is **at most 10 lines**: what changed, the measured PASS/FAIL result, one screenshot of the Fusion model. The screenshot is for the owner; PASS/FAIL comes only from the Runner's machine-checked geometry (body sizes, net volumes, which bodies each cut touched, material removed, interference).
- **No** new evidence folders, handover files, status reports, manifests or hash tables. Keep test output in CI or in the test itself.
- Comment in an issue only to report a finished feature or a real blocker. No acknowledgements, plans, proposals or role sign-offs.
- Update PROJECT_STATUS.md (one screen maximum) only when a feature is finished.
- Ask the owner only when a decision needs money, a new product feature, a Runner reinstall, or anything touching `main`. Ask as a yes/no question in under 50 words.

## Who does what

- **Jack — lead developer, reviewer and publisher.** Sets the next milestone from ROADMAP.md, reviews every PR (code, tests, and whether the tests prove the feature works in Fusion) and records the verdict as a GitHub review from his own account, asks Astra for fixes, merges to `develop` when satisfied and CI is green, and reports to the owner.
- **Astra (Ashra) — builder.** Writes all the code and all the tests, runs them offline and in Fusion, fixes Jack's findings and opens the PR.
- **Claude — independent reviewer.** Reviews milestones when the owner asks (for example "Claude, review PR 40"). Not a step in every PR.

Cycle: Jack writes done criteria and labels `ready` → Astra builds and tests → Jack reviews (two rounds max) → Jack merges and labels the next task `ready`. No other agents take part. CI (`unit-tests (3.10)` and `unit-tests (3.12)`) must pass before any merge. The owner judges progress by looking at the model in Fusion.

## Engineering rules (unchanged)

- `src/vandesign` is the only maintained runtime. Keep CAD-neutral millimetre maths in the core; keep `adsk` imports and unit conversion in the Fusion adapter.
- Keep models parametric: dimensions must stay editable as Fusion user parameters, not only in code.
- Give every component a stable ID. Every boolean cut names its exact target bodies.
- Check changed CAD behaviour against real Fusion bodies (sizes, cuts, contacts, interference), not arithmetic alone. Never weaken a test to get a pass.
- No claims of manufacturing, load, anchoring, vehicle-fit or CNC readiness without real evidence.
- No force pushes, no history rewrites, no credentials or cloud document IDs in the repo.

Detailed geometry rules: [precision and ownership](docs/standards/precision-and-ownership.md).
