> New installations: generate scripts from the installed wheel as described in [single-package deployment](../docs/integration/ONE_PACKAGE_MIGRATION.md), then use those generated folders for --g3-dir and --demo-package-dir. Existing pinned installations are not changed by the migration.

# VanDesign Fusion automation runner (v0.2.0)

Runner-created demo creation, approved build, verified first save and viewport
capture: [DEMO_WORKFLOW.md](DEMO_WORKFLOW.md). Existing-design mutation rules
remain unchanged; only newly runner-created sessions can use the demo lifecycle.

Replaces repeated Claude Computer Use clicking with validated local jobs executed
inside Autodesk Fusion through its supported Python API.

```
Claude / local CLI (python -m vdrunner)
   -> validated JSON job (schema vandesign.runner.job/1) -> <queue>/inbox
   -> VanDesignRunner add-in (watcher thread fires a Fusion CustomEvent;
      the job runs on Fusion's main thread, one at a time)
   -> verified G3 code reused unchanged (measure + validate + report writer,
      VanDesignCutAuditG3)
   -> original G3 TXT/JSON reports + audit reports + result.json per job
   -> python -m vdrunner package -> evidence ZIP with SHA-256 manifest
```

**Dependency baseline:** branched from `4d4345b` on the *unmerged* G3 branch
`feature/v5-g3-cabinet-variants` (draft PR #5). The runner does not copy or modify
G3 code; it imports the verified G3 install named in `config.json`.

## Layout

| Path | Role |
|---|---|
| `vdrunner/` | Pure Python (no `adsk`): `schema` (strict job validation), `queue` (atomic files, ledger, states, recovery, heartbeat), `executor` (sequencing + safety), `expect` (pass criteria), `journal` (restore journal), `policy` (allowlist, bounds), `evidence`, `cli` |
| `VanDesignRunner/` | Fusion add-in: `VanDesignRunner.py` (lifecycle, watcher, CustomEvent) and `fusion_backend.py` (the only `adsk` code) |
| `schema/vdrunner-job-v1.schema.json` | Versioned JSON Schema documentation of the job contract |
| `jobs/examples/` | `ping`, `inspect_design`, `measure_base`, `demo_base_dado_batch` |
| `tools/install_runner.py` | Install/upgrade the add-in, manage the allowlist |
| `tests/` | 44 offline unit tests (fake Fusion backend) |

## Commands (all others are rejected)

| Command | Mutates | Behaviour |
|---|---|---|
| `ping` | no | Runner + Fusion version |
| `inspect_design` | no | Cloud identity, parameters, counts, timeline, managed ids, stored-spec hash |
| `measure` | no | G3 measure path only (never builds); original G3 TXT/JSON report; step passes only if its `expect` block is met (default: verdict PASS, 0 FAIL/UNKNOWN, stored spec unchanged) |
| `set_parameter` | yes | Allowlisted design only; `Cab_*` name in bounds; plain `N mm` expression only (formulas refused); journalled *before* the change; value read back |
| `restore_parameter` | yes | Restores the journalled original, reads it back, re-measures; journal cleared only if both pass |
| `audit_cuts` | no* | Runs `VanDesignCutAuditG3` (*it moves and restores the timeline marker); requires timeline restored, counts unchanged, all features PASS |
| `preview_width_change` | no | G4: plan a width change from the stored spec (changed parameters/panels/cuts, new hash, refusal reasons). See `G4_WIDTH_UPDATE.md` |
| `update_width` | yes | G4: verified, journalled width update of an existing cabinet; writes the new spec via the G3 adapter; rolls back on any failure |
| `run_test_batch` | if any step mutates | Ordered steps, stops at the first non-PASS step, design counts/hash must stay equal to the batch's first measurement |

Existing-design operations never save or build. The guarded demo lifecycle can
create a new design, run FirstInteriorDemo and first-save verified results.
The runner never deletes existing designs, exports manufacturing data or
executes Python supplied in jobs (enforced by schema and lifecycle tests).

## Safety model

* **Identity:** the target is the Fusion `DataFile.id` (cloud lineage id), re-checked before *every* step; titles are only a secondary check. Unsaved documents cannot be targeted.
* **Mutation allowlist:** `config.json` `allowed_design_ids`; `protected_design_ids` always refused. The policy is re-read for every job.
* **Restore journal** (`<queue>/journal/`): `pending` -> `applied` -> cleared after verified restore. A `pending` or `restore_unverified` entry blocks all further mutation of that design until a human resolves it. Edits are never stacked.
* **Exactly-once:** `ledger/<id>.submitted` and `ledger/<id>.claimed` are created with `O_EXCL` and never deleted, so an id can be submitted once and executed once, even after restarts or a stray file reappearing in the inbox.
* **Interruption:** at start-up any job still in `claimed/` is marked `interrupted` / outcome `UNKNOWN` and is **not** re-run.
* **Timeouts:** `wait` cancels a still-queued job (so it cannot run late); a running job is reported `timeout_running`. A missing/stale heartbeat cancels a still-queued job as `runner_not_running`; a claimed job is never declared lost on heartbeat silence alone (it ends `done` or `timeout_running`; a crash is marked `interrupted` at the next start).
* **No inferred success:** a job is `completed` only when every step's own evidence met its expectations; otherwise `failed`, `rejected` or `REFUSED`.

## Install and start

```bash
python automation/tools/install_runner.py install --g3-dir "C:\Users\Buzz\Documents\VanDesign-G3\4d4345b\VanCabinetJoineryV5" --audit-script "C:\Users\Buzz\Documents\VanDesign-G3\4d4345b\VanDesignCutAuditG3\VanDesignCutAuditG3.py"
```

This creates `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\VanDesignRunner` (a separate add-in; G2/G3 folders are only read) and `config.json`; the queue defaults to `~/Documents/VanDesign-Runner/queue`. Use `install --upgrade` to replace code and keep `config.json`.

Start once per Fusion session: **Utilities > Scripts and Add-Ins**, find `VanDesignRunner`, switch **Run** on. Then, from `automation/`:

```bash
python -m vdrunner runner                 # heartbeat / alive
python -m vdrunner ping
python -m vdrunner inspect                # read-only; prints the active design_id
python automation/tools/install_runner.py allow <design_id> --name <document name> --note "disposable test design"
python -m vdrunner submit jobs/examples/demo_base_dado_batch.json --target-id <design_id> --target-name <name> --wait
python -m vdrunner package <job_id> [<job_id> ...] --out evidence.zip
```

Exit codes: 0 PASS, 1 FAIL/refused/interrupted, 2 invalid job or duplicate id, 3 timeout, 4 runner not running.

## Recovery

| Situation | What you see | What to do |
|---|---|---|
| Fusion closed or crashed mid-job | job `interrupted`, outcome `UNKNOWN` after next start | `inspect` the design; check `<queue>/journal/<design>.json`; restore by hand or close the design without saving; then delete only that journal entry |
| Restore measurement failed | step FAIL, journal `restore_unverified` | do not save; inspect; fix or close without saving |
| Batch stopped with an edit applied | result `open_edits` | submit `restore_parameter` for each, or close without saving |
| Runner not running | `wait` -> `runner_not_running` (job cancelled) | start the add-in, resubmit with a NEW job id |
| Duplicate id | exit 2 / log `DUPLICATE refused` | use a new id; ids are never reused |

## Tests

* Fast (CI, no Fusion): `cd automation/tests && python -m unittest discover -v` (schema, queue/ledger/duplicates, timeouts, recovery, executor safety with a fake backend, policy, evidence, layering).
* Full offline regression: the fast suite plus `python -m unittest discover -s tests` and `prototypes/claude-v5/tests`.
  On Windows with `core.autocrlf=true` three `test_spec_files` checks fail only because the working tree converts the committed LF fixtures to CRLF; the same suite passes 109/109 on an LF-exact `git archive` export.
* Integration (real Fusion, manual start of the add-in): submit `jobs/examples/demo_base_dado_batch.json` against an allowlisted disposable base@1 design and verify its reports.

## First real-Fusion demonstration (2026-10-14, Fusion 2705.1.30)

Job `vd-20261014T230957-dc2edb` on `v5-g3-base` (`urn:adsk.wipprod:dm.lineage:_x75dtN8TEGrSBPecduzaw`):
**7/7 steps PASS**: baseline 59/59 shelf 1175.4; dado 6 -> 10 read back 10; 59/59 shelf 1183.4; restore 6 read back, 59/59 shelf 1175.4; audit 2/2, timeline restored, counts unchanged; counts 16/8/9/28 throughout; no open edits. The design was not saved.

The runner's G3 reports were re-checked by an independent verifier (every `Cab_*` value recomputed): baseline and restored TXT are byte-identical (`305168a6...`) to the manually verified F1 baseline report, the 10 mm TXT is byte-identical to the manual F1 10 mm report (`1f28c90a...`), and the audit results equal the manual F1 audit.

Real-Fusion safety probes: edit on a non-allowlisted design -> REFUSED; wrong expected shelf length -> FAIL (real verdict 59/59 PASS, so completion was not treated as success); reused job id -> rejected at submit (exit 2); a stray copy of an executed job placed directly in the inbox -> refused by the runner (`DUPLICATE refused`).

**Deviation:** Fusion Personal's 10-editable-document limit prevented creating a new disposable design, so the demo used the G3 test design `v5-g3-base` (created for G3 testing in the same session), allowlisted explicitly; the runner never saves, so the saved F1 version is unchanged.

### Measured timings (actual, not estimated)

| Item | Time |
|---|---|
| Runner start-up (add-in `run`) | 5.7 ms / 3.7 ms (two starts) |
| Job submission (CLI, validate + atomic queue write) | 7-8 ms |
| `ping` round trip incl. pickup | 0.26 s |
| Parameter edit + Fusion regeneration | 66.4 ms (6 -> 10), 75.0 ms (10 -> 6) |
| Measurement (G3 validate + reports) | 60-62 ms |
| Independent cut audit | 26.7 ms |
| Complete 7-step batch inside Fusion | 458.7 ms |
| Complete batch, CLI submit to result | 1.34 s |

Earlier Computer Use workflow, from the timestamps of consecutive real reports (each cycle = parameter edit + script-path check + run + dismiss + verify): F1 58.6 s mean (n=7), F2 69.2 s (n=8), F3 63.9 s (n=5); the F1 dado 10 mm -> restored pair took 86 s between reports. An automated edit + measure cycle took 0.13 s (73.1 + 60.3 ms), i.e. roughly 440-520x faster per cycle on these runs. The add-in start-up still needs one manual toggle per Fusion session.

## Limitations

* The add-in must be started manually once per Fusion session (no run-on-startup by default).
* Only `mm` user parameters with plain constant expressions and configured bounds can be edited.
* No build, save, save-as, close or reopen commands (save/reopen tests still need a human or a later, separately reviewed command).
* Validated on the base@1 fixture only; tall/overhead jobs are expected to work through the same G3 code but were not run through the runner.
* Protected-design ids are not yet populated in `config.json`; mutation is still impossible on them because only allowlisted designs can be mutated.
* Fusion Desktop integration tests are not part of cloud CI (no Fusion runtime there).

## M2.1 profile fixture (offline candidate)

`BuildArrangement` also accepts the exact request in `jobs/requests/profile_fixture_request.json`.
It selects a trusted built-in fixture, not arbitrary profile JSON, expressions or code.
The two resolved `PanelProfile` objects feed CAD expectations and DXF unchanged: an
E1.1-sized rounded outline and a relieved through-slot panel with top pocket and bottom blind hole.
XY loops are fixed; only `Profile_Thickness` is newly parametric (18 -> 20 -> 18 mm).
20 mm is a geometric test, not new material/joint qualification. Invalid 5 mm thickness
is refused before mutation. Overlapping/touching feature bounding rectangles, overlapping
panel bounds and ambiguous probes are unsupported and refused before CAD construction.
Cuts set exact participant bodies, verify material removed and unchanged mates, and read
stable feature attributes plus affected bodies without timeline movement. This does not
claim configured participant-list persistence. Missing evidence cannot pass.
The existing owned unsaved-session, no-retry/no-save and stop-on-failure rules apply.
New Fusion behaviour remains UNKNOWN until owner-approved deployment and live qualification;
all existing box arrangements and the earlier rounded-panel parameter path are unchanged.
