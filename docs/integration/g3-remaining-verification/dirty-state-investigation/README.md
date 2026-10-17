# Read-only investigation of the dirty flag — 2026-10-17

**Finding: no meaningful model difference was detected in the recorded measurements. The fixture now reports clean. The cause and exact contents of the earlier unsaved state CANNOT BE DETERMINED from the available evidence.** Do not retroactively relabel the guarded refusal or original persistence safety failure.

This investigation used the existing Fusion API with `readOnly:true` and direct property queries. It did not run the geometry validator, parameter edits, cut audit or another persistence test. No save, discard, close, reopen, timeline movement, geometry change or runner configuration change was requested. The current owner instruction supersedes any earlier permission to perform another persistence test.

## Observations

| Question | Finding |
| --- | --- |
| Modified now? | **False** before and after the read-only snapshot. A separate native `fusion_mcp_read` document query also reports `isModified:false`. The prior guarded preflight genuinely recorded true; the flag changed between observations. |
| Correct document? | Sole open, active, saved `VanDesign-G3-overhead-remaining-20261017`. Same cloud identity as the accepted baseline, same version **2**, cloud complete. |
| Parameters/specification? | All **16 recorded user parameter expressions and values** match the earlier post-reopen baseline. Stored specification text is exactly equal. No difference detected. |
| Counts? | Same **16 user parameters, 8 root occurrences, 9 components, 28 timeline items**. Eight component bodies, all solid, zero direct root bodies. Same eight stable body IDs. |
| Geometry? | Each of the eight bodies' recorded component-space bounding boxes and volumes matches the baseline within the existing absolute tolerance **1e-6** (mm for coordinates, mm³ for volume). No measured change detected. This is not proof of exact BRep/topology equality. |
| Timeline? | Marker **28 of 28**, at the end. No suppressed entries observed. The 20 sketch/extrude features expose health value 0 and empty warning/error text. No feature failure or additional timeline item is evident. |
| Configuration? | Unchanged SHA-256 `70bf4288f224cef35efc1760aae594c54cf39d1676a298aa10956621d81d8378`. |

Evidence: [current snapshot](snapshot.json), [baseline comparison](comparison.json), [independent native document-state query](native-document-state.json), [read-only query source](read-only-snapshot.py), [publication hashes](publication.json). The comparison uses the original private `persistence.private.json` **after** snapshot, whose published equivalent remains [here](../persistence.json). Cloud identities are hashed consistently, not changed or substituted with a different fixture.

## What the earlier verification could explain

The earlier approved workflow included temporary parameter edits, a timeline-moving cut audit, saving the restored fixture, and closing/reopening it. Such operations are candidates when investigating document-state changes, but the evidence does not establish that they caused the later dirty flag. The parameter edits/audit preceded the verified clean saved baseline. The original persistence record and its immediate follow-up reported the reopened fixture clean. The later guarded query reported dirty without running another mutation.

The [native log excerpt](log-excerpts.json) records background autosave at **01:29:42 Europe/Dublin**, between the clean post-persistence observation around 01:21 and the dirty guarded query at **01:32:35**. The present snapshot was taken around **01:38:23**, clean again, still version2. The autosave entry is an observed background Fusion action, not an action requested during this investigation. It precedes the dirty observation, so it does **not** prove why the flag subsequently cleared. No observed version change supports a new cloud revision, but unchanged version alone cannot prove that all transient document state was unchanged.

A transient document/session bookkeeping effect associated with verification or background work is **plausible**, given the matching measured model and now-clean state. It is not an authenticated cause. The available logs are not an exhaustive undo/change history and cannot rule out intervening user/application state changes. We cannot responsibly label the earlier unsaved contents conclusively harmless.

## Limits and failed/unavailable reads

- The original baseline records the 16 exposed cabinet parameters, counts, stored spec, body bounds/volumes and validation checks. It does not record every internal Fusion model parameter, camera/display setting, occurrence transform, face/edge topology fingerprint or complete timeline entity state. Current occurrence transforms and topology counts are captured, but their historical equivalence is **UNKNOWN**. Equal bounds/volume do not exclude every possible shape or placement difference.
- Health properties were unavailable on the eight occurrence timeline entries: 16 attribute-read errors are retained in the snapshot. Those entries are not reported as passing feature-health checks. The actual sketch/extrude health reads succeeded. No unavailable property was converted into PASS.
- The dirty flag changing between observations does not prove a correction occurred, identify an actor, or establish the reason. No corrective operation was performed by this investigation.

## Disposition for Jack and the owner

**Classification:** currently consistent with the verified model in the measured scope; original dirty-state cause/content **cannot be determined**. No meaningful change has been demonstrated, and there is no current dirty flag to clear. No automatic save or discard is justified by these findings.

Preserve the prior safety FAIL and guarded REFUSED result. PR #21 remains draft and G3 remains open pending Jack's review. This investigation grants no persistence acceptance, merge, release or G4/G5 progression. Any proposed corrective action requires explicit owner approval first; no corrective action is proposed now. No further persistence test will be attempted under this investigation.
