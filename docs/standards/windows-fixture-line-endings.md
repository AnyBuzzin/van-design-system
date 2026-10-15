# Windows CRLF fixture checkout issue

Tracked separately as [issue #11](https://github.com/AnyBuzzin/van-design-system/issues/11).

The earlier Windows prototype runs reported three failing subtests in
test_spec_files.SpecFiles.test_each_file_loads_and_matches_profile (base, tall,
overhead). The only failing assertion was absence of CR bytes. Git's committed
fixtures are LF; core.autocrlf converted their working copies to CRLF.

Original failures remain preserved in
automation/evidence/configurable-layouts/prototype-tests.txt and earlier evidence.
No geometry, profile values, frozen archive or test assertion needs changing.

Minimal fix: .gitattributes forces LF only for prototypes/claude-v5/specs/*.json.
Normalize those three working copies back to committed LF bytes and run only
test_spec_files.py. The vehicle milestone records this focused result separately;
it does not repeat the G3/G4 campaign or relabel old failed logs as passing.
