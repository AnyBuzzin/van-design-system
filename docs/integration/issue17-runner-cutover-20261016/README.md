# Issue #17 — runner migration evidence for review

**Astra — developer/test submission, 16 October 2026. Operational result PASS for the default smoke; Jack's review and acceptance pending. Keep issue #17 open.**

The owner approved migration of the existing runner to permanent reviewed packages and one new disposable unsaved design. This PR publishes that already-completed work and the owner's GitHub communication instructions; it changes no runtime code and performs no further live operation. Base: `develop` at `65de693ffacd47ad2d76547a09ff21a2dd8319a5`; evidence branch: `codex/issue17-evidence-and-team-workflow`. The tested deployment is identified by the manifests below, not by this later documentation commit.

## Deployment and safety

Only `g3_script_dir` and `demo_package_dir` changed to `%USERPROFILE%\Documents\VanDesign-Runner\deployments\vandesign-0.5.0\VanCabinetJoineryV5` and the sibling `FirstInteriorDemo`. `%USERPROFILE%` is publication notation; the installed values are absolute Windows paths. See [exact old/new comparison and configuration hashes](configuration-verification.json). Private IDs, destination lists and whole configuration files are excluded.

The exact original config and complete add-in backup remain private and unchanged. Original config SHA-256: `ed0d8eb01bd7e3391c6f0469daf687462bf4742c6d9d9c88df7e74bb3aa51fc5`; applied config SHA-256: `70bf4288f224cef35efc1760aae594c54cf39d1676a298aa10956621d81d8378`. All other settings and runner source were preserved. The original Untitled remained valid, unsaved and unmodified; the new runner-owned test document was left open and unsaved. No existing design was modified, saved or closed.

**Failure retained:** direct invocation of the add-in's Python lifecycle resumed its heartbeat but did not process the first ping. The ping was cancelled unclaimed by the existing CLI. The original config was restored exactly; a native Fusion `Application.scripts` lifecycle reload recovered normal queue processing. A second approved cutover using that lifecycle passed. The native start request returned before `isRunning` became true; subsequent fresh queue results, not that immediate flag, establish recovery. See [timeout](first-ping-timeout-state.json), [rollback](rollback.json), [recovery ping](jobs/vd-20261016T005837-f61490/result.json), [second cutover](cutover-attempt2.json) and [final heartbeat](final-heartbeat.json). No interrupted mutation was replayed, history cleared or journal reset.

## Acceptance evidence

| Criterion | Observed result | Evidence |
| --- | --- | --- |
| Runner responds after migration | PASS | [Ping](jobs/vd-20261016T005902-e19a24/result.json), [read-only inspection](jobs/vd-20261016T005903-f527d4/result.json) |
| Fresh runner-owned unsaved design | PASS | [Create result](jobs/issue17-create-20261016-005940/result.json) |
| Five-stage actual BRep smoke | 95 PASS, 0 FAIL, 0 UNKNOWN | [Original raw report](jobs/issue17-build-20261016-010000/evidence/interior_20261016_005958.json), [runner result](jobs/issue17-build-20261016-010000/result.json) |
| Bed edit/restore | 1900 → 1800 → 1900 mm, PASS | Same raw report |
| Cabinet width edit/restore | 1200 → 1100 → 1200 mm, PASS | Same raw report |
| Restoration and unintended interference | Exact baseline measured checks/parameters restored; zero interference each stage; counts stable | [Recorded verification summary](verification-summary.json) |
| Live canonical package provenance | 24 cabinet and 26 demo modules match permanent roots and source hashes | [Cabinet](cabinet-provenance.json), [demo and final document flags](demo-provenance.json) |
| Existing document safety | Original remained valid, unsaved and unmodified; only the new demo is modified | [Before](observe-before.json), create/build results, final provenance |
| Queue/journals/history | No pending jobs/restore entries; historical records unchanged | [Verification summary](verification-summary.json) |
| Explicit combined-interior cut-participant readback | UNKNOWN / not performed; saved-target safeguards not bypassed | Separate earlier cabinet audit remains scoped evidence, not an interior audit |
| Cloud save/reopen | NOT RUN / not requested | No save/close operation in this milestone |

Fusion 2705.1.30; runner 0.4.0; canonical package 0.5.0; generator `vandesign.cabinet@0.5.0`; schema identity remains 0.1. Geometry jobs used the existing runner queue. Fusion's existing built-in local Python API connection was used for read-only provenance and add-in lifecycle control; no new runner, service or installed helper was added.

## Package identity

| Artifact | SHA-256 |
| --- | --- |
| Reviewed wheel | `549ff8843b8966e7339181e9a75d835c8cb5e1d3ac5b20a2954c7adc2bcef80f` |
| [Cabinet deployment manifest](packages/VanCabinetJoineryV5-DEPLOYMENT.json) | `9dca986105401b2b3c506b151d5d21684057a8f8cc2eece85752705ce66bcb2a` |
| [Interior deployment manifest](packages/FirstInteriorDemo-DEPLOYMENT.json) | `c5fee18088bf2518f6679df134c7f5eefa5dffbbd0057aad030639a717d1380e` |

All 31 covered files per bundle matched. Only manifest-covered files plus the original manifest were copied to permanent folders; prior reports/editor settings/bytecode caches remained untouched at their historical location. [Staging verification](packages/STAGING-VERIFICATION.json) records both clean inventories. The private original runner ZIP hash is recorded in configuration-verification.json; that ZIP is not uploaded because it includes cloud metadata.

## Publication verification and review request

[PUBLICATION.json](PUBLICATION.json) maps original-byte hashes to published-byte hashes and identifies every transformation. The raw interior report and deployment manifests are byte-for-byte originals. Normalized job/provenance copies omit cloud destination lists and replace the user-home prefix; measured values, outcomes and module source hashes are unchanged. Original artifacts remain private and immutable. Do not compare a sanitized file to its original-byte hash.

[Publication validation](publication-validation.json) rechecked the existing 95 checks, restoration, module-to-manifest hashes and published artifact hashes. **No successful Fusion tests were repeated.** CI on this documentation/evidence PR is separate offline validation, not another live test. Developer verification is not independent acceptance.

**Jack:** review the raw report, deployment/provenance evidence, first-failure/rollback history and stated exclusions; record acceptance or precise changes required in issue #17. **ChatGPT:** provide independent technical advice through GitHub. The owner retains approval of merges, releases and new live/design scope. No manufacturing or full G3/G4 qualification is claimed.

**Next recommended milestone after #17 acceptance:** issue #4's remaining overhead F3 depth/height edit/restore, intended range failure, exact two-cut ownership audit and explicitly approved clean persistence check, plus an F0 evidence-gap disposition. Reuse accepted base/tall evidence. This identifies the existing roadmap step; it does not authorize a new saved-design operation or start another test campaign.
