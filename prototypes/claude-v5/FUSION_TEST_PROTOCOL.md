# Fusion V5 smoke-test protocol

**State:** Fusion smoke-test scenarios A–E passed in user-run Fusion 360 v2705.1.30 reports (58/58 automated checks each run); manual cut-target inspection remains unverified. This is a smoke-test milestone, not manufacturing qualification. Issue [#2](https://github.com/AnyBuzzin/van-design-system/issues/2), Draft PR [#3](https://github.com/AnyBuzzin/van-design-system/pull/3).

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

## Manual checks
1. Optional: Inspect dado cut Edit Feature → Objects To Cut; should list **only** its own side-panel body, never the shelf.
2. Hide shelf and doors and verify grooves are open at the front.
3. Inspect → Measure gap to groove far wall: expected 0.3 mm.

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
| Manual cut targeting | UNKNOWN | — | Not yet inspected |

**Evidence limits:** All five scenarios are evidenced by user-supplied real-Fusion text reports, not just CAD-independent tests. Tests E's save/reopen sequence is reported by the user workflow; the text report alone does not independently prove an app-close event. Machine-readable JSON reports have not yet been committed, and manual cut-target inspection is still UNKNOWN. Do not mark the whole adapter production-ready solely on these smoke tests.
