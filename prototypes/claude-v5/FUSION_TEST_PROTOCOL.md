# Fusion V5 smoke-test protocol

**State:** ready for the first diagnostic run, **NOT Fusion-verified**. Issue [#2](https://github.com/AnyBuzzin/van-design-system/issues/2), Draft PR [#3](https://github.com/AnyBuzzin/van-design-system/pull/3).

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
| E | Save, close and reopen; measure, then `Cab_Dado_Depth=8 mm` | 1179.4 mm | 7.7 mm |

Check the following derived values in reports:
- A: `Cab_Shelf_X=12.3 mm`, `Cab_Shelf1_Z=416 mm`
- B: `Cab_Shelf_X=8.3 mm`
- D: `Cab_Shelf_X=5.3 mm`, `Cab_Compartment=402.5 mm`, `Cab_Shelf1_Z=417.5 mm`, `Cab_Slot1_Z=417.25 mm`

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
| A | UNKNOWN | — | Not yet run in Fusion |
| B | UNKNOWN | — | Not yet run in Fusion |
| C | UNKNOWN | — | Not yet run in Fusion |
| D | UNKNOWN | — | Not yet run in Fusion |
| E (reopen/edit) | UNKNOWN | — | Not yet run in Fusion |
| Manual cut targeting | UNKNOWN | — | Not yet inspected |

**G2 must not be marked complete solely from CAD-independent tests.**
