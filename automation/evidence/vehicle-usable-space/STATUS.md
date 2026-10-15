# Vehicle usable-space milestone — 2026-10-15

Fusion 2705.1.30 / runner 0.4.0. Feature branch vehicle-usable-space is based on
feature/configurable-interior-layouts. Existing draft PRs remain unmerged.

## Previous milestone completed

PR #10 is open/draft/unmerged and its remote head f0826c6 matches the previous
local and pushed branch; its evidence remains committed unchanged.
vd-vehicle-prior-persistence-20261015 PASS: configurable layout cloud version 1
was clean, measured, closed and reopened without saving/discarding edits.
Bounds, volumes, parameters, counts and identity/version match; maximum corner
change 0 mm. Parameters also match its prior saved evidence. Other designs were
left untouched. Only this explicitly approved clean target was reopened.

The three historical Windows CRLF fixture failures remain preserved in earlier
logs and are tracked separately as issue #11. Narrow .gitattributes LF checkout
rule added for the three canonical profile JSON fixtures; their contents equal
the already committed LF bytes. Focused test_spec_files passes all three variant
subcases. No archive, profile values or test assertions changed.

## Live invalid demonstration

vd-vehicle-invalid-create-20261015 created a fresh dedicated empty design.
vd-vehicle-invalid-build-20261015 was REFUSED before any CAD operation:
Kitchen_X=400 yields a 482 mm aisle, below the required 600 mm. Independent
inspection vd-20261015T020659-396c17 confirms zero parameters, occurrences and
timeline items, only the root component. The refused tab remains empty/unsaved;
it was not discarded or saved. Wheel-arch collision refusals were tested offline,
not as a separate live invalid case.

## Live valid demonstrations and image review

First valid build/save/image (vd-vehicle-valid-*) passed geometry, but inherited
a low side camera. Saved VanDesign-Vehicle-Space-Demo-20261015 version 1 remains
untouched. Source now sets an isometric camera only at the end of a fresh
vehicle-profile build. A second fresh build/save/image (vd-vehicle-view-*) provides
the final readable viewport; no earlier saved model was modified for the image.

Final saved document: VanDesign-Vehicle-Space-View-Demo-20261015, Default Project
root, version 1, cloud complete, saved and unmodified. Lineage
urn:adsk.wipprod:dm.lineage:qqe9qLvAR7mz1L7RpvEkEA.
Separate saved inspection: vd-20261015T021051-beb4c0.
31 parameters, 17 panel occurrences, 18 components including root, 55 timeline items.

| Actual BRep item | Min XYZ mm | Max XYZ mm |
| --- | --- | --- |
| Van floor | 0, 0, 0 | 2100, 4600, 18 |
| Left wheel arch | 18, 3000, 18 | 268, 3800, 318 |
| Right wheel arch | 1832, 3000, 18 | 2082, 3800, 318 |
| Bed deck | 200, 2582, 750 | 1900, 4582, 768 |

Kitchen occupied bounds: X=100..1300, Y=500..1068, Z=18..868. Bed 1700 x 2000
with underside Z=750. Shell height 2200. Each arch measures 250 x 800 x 300.
Measured kitchen aisle 782 mm >= 600; bed underside 432 mm above arch tops;
prohibited furniture/arch overlaps 0. Both arches are present and individually
measured; the far arch is occluded by the bed in the isometric picture.

Final build: 198/198 checks across nine actual-BRep baseline/edit/restore stages,
zero interference throughout. Bed length, cabinet width and kitchen X/Y edits
restore baseline parameters/counts. Fresh presave: 22/22 checks PASS. Raw body
corners/volumes and measured usable-space checks are recorded in every stage.
Existing document snapshots match before/after the final create/build/save,
including the earlier unsaved v5-g3-tall, original demos and empty refusal tabs.
Snapshots compare names/valid/saved/modified flags, not whole protected BRep hashes.

## Focused tests and remaining limits

69 runner tests, five vehicle-space tests, five legacy layout tests, five foundation
tests and one fixture test (three variant subcases) PASS. Logs retained here.
Full G3/G4 campaigns were not repeated. The source retains CAD-neutral math,
existing IDs/parameter names and explicitly owned cabinet cuts; no new boolean cuts.
Original jobs/results/evidence and actual viewport images are preserved alongside
a ZIP with the existing packager's SHA-256 manifest.

Simplified rectangular envelope and box-shaped arches only; not measured vehicle
fit. Arches are floor/side anchored with shared dimensions and independent Y
positions. Aisle is the straight strip beside the kitchen, not a certified route
through the rear bed or a door/headroom/turning/access analysis. Arch space may
occupy empty under-bed volume but not structural material or cabinet volume.
New vehicle demos have not been reopened; the prior configured demo was.
Bed support positioning is fixed at platform ends; layouts colliding with arches
are refused rather than automatically redesigned. No production, manufacturing,
structural, fixing, electrical, CAM or road-legal approval is claimed.
