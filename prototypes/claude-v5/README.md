# VanDesign V5 — G0/G1 skeleton + G2 Fusion adapter

Status: **core and tests run and pass outside Fusion (30 tests). The Fusion adapter has NOT been run in Fusion yet.**

## Layout
```
baseline/                    G0: tested V4 rev 2 (.py, .manifest) + SHA256SUMS.txt
VanCabinetJoineryV5/         <- the Fusion script folder (copy this whole folder)
  VanCabinetJoineryV5.py     thin entrypoint (run/stop only)
  VanCabinetJoineryV5.manifest
  cabinet_spec.json          OPTIONAL: overrides defaults on first build (see below)
  vandesign/
    core/         units, Expr (dimension-checked lengths), parameter graph, boxes, frames
    components/   stable IDs, Panel, DadoOperation, Constraint, AssemblyDefinition
    schemas/      CabinetSpec (typed, versioned, hashed)
    modules/      cabinet.py: CabinetSpec -> AssemblyDefinition (the ONLY place formulas live)
    verification/ validate(): PASS / FAIL / UNKNOWN from measured solids
    cad/          protocol + shared preflight
    cad/fusion/   adapter.py, runner.py   <- only code that imports adsk
tests/           unit tests, V4-equivalence, simulated-CAD failure modes
```

## Install (Fusion)
1. Utilities → Scripts and Add-Ins → Scripts tab → green **+** → *Add existing script* → pick `VanCabinetJoineryV5`.
   (Folder, `.py` and `.manifest` share the name `VanCabinetJoineryV5`.)
2. Open a NEW, EMPTY design with design history ON. Run the script.
3. Optional first-build overrides: create `cabinet_spec.json` next to the script:
```json
{"schema_version":"0.1","module":"base_cabinet@1",
 "parameters":{"shelf_count":2,"height_mm":1800}}
```
   Omitted fields keep their defaults. Shelf/door counts are fixed at generation.

## Fusion smoke test (do this first)
1. Run on an empty design → expect `RESULT: PASS`. A JSON report is written to `reports/`.
2. Modify → Change Parameters: set `Cab_Dado_Depth` = 10 mm. Run the script again (it re-measures; nothing is rebuilt) → PASS, `Cab_Shelf_Length` = 1183.4.
3. Repeat for `Cab_Width` = 1000 (983.4), and `Cab_Ply` = 15 (1189.4).
4. Save, close, reopen, run again → still PASS (stable IDs and spec are stored in the file).
5. A **FAIL** names the exact check. **UNKNOWN** means evidence was unavailable (e.g. a Fusion call failed) — it is never reported as PASS. Send me the report text for either.

## Tests (no Fusion needed)
```
cd tests
python -m unittest discover -v
```

## What changed vs V4 (behaviour preserved)
- Same parameter names (`Cab_*`), same panel layout, same derived formulas — a test imports the archived V4 script and checks every derived value matches for 0–4 shelves and fixtures A–D.
- Formulas now live once, as `Expr` objects: evaluated in Python for validation and rendered into Fusion parameter expressions, so they cannot drift apart.
- Every cut must name its target; the adapter resolves every target to exactly one body **before the first cut** and always sets `participantBodies`.
- Components carry a stable ID attribute (`VanDesign/stable_id`); lookup never uses display names.
- Validation adds BRep point probes (groove empty, open at front, solid on the other sides) plus checks that the shelf volume is untouched.

## Notes on the architecture doc
- Its provenance warning says the attached V4 lacks `participantBodies`. The V4 rev 2 you ran **does** set it (`baseline/…rev2.py` line 216), so the archived baseline is the right one.
- Hashes in `baseline/SHA256SUMS.txt` are of the file as delivered in this chat. If you changed it locally, re-hash yours.
