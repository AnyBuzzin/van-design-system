# G4 first feature: safe width update of an existing cabinet

**Status:** implemented and demonstrated once in real Fusion (2705.1.30) on the disposable design
`v5-g4-width-demo` (1200 -> 1100 mm). Scope: one existing VanDesign cabinet, width only.
Not manufacturing approval.

## Workflow (runner commands)

1. `preview_width_change {new_width, unit:"mm"}` (read-only) shows, using the verified G3 code only:
   * old/new width, every parameter whose value changes, every panel and dado cut whose box changes
     (and those that do not), old/new design-spec hash;
   * refusal reasons, if any.
2. `update_width {new_width, unit:"mm", expect?}` (allowlisted disposable designs only):
   1. same plan + refusals as the preview; any refusal => nothing is touched;
   2. the existing cabinet must validate (G3 measure, all PASS) before anything changes;
   3. the edit is journalled (original width expression + original stored spec text);
   4. `Cab_Width` is set; Fusion regenerates the existing features (no new features);
   5. the stored spec is written with the G3 adapter's own `store_spec_json` and read back;
   6. G3 validation must PASS with the **new** spec hash, unchanged design counts, expected
      `Cab_Width` / `Cab_Shelf_Length`; the managed components (stable id, entity token, name,
      body count) and the timeline length must be identical to before;
   7. any failure => width and original spec restored, re-validated (hash, width and design counts);
      if that cannot be proven the journal entry stays `restore_unverified` and blocks further edits.

## Refusals ("unexpected modification" detection)

The design must be exactly what its stored spec generates: every managed `Cab_*` parameter's
expression (whitespace-normalised, Fusion re-spaces formulas) and value, no missing or extra
`Cab_*` parameters. Also refused: no-op, outside edit bounds or profile range, rejected by the G3
loader (e.g. `width_fits`), constraint violations, any change to other formulas or to the
panel/cut structure, non-allowlisted or protected designs, an uncertain restore journal.

## Real-Fusion evidence (2026-10-15)

| Job | Result |
|---|---|
| G3 build of `v5-g4-width-demo` from committed `base.json` | 59/59 PASS, hash `0db0be53...` (report `report_20261015_001001_309530_build`) |
| `g4-probe2-width30` preview 30 mm | REFUSED (bounds + G3 `width_fits`), nothing changed |
| `g4-probe2-drift-set` / `-update` / `-restore` | dado 6->10 (simulated manual edit); `update_width` REFUSED with 4 named differences; dado restored, 59/59, original hash |
| **`g4-demo-width-1100`** | **7/7 PASS, 773.6 ms**: 1200 mm 59/59 -> preview -> update (apply 158 ms) -> 1100 mm 59/59, shelf 1175.4 -> 1075.4, doors 595.5 -> 545.5 mm, hash `0db0be53...` -> `8788ca17...`, 8 stable ids identical, timeline 28 -> 28, cut audit 2/2 |
| design saved, closed, reopened; `g4-demo-reopen-check` | PASS: version 3, stored spec `8788ca17...`, 59/59, audit 2/2, each stable id exactly once |

The runner's G3 reports were re-checked by an independent verifier (all 16 `Cab_*` values
recomputed for 1200 and 1100 mm; only `Cab_Width` differs from the build expressions).

## Defects found by the real run and fixed

* `submit` wrote the `queued` state after the job reached the inbox; the runner claimed it at once
  and both processes wrote the state file -> `WinError 32`. State is now written first; atomic
  writes/reads retry transient Windows sharing violations (regression tests added).
* Restarting the add-in did not reload `vdrunner` (Fusion keeps modules across stop/start), so
  new commands were "unknown". The add-in now drops its cached modules on start.
* (Offline) rollback verification did not compare design counts; an extra timeline feature could
  pass as "verified". Fixed with a test.

## Limits

One cabinet, width only; schema 0.1 and 0.2 stored specs are handled by the G3 loader but only
0.2 base@1 was demonstrated. The runner never saves: saving after a verified update is a manual
Fusion action (done once here). No structural changes (shelf/door counts), placement or UI.
