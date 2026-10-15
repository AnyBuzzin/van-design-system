## Summary

Generate the first simplified campervan interior in a dedicated new Fusion design:
parametric rear bed, reused base cabinet as kitchen/storage, and an open rectangular
van envelope. Uses the existing cabinet generator and Fusion adapter unchanged.
Based on verified G4 `ce09a533`; targets `feature/g4-safe-width-update` so the diff
contains only this demonstration.

## Changed design contracts

New millimetre parameters for the envelope, bed and kitchen placement; existing
Cab_* names and cut ownership remain unchanged. Stable IDs identify all 15 bodies.
The manual script refuses saved, modified or non-empty designs. It never saves,
closes or switches documents. No protected design is mutated.

## Tests run (attach logs)

- Interior layout/edit tests: 2 PASS; foundation: 5 PASS. Logs in demos/evidence.
- Prototype regression: 111 tests, three existing CRLF spec-fixture subtest
  failures on Windows. Not a clean regression PASS; exact log retained.
- Independent report review recomputed 75 measured panel-volume observations,
  checked all 95 verdicts and matched the live runner census/restored parameters.

## Fusion 360 run and version

- [x] Tested in Fusion 2705.1.30, dedicated Untitled document.
- Five stages PASS: baseline, Bed_Length 1800, restore 1900, Cab_Width 1100,
  restore 1200. 19 checks per stage; zero interference in all five.
- 24 parameters / 15 occurrences / 16 components including root / 49 timeline items.

## Geometry evidence and regression checks

Original real-Fusion report: demos/evidence/interior_20261015_005947.json.
Live runner result: demos/evidence/runner-postbuild-inspect.json.
Review: demos/evidence/independent-report-review.json and STATUS.md.
Actual BRep bounds were checked within 0.05 mm; volumes agree to under 4.03e-7 mm3.
Original report contains combined bounds/volume verdicts, not raw bound coordinates.
The runner independently reads identity, parameters and census; it does not
independently remeasure the interior BRep. Save/reopen persistence remains UNKNOWN.

## Risks and rollback plan

Fixture only: rectangular nominal envelope, no measured van fit, structural
checks, fixings, services or manufacturing approval. Explicit cut-participant
readback on the combined interior and wider parameter ranges remain unverified.
Build failures can leave partial geometry only in the dedicated demo document.
Do not rerun in a non-empty document or modify protected designs. Keep this PR
draft pending review and remaining acceptance decisions; no merge requested.
