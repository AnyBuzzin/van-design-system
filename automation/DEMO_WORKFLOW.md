# Runner-created demonstration workflow

Extends the existing queue/add-in; no new service or UI. Requires runner 0.2.0
(0.3.0 for [configurable layouts and targeted persistence](CONFIGURABLE_LAYOUTS.md)).
FirstInteriorDemo is the only compiled-in approved entry point. Its trusted
package folder is configured by the installer, never supplied in a job.

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

Install with the existing install_runner.py `install --upgrade`, retaining the
existing G3/audit locations and adding `--demo-package-dir <repo>/prototypes/claude-v5/VanCabinetJoineryV5`.
An already running older add-in needs one stop/start to load upgraded code;
thereafter create/build/save/capture are normal queue jobs without UI clicks.
No Windows permission changes are needed.

Cloud save completion is distinct from reopen/persistence and engineering
qualification. No measured van fit, structural, manufacturing or road-legal
approval is implied by these demonstration checks.
