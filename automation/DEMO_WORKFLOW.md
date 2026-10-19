# Runner-created demonstration workflow

Extends the existing queue/add-in; no new service or UI. Requires runner 0.2.0
(0.3.0 for [configurable layouts and targeted persistence](CONFIGURABLE_LAYOUTS.md)).
FirstInteriorDemo and BedCabinetComposition are the compiled-in approved entry points. Their trusted
package folder is configured by the installer, never supplied in a job.

Issue #43 adds the unsaved-only `BedCabinetComposition` entry point using the
accepted V6.3 assembly and the same configured package. After the reviewed code
is integrated with green CI, installation/configuration still requires owner
approval and an exact backup. These instructions do not authorise deployment.

For this entry point: `inspect_design {}` first records all open documents and
editable capacity. Jack posts this session baseline before creation. Missing
metadata or capacity, count >= 9, or an unexpected document inventory change
blocks creation. Then use `create_demo_design`, `run_approved_demo` with only
`demo_id` and `entry_point: "BedCabinetComposition"`, `capture_demo_viewport`,
and `close_demo_design {"demo_id":"<create job ID>"}`. Close refuses unknown,
saved, inactive, invalid or previously attempted sessions; it calls close(False)
only on the owned object and verifies the original document census/states.
Restart loses ownership; do not restart to bypass a changed baseline.

The build checks 11 actual solids/net volumes, two exact side-panel cut targets,
empty groove probes, interference and X clearance. Independent width sequences
are Bed_Width 1400→1300→1400 (gap 100→200→100 mm) and Cab_Width
1200→1100→1200 (gap 100 mm). Original parameter expressions are restored.
Participant readback temporarily moves/restores only the owned fixture's
timeline. Each stage is measured; any failure stops without automatic geometry
restoration or close. Preserve the unsaved fixture/result for investigation.
Offline fake-API tests prove control flow, not real Fusion geometry. No live
PASS or screenshot exists until the approved installed Runner executes it.

Issue #46 candidate adds `Cab_Pos_X` / `Cab_Pos_Y` only to the Runner's composed
assembly (defaults 1500/0 mm); standalone generators and the fixed composition
API default are unchanged. The same build job previews and applies 1600/100 mm,
measures translated panels, net volumes and the established groove-boundary
probes, then restores the exact original expressions. A requested 100/100 mm
placement must be refused before either setter, with complete parameter,
timeline and measured-geometry snapshots unchanged. Occupied envelopes reserve
the empty bed underside. Coordinates are finite and bounded to ±10000 mm;
an unsafe X-first intermediate position is also refused without a setter.
The original width sequence remains part of this bounded qualification.
Raw manual parameter edits are not continuously guarded; no access/vehicle-fit
or manufacturing claim follows. Stop on failure; retain partial job results and
the unsaved fixture rather than automatically rolling back or retrying. Candidate
deployment still requires fresh owner approval after review/green integration.

Jobs use the existing `submit <file> --wait` command:

1. `inspect_design {}` lists `cloud_destinations` (accessible projects, root
   folder IDs and document names). Resolve the user's selected project exactly
   and check the intended name. Store the explicit selection as `demo_destination`
   in local config.json: project_id, project_name, folder_id, folder_name.
2. `create_demo_design {}` checks API editable-file capacity, creates/activates
   one new empty design, and returns `demo_id` equal to the create job ID.
3. `run_approved_demo {"demo_id":"<create job ID>","entry_point":"FirstInteriorDemo"}`
   builds and performs the existing five-stage real-BRep edit/restore tests.
4. `save_demo_design {"demo_id":"<create job ID>","name":"<new name>","project_id":"<selected ID>","folder_id":"<selected ID>"}`
   remeasures all geometry and requires the exact verified baseline parameters
   and counts, rechecks capacity and refuses an existing case-insensitive name.
   It calls first-save saveAs only once and waits up to 45 s for cloud completion.
5. Optional `capture_demo_viewport {"demo_id":"<create job ID>"}` stores
   viewport.png in that job's evidence folder. No path can be supplied in jobs.
6. `inspect_design {}` independently confirms saved cloud identity and counts.

Demo commands must not have `target` and cannot appear in test batches. They
reference a live runner-created document object, not a title or cloud ID.
After restart the sessions are forgotten and old documents cannot be adopted.
A failed/interrupted build or uncertain save cannot be retried or saved through
another job; inspect evidence and create a new demo session when appropriate.
Saving an already saved session is refused. Existing documents are never saved,
closed, discarded or assigned editable status by build/save operations. The
separate persistence check can reopen only explicitly approved clean demos.
Existing document validity,
saved/modified flags and names are checked against their creation-time snapshot.

For a reviewed future installation, generate bundles from the installed wheel
using [the single-package deployment procedure](../docs/integration/ONE_PACKAGE_MIGRATION.md).
Use its VanCabinetJoineryV5 folder for `--g3-dir` and FirstInteriorDemo folder for
`--demo-package-dir`, retaining the existing audit location. The migration itself
does not run the installer or change existing pinned configurations.
An already running older add-in needs one stop/start to load upgraded code;
thereafter create/build/save/capture are normal queue jobs without UI clicks.
No Windows permission changes are needed.

Cloud save completion is distinct from reopen/persistence and engineering
qualification. No measured van fit, structural, manufacturing or road-legal
approval is implied by these demonstration checks.

## Development-only Transit envelope (Issue #51)

`TestTransitEnvelope` is a fixed compiled-in entry using only `demo_id` and
`entry_point`. It builds the accepted three-panel bed and an explicitly specified
1100 mm base cabinet, plus five separate reference objects. The 1784 x 3044 x
2025 mm clear box is UNMEASURED; two 196 x 800 x 300 mm arches at Y600 are
arbitrary test assumptions. Floor, right sill and front guide sit outside the
clear box, with no roof or decorative left sill; clear bounds remain unchanged.
Reference roles/IDs are excluded from `furniture_rows()` and furniture-only
interference; arches are checked separately against furniture material/space.
One baseline measurement and one fixed refused bed +600 mm Y preview are checked
for exact before/after geometry, parameter and timeline equality. There are no
width-edit replays, saving, recovery injection or generic job-supplied placements.
Run only after reviewed green integration, owner-approved backed-up installation
and Jack's fresh baseline handoff. Capture then close only this new owned unsaved
fixture. Stop on failure without retry/cleanup; prior failed fixtures stay protected.
Offline tests prove intent, not Fusion solver success. Live qualification and
screenshot remain NOT RUN until separately authorised deployment and execution.


## Under-bed storage box (Issue #56 candidate)

`TestStorageBox` accepts only the existing owned `demo_id` and fixed entry point.
It adds five 18 mm butt-contact panels to the unchanged test scene at X592/Y600/Z0.
Width 600 -> 700 -> 600 stays anchored, with measured 396/396 -> 396/296 ->
396/396 mm arch gaps and 432 mm deck clearance. Eight contacts, bounds, volumes,
interference, cabinet cut ownership and exact restoration are checked. A fixed
+500 mm X preview must refuse without changing parameters, geometry or timeline.
Raw parameter edits are not continuously guarded. There is no qualified extraction
path through the bed supports, load capacity, measured van fit or CNC approval.
Failure stops and retains the new fixture and partial report; no automatic restore,
retry or cleanup. Success follows capture/close-only-owned-unsaved/final baseline.
Owner approval is required BEFORE deployment or ANY live test of this candidate.
Offline tests are not live Fusion evidence. All existing documents remain protected.


## Phase A close-out (Issue #60 candidate)

Offline profile traces compare all base/tall/overhead/bed panels and cuts with
pre-PR49 sketch dimension/constraint output. Only parameter-dependent zero-origin
bindings may differ; fake-API results do not establish real BRep correctness.
`PhaseABaseCheckpoint` uses a fresh Runner receipt and the existing base@1
59-check validator, exact cut participants and width1200 ->1210 ->1200 mm.
It stops on failure without automatic restoration and remains unsaved-only.
`PhaseACombinedPersistence` is a separate fixed entry with explicit `demo_id`,
`name`, `project_id`, `folder_id`. Existing `TestStorageBox` stays unsaved-only.
It compiles/measures the accepted combined scene once (no storage resize replay),
saves once to the uniquely resolved existing folder/name, closes and reopens only
that saved session-owned object, then compares measurements and state. Only the
reviewed absolute1e-6 mm3 volume noise is allowed; all other fields remain exact.
The saved fixture is left open; the report gives its exact name for the owner to
mark read-only. No API read-only transition is claimed or silently attempted.

Persistence requires a fresh Runner session baseline with ZERO documents, then
only the new owned fixture open; saved clean cloud-complete identity/version are
rechecked immediately before close. An existing blank tab is NOT disposable:
G3 previously observed its disappearance during reopen. Owner must manually
preserve/close existing tabs before this procedure; agents never close them.
The read-only zero-document inspection explicitly has no geometry measurements.
Existing in-memory baselines cannot be reset/rebased when documents disappear.
If Fusion creates a blank automatically, refuse; no workaround or tab cleanup.
Stop on unexpected inventory, metadata, geometry, save/reopen or dirty-state
failure; preserve reports/fixtures, with no retry, second save or rollback.
Editable capacity must remain below9 including the new save. Inspect destination
read-only first and obtain clarification if the approved existing folder is not
unique. New installation/configuration changes require separate owner approval.


## Issue #60 owner-priority dimensioned cutaway

`DimensionedCutaway` accepts only a fresh owned `demo_id` and this fixed entry.
It reuses the accepted storage scene, changing only the outside right reference
sill into a full-height wall. Front wall and floor stay outside the clear volume;
a roof sketch outlines 1784 x 3044 at Z2025. Left/rear/roof remain open for viewing.
No negative-X solid guide, added furniture, parameter edit or resize campaign.
The two reference sketches and roof plane add three timeline items (70 total).
Nominal furniture cut-list rows and IDs stay unchanged (16 furniture panels).
A 28 mm sketch-text legend outside the model uses complete PASS BRep observations;
clear-volume values are explicitly specification, arches ASSUMED, vehicle UNMEASURED.
Labels are a static measured snapshot, not continuously updating dimensions.
Sketch text uses Autodesk createInput3/setAsMultiLine; unavailable API or mismatched
text/roof readback stops, preserving partial evidence. No fallback script or retry.
The fixed helper captures cutaway and plan views. Text legibility stays UNKNOWN
until image review; screenshots never replace bounds/volume/ownership checks.
The existing full baseline/capacity and session guards apply with protected tabs
allowed. Save is refused. Capture/close only this new unsaved receipt and compare
final baseline. This does not bypass or resolve the separate persistence blocker.
Reviewed merged green code and NEW owner installation approval are required before
live execution. Failure retains the owned fixture; no automatic cleanup/rollback.
