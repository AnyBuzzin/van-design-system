# VanDesign agent rules

**Owner standing instruction, 18 October 2026. This replaces the Tier A–D policy, the Issue #36 mandate and all earlier approval gates.**

Goal: visible progress in Fusion every session. Judge every task by one question: can the owner open Fusion and see something new that works?

## How to work

1. Read [PROJECT_STATUS.md](PROJECT_STATUS.md) and take the top unfinished item in [docs/ROADMAP.md](docs/ROADMAP.md). Work on it until it works in Fusion.
2. Branch from `develop`, one branch per feature. Jack merges to `develop` after his review when CI is green. Never touch `main`, releases or tags.
3. Run live Fusion tests whenever useful, in **new documents you create in that session**. Don't save them unless the owner asks (saved documents count toward Fusion's 10-editable-document limit). Never open, edit, save, close or discard any document you did not create.
4. Don't change the installed Runner's configuration or installation. Using it to run jobs is fine.
5. If an hour passes with no working geometry, stop and report why in one line.

## Writing rules

- A PR description is **at most 10 lines**: what changed, what you tested, one screenshot of the Fusion model. That is the whole record.
- **No** new evidence folders, handover files, status reports, manifests or hash tables. Keep test output in CI or in the test itself.
- Comment in an issue only to report a finished feature or a real blocker. No acknowledgements, plans, proposals or role sign-offs.
- Update PROJECT_STATUS.md (one screen maximum) only when a feature is finished.
- Ask the owner only when a decision needs money, a new product feature, or anything touching `main`. Ask as a yes/no question in under 50 words.

## Who does what

- **Jack — lead developer, reviewer and publisher.** Sets the next milestone from ROADMAP.md, reviews every PR (code, tests, and whether the tests prove the feature works in Fusion), asks Astra for fixes, merges to `develop` when satisfied and CI is green, and reports to the owner.
- **Astra (Ashra) — builder.** Writes all the code and all the tests, runs them offline and in Fusion, fixes Jack's findings and opens the PR.
- **Claude — independent reviewer.** Reviews milestones when the owner asks (for example "Claude, review PR 40"). Not a step in every PR.

Cycle: Jack sets the task → Astra builds and tests → Jack reviews → Astra fixes → Jack merges and sets the next task. No other agents take part. CI (`unit-tests (3.10)` and `unit-tests (3.12)`) must pass before any merge. The owner judges progress by looking at the model in Fusion.

## Engineering rules (unchanged)

- `src/vandesign` is the only maintained runtime. Keep CAD-neutral millimetre maths in the core; keep `adsk` imports and unit conversion in the Fusion adapter.
- Keep models parametric: dimensions must stay editable as Fusion user parameters, not only in code.
- Give every component a stable ID. Every boolean cut names its exact target bodies.
- Check changed CAD behaviour against real Fusion bodies (sizes, cuts, contacts, interference), not arithmetic alone. Never weaken a test to get a pass.
- No claims of manufacturing, load, anchoring, vehicle-fit or CNC readiness without real evidence.
- No force pushes, no history rewrites, no credentials or cloud document IDs in the repo.

Detailed geometry rules: [precision and ownership](docs/standards/precision-and-ownership.md).
