# Demonstration evidence

User confirmed Fusion editable capacity 3/10 on 2026-10-15.

Offline checks performed on this branch:
- Interior layout/edit tests: 2 passed (`offline-interior-tests.txt`).
- Foundation: 5 passed (`offline-foundation-tests.txt`); PYTHONPATH=src required.
- Prototype regression: 111 tests, three failing subtests in unchanged
  `test_spec_files` due to CRLF in base/tall/overhead JSON fixtures
  (`offline-prototype-tests.txt`). This is not a clean regression PASS.

Implementation review: cabinet panel and cut boxes receive the same translation;
cut participants remain the existing adapter's explicitly resolved target bodies.
The new Fusion path refuses saved, modified, or non-empty documents and never
creates/saves/closes/switches documents. Parameter edits restore in finally blocks.
Missing body, containment or interference evidence never yields PASS.
Existing core, adapter, runner and legacy files remain unchanged.

Real Fusion build and edit verification: PASS for the demonstrated fixture,
Fusion 2705.1.30, report `interior_20261015_005947.json`: five stages, 19 checks
per stage (95 total), no FAIL/UNKNOWN. Bed_Length 1900 -> 1800 -> 1900 and
Cab_Width 1200 -> 1100 -> 1200, with actual BRep checks at every stage.
All stages report zero body interference and unchanged object counts.

Independent report review (`independent-report-review.json`) recomputed all
75 panel-volume observations from direct dimensional formulas, verified stage
coverage, unique IDs, restored parameters and count invariants. Largest volume
error was 4.03e-7 mm3. Review PASS applies to report consistency and these checks.

Live read-only inspection (`runner-postbuild-inspect.json`), job
`vd-20261015T010052-3f76bc`, independently matches the restored baseline:
Untitled, unsaved/modified, parametric, 24 parameters, 15 root occurrences,
16 components including root, 49 timeline items, marker at 49, 15 unique IDs.
No protected design was selected for mutation.

Placement evidence: the executed script checked every actual BRep bounding box
against the expected min/max corners within 0.05 mm. The original report stores
the combined dimension/volume PASS, not raw bounding coordinates; the runner
inspection itself does not measure BRep geometry. Separate raw-coordinate audit
and explicit cut-participant readback for this interior remain UNKNOWN.

Baseline layout (mm, X across / Y front-to-rear / Z up):
- Floor: X 0..1800, Y 0..4000, Z 0..18.
- Bed deck: X 18..1782, Y 2082..3982, Z 700..718 (1764 x 1900 x 18).
- Bed supports: X 18..1782, Y 2082..2100 and 3964..3982, Z 18..700.
- Kitchen including doors: X 50..1250, Y 100..668, Z 18..868.
  Cab_Depth=550 describes the body; door thickness adds 18 to occupied depth.
- Clear longitudinal gap kitchen rear to bed front: 1414 mm; clear side gap
  from kitchen right to inner right sill: 532 mm. These are geometric gaps,
  not certified access/egress clearances.

Ready to save as a demonstration checkpoint. Save/reopen persistence, wider
parameter combinations, door motion/access, measured vehicle fit, fixings,
loads, structural/road-legal/manufacturing suitability remain unverified.
