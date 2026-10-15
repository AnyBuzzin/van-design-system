# Configurable layout and persistence evidence — 2026-10-15

Fusion 2705.1.30, runner 0.3.0. Separate feature/configurable-interior-layouts branch.
No existing draft PR was merged.

## Targeted persistence

Initial persistence job vd-layout-persistence-20261015 was REFUSED because the
autonomous demo had acquired unsaved changes. Nothing was closed or discarded.
The user saved only that demo, creating cloud version 2. Then
vd-layout-persistence-clean-20261015 PASS: before/after measurements match across
all 15 bodies (raw min/max bounds and volumes), all parameters, stable IDs and
counts; cloud lineage/version remain unchanged and document stays clean.
24 parameters / 15 occurrences / 16 components including root / 49 timeline items.
Only that clean explicitly allowlisted demo was closed/reopened. Other designs
were untouched, including unsaved changes in v5-g3-tall.

## Deliberately invalid layout

vd-layout-invalid-create-20261015 created a dedicated empty design.
vd-layout-invalid-build-20261015 was REFUSED: Kitchen_Y=3000 overlaps the occupied
rear-bed envelope. No CAD operation ran. Independent inspection job
vd-20261015T014112-20e033 confirms zero user parameters/occurrences/timeline items,
one root component, unsaved/unmodified. The refused empty tab is left open;
it was not saved or silently discarded. This is an expected refusal, not a
geometry PASS. Envelope-excess cases are tested offline, not separately in Fusion.

## Successful layout

vd-layout-valid-create-20261015 / vd-layout-valid-build-20261015 PASS.
Bed 1500 x 2000 x 18, deck Z=650..668, X=150..1650, Y=1982..3982.
Kitchen occupied X=200..1400, Y=600..1168, Z=18..868.
Clear longitudinal gap is 814 mm (geometric gap only, not access certification).

Nine measured stages, 19 checks each: 171/171 PASS. Bed_Length 2000 -> 1900 ->
2000; Cab_Width 1200 -> 1100 -> 1200; Kitchen_X 200 -> 109 -> 200;
Kitchen_Y 600 -> 550 -> 600. All stages report zero BRep interference and restore
baseline parameters/counts. Requested bed width/height are measured at baseline.

vd-layout-valid-save-20261015 PASS, including 19 fresh BRep checks. Saved as
VanDesign-Configurable-Layout-Demo-20261015, Default Project root, version 1,
cloud complete, clean. Lineage urn:adsk.wipprod:dm.lineage:b2Rkuzt1SDieIGYA4kygmQ.
25 parameters / 15 occurrences / 16 components / 49 timeline items.
vd-layout-valid-image-20261015 captured viewport PNG (visually reviewed).
Independent saved inspection vd-20261015T014320-37b8c1 matches the saved identity,
parameters and counts. Existing-document snapshots remained unchanged.

## Offline checks and limits

68 runner tests, five layout tests, five foundation tests PASS; logs retained.
Full prototype suite ran 114 tests and reports the same three CRLF fixture
subtest failures in unchanged base/tall/overhead JSON files. Not a clean suite PASS.
Raw queue jobs/results/geometry evidence and ZIP with SHA-256 manifest are archived.

This is fixed furniture topology with configurable dimensions/placement, not
general layout optimization or structural regeneration. The new configured
layout has not itself been reopened; the requested prior autonomous demo has.
Bed width/height input geometry is verified, but live edit/restore exercises cover
bed length and kitchen X/Y. More configurations, explicit cut-participant audit,
door/access volumes, measured vehicle fit, loads/fixings and manufacturing
qualification remain unverified. Stored reports/live parameters preserve intent;
there is no new general interior spec/migration framework.
