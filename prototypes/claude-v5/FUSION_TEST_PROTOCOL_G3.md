# G3 real-Fusion test protocol (three cabinet variants)

**STATUS: NOT RUN.** Nothing in this document has been executed in Fusion. Offline simulator,
mock and CI results are development evidence only and are not Fusion verification. Every result
cell below stays `NOT RUN` until a report file from a real run exists.

These are fixture cabinets (test sizes), not engineering sign-off: no van fitment, structural,
load, fixing or manufacturing approval follows from passing them.

Do the steps **one at a time** and send back the requested file/screenshot after each. Do not
hand-edit features. If a build fails part-way: close that design **without saving** and use a
new empty one.

## Expected values (hand-computed from the formulas)

| | base@1 | tall@1 | overhead@1 |
|---|---|---|---|
| Fixture file | `specs/base.json` | `specs/tall.json` | `specs/overhead.json` |
| W x H x D (mm) | 1200 x 850 x 550 | 600 x 1900 x 550 | 1000 x 400 x 350 |
| Shelves / doors | 1 / 2 | 3 / 1 | 1 / 2 |
| `Cab_Shelf_Length` | 1175.4 | 575.4 | 975.4 |
| `Cab_Shelf_X` | 12.3 | 12.3 | 12.3 |
| `Cab_Compartment` | 398 | 452.5 | 173 |
| Shelf Z | 416 | 470.5 / 941 / 1411.5 | 191 |
| Dado operations | 2 | 6 | 2 |
| Named checks in report (current code) | 59 | 112 | 62 |
| Provisional range checks | none | W 300-900, H 1400-2200, D 300-650 | W 300-1500, H 250-700, D 250-450 |

Check counts are snapshots (original checks + `entities.managed_ids` + range checks). Acceptance
is per named check: every check must be PASS. Any FAIL or UNKNOWN is a failure of that step.

## Preparation (once)

1. Copy the whole `VanCabinetJoineryV5` folder from the tested commit (record `git rev-parse HEAD`)
   over your installed script folder. Do not mix files from different commits.
2. Add the audit script: Utilities > Scripts and Add-Ins > Scripts > **+** > add existing script
   `tools/VanDesignCutAuditG3` (a separate script; it is read-only, see Audit below).

## F0 - protect the verified G2 design, then prove G3 reads it unchanged

1. Open `v5-smoke-test`, **File > Save As** a copy named `v5-smoke-test-g3-copy`. All F0 work is on the copy.
2. Run `VanCabinetJoineryV5` on the copy (it measures; nothing is rebuilt). Send the TXT and JSON.
   Expect: `mode: measure`, `design_schema_version: 0.1`, `design_spec_hash`
   `a0a43e005535b33f069dd786dc847682734819a09bd0803650688bb5e4b0a750`,
   `stored_spec.unchanged: true` (raw SHA-256 before == after), all checks PASS,
   `design_counts` identical to the counts from a second run.
3. New **empty** design, **no** `cabinet_spec.json` in the script folder: run once. Expect the stored spec
   to be the legacy 0.1 default (hash above) and PASS. Then repeat G2 tests A-E from `FUSION_TEST_PROTOCOL.md`;
   test E must give shelf length **1185.4 mm** (15 mm ply, 8 mm dado).

## F1 / F2 / F3 - one new, saved design per profile

Variants: F1 `v5-g3-base`, F2 `v5-g3-tall`, F3 `v5-g3-overhead`. For each:

1. **Select.** Copy the profile's fixture to `cabinet_spec.json` beside `VanCabinetJoineryV5.py`
   (replacing any previous one). Open a new empty design (history on) and save it with the name above.
2. **Build.** Run once. Send TXT + JSON. Expect `mode: build`, `design_schema_version: 0.2`,
   `variant`, `profile_version: 1`, verdict PASS, and the expected values in the table.
3. **Reruns.** Run twice more (measure). Expect identical `design_counts` in all three reports
   (user parameters, root occurrences, all components, timeline items) and `entities.managed_ids` PASS.
4. **Scalar edits** (Modify > Change Parameters; one change at a time, run to measure, then restore):
   dado depth 6 -> 10; ply 18 -> 15; width; depth; **height**. Tall: height 1900 -> 2000 must give
   `Cab_Compartment` = 477.5 (ply 18). Each rerun: all PASS.
5. **Out-of-range negative test (tall and overhead only).** Tall: set `Cab_Height` = 2300 mm. Expect a
   named FAIL `profile.tall.height_range` showing observed 2300 and limits 1400-2200, and the parameter still
   2300 (never altered). Overhead equivalent: `Cab_Height` = 800. Restore the value and re-measure: PASS.
   Record this separately from normal runs.
6. **Save, close, reopen, rerun.** PASS; same variant, profile and `design_spec_hash`.
7. **Cut audit.** Run `VanDesignCutAuditG3` (read-only; it temporarily moves the timeline marker and
   restores it). Expect `Features passed: N/N` (base 2/2, overhead 2/2, **tall 6/6**), each with exactly one
   participant = the intended side panel, `Timeline moved back to original position: True`, counts before = after,
   `OVERALL: PASS`. If the restore line says False, do not edit the design; close without saving.
8. Archive all reports (redact private data) under the G3 evidence folder and update Issue #4.

## Evidence table (fill only from real reports)

| Step | base | tall | overhead |
|---|---|---|---|
| F0 G2 copy measures unchanged | NOT RUN | - | - |
| F0 empty design, legacy default + A-E | NOT RUN | - | - |
| Build PASS | NOT RUN | NOT RUN | NOT RUN |
| Reruns stable counts | NOT RUN | NOT RUN | NOT RUN |
| Scalar edits incl. height | NOT RUN | NOT RUN | NOT RUN |
| Out-of-range FAIL (named) | n/a | NOT RUN | NOT RUN |
| Save/close/reopen | NOT RUN | NOT RUN | NOT RUN |
| Cut audit | NOT RUN | NOT RUN | NOT RUN |

## Notes and limits

- One cabinet per Fusion design (global `Cab_*` names and unscoped stable IDs).
- The spec file picks the variant on **first build only**; later runs read the spec stored in the design.
- The audit script is new and has not itself been run in Fusion; compare its output style with
  `docs/test-results/cut_audit_20261014_174320_047406.txt`.
