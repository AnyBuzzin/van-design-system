## Summary

Add optional explicit-mm bed width/length/height and kitchen X/Y inputs to the
existing FirstInteriorDemo runner job. Reject envelope violations and overlapping
occupied furniture bounds before CAD operations. Reuse the same cabinet,
parametric panel adapter, queue and guarded save path; no new service or UI.
Targets feature/runner-demo-workflow; existing draft PRs remain unmerged.

## Changed contracts and safety

Omitted layout_mm retains the original 24-parameter geometry. Explicit layout_mm
adds Bed_Width while preserving existing parameter names, stable IDs, topology
and explicitly owned cabinet cuts. Kitchen placement translates its panels and
cuts together. Failed preflight is terminal and cannot be saved. Bounds checking
includes door depth and conservative under-bed occupied space.

Add a narrowly guarded persistence command: only an explicitly configured,
unprotected, active saved demo with no unsaved changes may be closed/reopened.
Compare raw BRep bounds/volumes, parameters, counts and stable cloud version;
never save/discard a dirty target. Requires runner 0.3.0 and one add-in reload.

## Tests and actual Fusion results

- Offline: 68 runner tests, five layout tests, five foundation tests PASS.
- Full prototype suite: 114 tests; same three existing CRLF spec-fixture
  subtest failures. Exact failure log retained; no clean full-suite PASS claimed.
- Fusion 2705.1.30: initial dirty-demo persistence request correctly REFUSED.
  After the user saved that demo to version 2, targeted close/reopen PASS with
  unchanged measured geometry/parameters/identity/version and other documents.
- Deliberately invalid Kitchen_Y=3000 REFUSED for bed overlap. Independent
  runner census confirms zero parameters/occurrences/timeline items; no build/save.
- Valid bed 1500 x 2000, deck underside Z=650; kitchen X=200/Y=600:
  171/171 actual BRep checks PASS across nine stages, zero interference.
  Bed length and kitchen X/Y edits/restores also pass without count changes.
- Fresh presave 19/19 PASS, saved as VanDesign-Configurable-Layout-Demo-20261015
  in Default Project root, version 1, cloud complete and clean. Separate inspection
  confirms 25 parameters / 15 occurrences / 16 components / 49 timeline items.
- Geometry JSONs, refusal evidence, original jobs/results, viewport image and
  packaged SHA-256 evidence are under automation/evidence/configurable-layouts.

## Limits and review

Fixed topology and nominal rectangular envelope only; conservative furniture
bounds are not access/door-motion certification. Envelope-excess refusals are
tested offline, not as a second live invalid case. The prior autonomous demo was
reopened; the new configured layout has not been reopened. No general spec
migration, real vehicle-fit, structural/load/fixing or manufacturing qualification.
Draft for safety/integration review; no merge requested.
