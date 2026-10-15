# Fusion V5 smoke-test protocol

**State:** Fusion smoke-test scenarios A–E passed in user-run Fusion 360 v2705.1.30 reports (58/58 automated checks each run); Fusion API cut participant audit passed for both grooves; optional manual UI/visual inspection remains unperformed. This is a smoke-test milestone, not manufacturing qualification. Issue [#2](https://github.com/AnyBuzzin/van-design-system/issues/2), Draft PR [#3](https://github.com/AnyBuzzin/van-design-system/pull/3).

## Preparation
1. Checkout `feature/v5-fusion-adapter` and ensure local files are current.
2. Run offline tests from `prototypes/claude-v5/tests/`: `python -m unittest discover -v` (31 expected after report changes).
3. In Fusion, record application version (Help → About) and operating system.
4. Utilities → Scripts and Add-Ins → Scripts → green **+** → **Add existing script**. Choose **the whole** `prototypes/claude-v5/VanCabinetJoineryV5/` folder (contains matching `.py`, `.manifest` and `vandesign/`).
5. Create a **new empty design** with design history enabled; save as `v5-smoke-test`.

## Fixtures (same design)
After every parameter edit, rerun the script, which should switch into **measure** mode, without rebuilding the cabinet.

| Step | Configuration changes | Shelf length | Shelf penetration at each side |
|---|---|---:|---:|
| A | Default W=1200 / Ply=18 / Dado=6 / End clearance=0.3 mm | 1175.4 mm | 5.7 mm |
| B | `Cab_Dado_Depth=10 mm` | 1183.4 mm | 9.7 mm |
| C | `Cab_Width=1000 mm` | 983.4 mm | 9.7 mm |
| D | `Cab_Width=1200 mm`, `Cab_Ply=15 mm` | 1189.4 mm | 9.7 mm |
| E | Save, close and reopen; measure, then `Cab_Dado_Depth=8 mm` | 1185.4 mm | 7.7 mm |

Check the following derived values in reports:
- A: `Cab_Shelf_X=12.3 mm`, `Cab_Shelf1_Z=416 mm`
- B: `Cab_Shelf_X=8.3 mm`
- D: `Cab_Shelf_X=5.3 mm`, `Cab_Compartment=402.5 mm`, `Cab_Shelf1_Z=417.5 mm`, `Cab_Slot1_Z=417.25 mm`
- E after editing dado to 8 mm (plywood remains **15 mm**): `Cab_Shelf_X=7.3 mm`, `Cab_Shelf_Length=1185.4 mm`. The previous expected length **1179.4 mm** incorrectly assumed 18 mm plywood; it is not applicable to the sequential A–E fixture.

## Required evidence
Every result must be `PASS` to count as verified. `FAIL` or `UNKNOWN` is not releasable; include diagnostic messages. Reports contain live `Cab_*` parameter values, document name, Fusion version, bounding boxes, solid volume, groove containment probes, shelf unmodified check, and interference.

Files should appear under the installed script directory at `reports/report_*_{build|measure}.json` and corresponding `.txt`. These are normally ignored by Git, so deliberately commit redacted reports to `docs/test-results/` only when intended.

## Cut targeting and optional visual checks
1. **PASS — Fusion API participant audit (alternative to manual Edit Feature inspection):** a read-only audit inspected `dado.shelf1.left` and `dado.shelf1.right`. Each had `Operation Cut: True`, exactly **one** participant: respectively `panel.left.001` / `panel.right.001`. **The shelf is not a cut participant.** The audit reported `Timeline moved back to end: True` and `OVERALL: PASS`. [Original audit text](docs/test-results/cut_audit_20261014_174320_047406.txt).
2. **Optional not manually inspected:** Hide shelf and doors to view the grooves open at the front (BRep `front_open` probes passed in all smoke tests).
3. **Optional not manually measured:** Inspect → Measure gap to groove far wall: expected 0.3 mm (automated checks passed).

If `Build failed`, do **not** save the partial design. Close and start from an empty design. Capture exception text, screenshot and Text Commands.

## Results
| Check | PASS / FAIL / UNKNOWN | Measured shelf length | Report filename / notes |
|---|---|---|---|
| A | PASS (58/58) | 1175.4 mm | User pasted complete initial `build` TXT report, Fusion 2705.1.30, document initially `Untitled` |
| B | PASS (58/58) | 1183.4 mm | `report_20261014_030324_809979_measure.txt` |
| C | PASS (58/58) | 983.4 mm | `report_20261014_030611_667348_measure.txt`; document saved as `v5-smoke-test` |
| D | PASS (58/58) | 1189.4 mm | `report_20261014_030749_282208_measure.txt` |
| E (after reported reopen, before edit) | PASS (58/58) | 1189.4 mm | `report_20261014_030933_513529_measure.txt`; `measure` mode recorded, but report alone cannot independently establish close/reopen |
| E (after edit, dado=8 mm, ply=15 mm) | PASS (58/58) | 1185.4 mm | `report_20261014_031006_041028_measure.txt`; left/right insertion 7.7 mm; zero interference |
| Fusion API cut participant targeting | PASS | — | `docs/test-results/cut_audit_20261014_174320_047406.txt`; only intended side-panel body per cut; timeline restored |
| Manual Edit Feature UI inspection | NOT RUN (optional) | — | Could not open feature dialog; direct API inspection supplies the participant check instead |

**Evidence limits:** All five scenarios are evidenced by user-supplied real-Fusion text reports, not just CAD-independent tests. Tests E's save/reopen sequence is reported by the user workflow; the text report alone does not independently prove an app-close event. Machine-readable JSON reports have not yet been committed. Cut participant targeting was verified through a separate read-only Fusion API audit; manual UI inspection is not claimed. **G2 smoke tests A–E and the cut-participant verification now PASS.** This is not proof of arbitrary configurations or manufacturing qualification. Do not mark the adapter production-ready solely on these smoke tests.
