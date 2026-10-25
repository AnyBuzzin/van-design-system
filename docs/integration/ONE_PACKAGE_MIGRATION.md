> **FINAL STATUS (2026-10-15):** This document is the *original pre-deployment review*, preserved for audit. The one-package migration was subsequently included in [merged aggregate PR #14](https://github.com/AnyBuzzin/van-design-system/pull/14) on `develop` at `b799db8`. A real Fusion 2705.1.30 test of the reviewed `base@1` bundle later **PASSED 59/59 at baseline, width edit and restoration**, with exclusive dado participants and 24 in-process source hashes verified; see [final evidence](pr14-checkpoint-evidence/live-20261015/FINAL_REVIEW.md). The **live Fusion runner configuration was NOT migrated** and remains a separate guarded task. G0/deferred G3/G4/G5 release limitations remain open. Sentences below stating that no live Fusion smoke occurred describe an **earlier point in time** and are no longer the current status.

---

# One authoritative Python package — ready for code review

2026-10-15. Child branch feature/single-vandesign-package, based on PR #13 head 9a94947176416531be2305a4c8a2dfe2a8a89d39. Jill's GitHub COMMENT review is retained in package-migration-evidence/jill-review-pr13.json. No merge approval is implied.

## Runtime and compatibility

src/vandesign is the only distributable/runtime source for maintained development and deployments. All 27 V5 Python files were copied from prototypes/claude-v5/VanCabinetJoineryV5/vandesign without changing their code. The historical bundle, launcher, V4 archive and frozen fixtures remain unchanged and are excluded from the wheel. Do not use the historical prototype folder as a supported installation.

DadoShelf keeps its public frozen dataclass fields, constructor, validation conditions/messages, properties and existing five tests. Its properties now evaluate the existing V5 expressions instead of maintaining a separate shelf-length/start formula. The canonical generator, schemas, IDs, parameter names and adapter geometry methods are unchanged. Additional compatibility checks compare legacy API values against canonical parameters and test constructor refusals/frozen state.

Distribution metadata now derives 0.5.0 from the existing V5 runtime __version__. SCHEMA_VERSION stays 0.1, GENERATOR_ID stays vandesign.cabinet@0.5.0; the strict 0.1/0.2 spec loaders and canonical hashes are unchanged. This aligns packaging metadata; it does not establish a release candidate.

Historical protected-source hashes continue to check the preserved archive. The same test now measures protected adapter methods on the installed runtime. A new parity test compares EVERY migrated installed V5 Python file against the preserved source (LF-normalized for Windows checkout only). No golden expectations were regenerated.

## Installed verification

A wheel was built using pip wheel --no-deps, then installed without dependencies into a newly created Python 3.12.14 virtual environment. No editable install or PYTHONPATH was used. python -I tools/check_installed.py confirms site-packages origin, distribution/runtime identity, both legacy and V5 imports, frozen default spec hash and CAD-neutral imports without adsk.

The 119 V5 regression tests now import the installed package. Removed runtime-path insertion from the test helper, interior/G4 tests and isolated mocked Fusion drivers. The only path insertion remaining in those drivers is for test support modules, not either vandesign source tree. The runner's independent vdrunner test support remains unchanged.

Local result: 8 compatibility/deployment tests (including the unchanged 5 legacy tests), 119 V5 regression tests and 69 runner tests PASS: 196 total. Compilation PASS. Raw logs and build/install evidence are in package-migration-evidence. CI now builds a wheel, creates a clean environment and runs all suites plus the isolated import check against that wheel on Python 3.10 and 3.12.

## Fusion deployment

From an interpreter with the reviewed wheel installed:

    python tools/deploy_fusion.py <new-directory>

This creates VanCabinetJoineryV5 and FirstInteriorDemo script bundles from the SAME installed distribution. Each includes a SHA-256 DEPLOYMENT.json covering the launchers, manifest and every package source. Existing output directories are refused. Historical/editable package origins and runtime/distribution version mismatches are refused. Generated copies are deployment artifacts, not separately maintained source.

The supported cabinet launcher is fusion/VanCabinetJoineryV5; it is unchanged from the historical thin launcher. Do not run this unbundled template directly. The maintained demos/FirstInteriorDemo launcher selects src in the repository or its generated local package in a standalone bundle, with reports beside the launcher. It never selects the prototype runtime.

For a FUTURE explicitly selected runner installation, pass the generated VanCabinetJoineryV5 folder as --g3-dir and the generated FirstInteriorDemo folder as --demo-package-dir to the existing install_runner.py; keep the original audit-script configuration. No config-key or runner protocol changes are needed. Do not point new installations at the historical prototype. Existing live installs remain pinned until a reviewed deployment is approved.

Offline tests verify every generated hash, refusal to overwrite, both isolated launchers with mocked adsk, stale-module purging, no-design refusal without CAD work, and both existing runner loaders (_g3 and demo modules) resolving modules from the generated bundle.

**Live Fusion smoke: NOT RUN.** No callable Fusion automation interface is available in this session; the existing installed runner, its configuration, queue and open designs were not changed. Before accepting an actual deployment, run one targeted smoke on a NEW disposable design from these generated bundles, checking default canonical parameters, actual BRep/owned cuts and a scalar edit/restore. This does not require restarting the deferred G3/G4 campaigns. Code is ready for Jill's review; live deployment qualification is still open.

## Gates and delivery

G0 exact executed V4 source provenance remains UNKNOWN/open. G1 package migration is prepared and offline-tested, pending review and deployment smoke; no full gate closure. G3 F0 and deferred overhead F3 checks remain open; broader G4 structural/manual-divergence qualifications remain open. G5 release/report/cut-list acceptance remains open.

This child PR should be reviewed as an addition to PR #13. Do not merge PRs, retarget the original stack or choose both aggregate and sequential delivery routes as part of this milestone.
