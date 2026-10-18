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
1100 mm base cabinet, plus six separate reference objects. The 1784 x 3044 x
2025 mm clear box is UNMEASURED; two 196 x 800 x 300 mm arches at Y600 are
arbitrary test assumptions. Guides sit outside the clear box, with no roof.
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
