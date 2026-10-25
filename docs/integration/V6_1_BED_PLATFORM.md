# V6.1 — standalone bed-platform geometry

Owner-approved bounded offline implementation, based on develop4c82a0a. **Unqualified geometric bed furniture:** no load capacity, lateral stability, fastening, secure vehicle anchoring or manufacturing suitability established.

## Contract and implementation

`BedPlatformSpec` in `src/vandesign/schemas/bed_platform_spec.py` uses separate schema `vandesign.bed-platform/1` and module `bed-platform@1`. Required envelope keys: schema_version, module, parameters. Omitted parameter values use the approved defaults; unknown/duplicate keys, unsupported versions/types and nonfinite values are refused. Canonical normalized JSON defines a separate bed SHA256 identity; cabinet schemas/hashes are unchanged.

`build_bed_platform(spec)` in `modules/bed_platform.py` returns existing `AssemblyDefinition`, using `Panel`, `BoxExpr`, parameter expressions and shared preflight. No new geometry engine, CAD adapter, workflow or Runner command. Bed_Height is finished deck-TOP height above local Z=0, unlike the experimental interior placement convention. The experimental interior source remains unchanged.

| Input | Default / scope |
|---|---|
| width_mm / Bed_Width |1400 mm, X across|
| length_mm / Bed_Length |1900 mm, Y along|
| height_mm / Bed_Height |700 mm, Z up to deck top|
| ply_mm / Bed_Ply |18 mm only, uniform nominal plywood|

Finite positive inputs have a10000mm numerical ceiling (a software bound, not an engineering qualification). Shared assembly constraints require width>thickness, length>2×thickness and height>thickness. Bed_Support_Height is derived as height−thickness. Both thickness constraints preserve the18mm restriction during shared validation. Impossible configurations fail before CAD compilation.

| Stable ID | Origin XYZ mm | Size XYZ mm | Default blank |
|---|---|---|---|
|bed.deck.001|0,0,H−T|W,L,T|1400×1900×18|
|bed.front.001|0,0,0|W,T,H−T|1400×682×18|
|bed.rear.001|0,L−T,0|W,T,H−T|1400×682×18|

Exactly three panels, one body/component per panel when compiled through the existing adapter; zero cut operations. Supports contact the underside of the deck over positive face areas; no solid overlap. These are geometric contacts, not qualified joints. IDs do not depend on labels/dimensions. One standalone assembly per fresh document; multi-instance placement is excluded.

## Preview usage

```text
python -m vandesign.panel_preview docs/integration/v6-1-bed-evidence/bed-spec.json NEW_OUTPUT
```

The existing entry point explicitly dispatches only the new module to the bed loader/builder. Existing `panel_rows` resolves the same geometry boxes; no duplicated sizing formulas. Deck axes X/Y/thicknessZ; support axes X/Z/thicknessY. Stable-ID sorted CSV/JSON, quantity1 per panel, fixed numeric formatting. All thicknesses are nominal18mm, not measured stock. [Example CSV](v6-1-bed-evidence/preview/panels.csv), [JSON](v6-1-bed-evidence/preview/panels.json).

Bed previews deliberately report UNKNOWN for measured evidence. Bed `--report` is refused explicitly: cabinet historical-report semantics are not repurposed and no bed live-report protocol is claimed. Cabinet report validation, accepted boolean/numeric evidence semantics and outputs are unchanged. Shared runtime package version0.5.0/cabinet generator identity remain unchanged; the bed preview identifies `vandesign.bed-platform@1`. This is development code, not a release. Future bed Fusion report/source identity handling must be independently reviewed before live qualification.

## Acceptance and evidence

- PASS: default independent numerical bounds/volumes; three unique semantic IDs; no operations.
- PASS: independent width1500, length2000 and height800 variants; contacts, no overlaps, stable IDs and restoration to original nominal geometry.
- PASS: deterministic regeneration and canonical hashes; integer/float equivalent values normalize identically.
- PASS: invalid input/type/version/duplicate-key/thickness/boundary rejection; shared preflight rejects unsupported thickness.
- PASS: CSV/JSON parity, orientation, quantity and thickness, including short supports where thickness is not the smallest dimension; spec-only UNKNOWN and unsupported report refusal.
- PASS:236 installed-wheel/offline tests (38 package,119 core/experimental,79 Runner), isolated installed source imports without adsk. Eight accepted cabinet preview files byte-identical.
- Python3.10/3.12 CI: results will be linked in the PR after completion.
- UNKNOWN / NOT RUN: actual bed Fusion BRep, runtime resizing, lifecycle/persistence, live source identity and deployment. No Fusion operation or installation/config change performed.

[Offline evidence and hashes](v6-1-bed-evidence/RESULTS.json). Initial no-build-isolation packaging attempt lacked setuptools in the existing interpreter; normal isolated build succeeded. No production failure or weakened assertion resulted.

## Safety and next boundary

Existing adapter requires a fresh parametric document and is not a general structural reconciler or atomic failed-build recovery mechanism. Live qualification, any deployment, saves and document operations require separate owner approval and a reviewed fixture/backup/stop plan. Both G4 fixtures, PR27/evidence and all existing designs remain untouched. One focused draft PR for independent review; no merge/release or V6.2.

Roadmap requirements remain deferred as already recorded in docs/ROADMAP.md:5/10/12/15/18mm, custom/mixed thicknesses, measured-stock tolerances, interlocking CNC joints, final mechanical fasteners and vehicle anchoring. No premature implementation or physical qualification claim. No layout engine, UI, vehicle-fit system or unrelated refactor.
