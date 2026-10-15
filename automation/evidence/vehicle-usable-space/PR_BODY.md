## Summary

Add basic usable vehicle-space constraints to the existing interior demo: explicit
van width/length/height, two parametric rectangular wheel arches, and a required
clear kitchen aisle. Reuse the existing panel/cabinet/joinery generator and queue;
no planner, UI, vehicle database, exporter or new automation framework.
Targets feature/configurable-interior-layouts; prior draft PRs remain unmerged.

## Contracts and safety

Optional vehicle_mm adds strict finite-mm inputs and two stable arch IDs. Legacy
jobs and document parameter sets remain compatible. Preflight refuses cabinet
occupied-volume/arch intersections, bed structural-material/arch intersections,
envelope excess and insufficient aisle width before CAD. Arches can fit into free
under-bed space. Actual BRep bounds recheck these constraints before save.
Existing cabinet cuts/participants and body ownership are unchanged.
Runner 0.4.0 validates extended report coverage, including kitchen edit stages.
Fresh vehicle builds use a standard isometric camera; old saved designs are not
changed to improve screenshots. Builds/saves still require runner-created sessions.

## Previous milestone and separate fixture issue

Confirmed PR #10 remote head f0826c6 and archived evidence pushed. Automated clean
configurable-demo close/reopen PASS at version 1, unchanged geometry/parameters/
counts/identity. Other documents untouched; no save or discard was needed.
Fixes #11: narrow LF checkout rule for the three canonical profile JSON fixtures;
same committed bytes, no archive/value/test-assertion changes. Historical three
CRLF failures remain archived and documented separately.

## Tests and actual Fusion results

- Focused offline: 69 runner + five vehicle + five legacy layout + five foundation
  + one fixture test (three subcases) PASS. No full G3/G4 campaign repeated.
- Fusion 2705.1.30 / runner 0.4.0: invalid 482 mm aisle REFUSED against 600 mm
  minimum; independent inspection confirms zero geometry/parameters/features.
- Valid 2100 x 4600 x 2200 envelope, two 250 x 800 x 300 arches, bed 1700 x 2000,
  kitchen X=100/Y=500: 198/198 checks across nine stages, zero interference.
  Measured aisle 782 mm and bed underside 432 mm above arch tops.
- Fresh presave 22/22 PASS; final new isometric demo saved in Default Project root
  as VanDesign-Vehicle-Space-View-Demo-20261015, version 1, cloud complete/clean.
  Separate inspection confirms 31 parameters / 17 occurrences / 18 components /
  55 timeline items. Original low-side-view valid demo remains untouched.
- Full raw reports, refusal, reopen evidence, images, test logs, independent
  review and ZIP/SHA-256 evidence: automation/evidence/vehicle-usable-space.

## Limits and review

Simplified unmeasured envelope and box arches; aisle is only a straight kitchen
strip. No route/headroom/door/turning analysis or structural/production approval.
Arch collision refusals exercised offline; the live invalid example exercises
aisle refusal. The new vehicle-profile demos have not been reopened. Conservative
constraints refuse collisions rather than relocating supports automatically.
Draft for review; no merge requested.
