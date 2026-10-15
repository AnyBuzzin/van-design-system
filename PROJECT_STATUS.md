# VanDesign project status

**As of 2026-10-15.** Authoritative integration branch: `develop`, merge `b799db8a73309a9d47a355ec37c955f5e4dc7850`. [Aggregate PR #14](https://github.com/AnyBuzzin/van-design-system/pull/14) merged the original development stack, [PR #13](https://github.com/AnyBuzzin/van-design-system/pull/13), unified package and Fusion checkpoint together. `main` is intentionally unchanged. Python 3.10/3.12 CI passed on the merge commit. **This is an experimental engineering baseline, NOT a G5/manufacturing release.**

## Canonical source and verified engineering gates

- The **sole maintained Python runtime** is `src/vandesign` (wheel version 0.5.0), containing the canonical CAD-neutral core, modules, report validation and Fusion adapter. The `DadoShelf` compatibility API remains functional. The `prototypes/claude-v5` V5 code and V4 archives are preserved as historical test/source records, not development runtime imports.
- Real-Fusion evidence and CI must be read with fixture scope; arithmetic, mocked `adsk`, saved file existence, screenshot or cloud-save completion alone do **not** prove manufacturing fitness.

| Gate | Current acceptance | Evidence / remaining work |
| --- | --- | --- |
| **G0 — exact verified V4 revision** | **OPEN** | Real V4 shelf behavior reported by user, but exact executed `.py` and `.manifest` association unproven. [Issue #1](https://github.com/AnyBuzzin/van-design-system/issues/1). Preserve archive; time-box any further provenance search. |
| **G1 — CAD-neutral foundation/integration** | **Integrated; supported package verified** | `src/vandesign` is one installable runtime. Existing legacy and V5 APIs import from the installed wheel; 196 offline tests; Python 3.10/3.12 CI. Do not equate this with every future module being qualified. |
| **G2 — Fusion adapter and basic dado fixture** | **PASS for A–E tested fixture** | Five real Fusion A–E scenario reports, each **58/58 PASS**, plus explicit one-target-per-cut audit. [Protocol](prototypes/claude-v5/FUSION_TEST_PROTOCOL.md); [issue #2 CLOSED](https://github.com/AnyBuzzin/van-design-system/issues/2). |
| **G3 — base/tall/overhead variants** | **Implemented; partially real-Fusion qualified; OPEN** | Base/tall/overhead share one core. Base 59/59 and tall build/edit/restore and 6/6 cut audit reported. Overhead has successful partial checks. Legacy F0 and overhead F3 depth/height, negative cases, persistence and independent cut audit remain deferred. [Issue #4](https://github.com/AnyBuzzin/van-design-system/issues/4). |
| **G4 — controlled change engine** | **Width update PASS; G4 gate OPEN** | Existing `base@1` 1200→1100 mm in-place update, preview, journal/rollback/drift refusal, stable IDs, 59/59 and 2/2 cut audit, save/reopen evidence. Structural shelf/door-count changes, divergent user edits and general reconciliation still not qualified. [Width report](automation/G4_WIDTH_UPDATE.md). |
| **G5 — V5 engineering release candidate** | **NOT STARTED as release gate** | Define explicit supported configurations, traceable validation/report acceptance, verified cut-list preview, installation/release criteria and engineering sign-off. Not a CAM/manufacturing certification. |

## Product demonstrations — independent of G0–G5 closure

| Demonstrated capability | Actual real-Fusion evidence | Limits |
| --- | --- | --- |
| First simplified interior | Rear platform bed, reused kitchen cabinet and envelope, **95/95** actual BRep checks, basic edit/restore | Nominal rectangular envelope, limited topology; no manufacturing fit |
| Autonomous Fusion workflow (runner 0.2) | New demo create/build/check/save/capture, fresh save **19/19** PASS, cloud identity confirmed | It is a fixed allowlisted demo, not arbitrary Fusion manipulation; [report](automation/evidence/demo-workflow/STATUS.md) |
| Configurable layout (runner 0.3) | Bed dimensions/kitchen XY, collision refusal before CAD, **171/171** live checks over 9 stages; prior demo persistence PASS | No general layout optimizer; new layout's separate reopen was not demonstrated; [report](automation/evidence/configurable-layouts/STATUS.md) |
| Simplified vehicle usable space (runner 0.4) | 2100×4600×2200 mm envelope, two rectangular arches, 782 mm aisle versus 600 mm minimum, invalid 482 mm aisle refused, **198/198** BRep checks and **22/22** presave PASS | No measured van model, headroom/access-route certification, real fixing system or reopen of new vehicle demo; [report](automation/evidence/vehicle-usable-space/STATUS.md) |
| Single-package live cabinet qualification | New reviewed deployment used in actual Fusion: **59/59 PASS** at 1200→1210→1200 mm, correct two-cut participants, all 8 solids restored exactly; 24 loaded modules matched hashes | Qualifies this `base@1` fixture only, not every variant/interior or installed runner; [raw review](docs/integration/pr14-checkpoint-evidence/live-20261015/FINAL_REVIEW.md) |

## Integration and operating state

- [PR #14](https://github.com/AnyBuzzin/van-design-system/pull/14) is merged into `develop`; [PR #13](https://github.com/AnyBuzzin/van-design-system/pull/13) and earlier feature heads are included in its commit ancestry, not separate merge targets. Historical branches/reports should be retained. `main` has not been merged or deployed.
- The last inspected **live Fusion runner installation** was pinned to **historical G3 and demo package paths**, and the heartbeat was stale/stopped. Do **not** claim it is already running the integrated wheel. Offline loader checks and the independent PR14 cabinet script passed, but migration of the installed runner to reviewed generated bundles needs an explicit backup/rollback plan and approval before modification.
- Windows canonical spec-fixture CRLF error was traced to checkout line endings and narrowly fixed by `.gitattributes` in the merged vehicle-space milestone. [Issue #11](https://github.com/AnyBuzzin/van-design-system/issues/11) may be closed only after reviewing the landed fix and focused passing test evidence.
- **GitHub branch protections:** `main` and `develop` were found unprotected on 2026-10-15; add required checks and avoid direct pushes when the repository settings interface allows it.

## Ordered next milestones

1. **Baseline stabilization:** update central docs and AI prompts; reconcile obsolete PRs/issues, verify merged CI, add lightweight branch protection. No geometry changes.
2. **Safe runner transition:** prepare generated bundles from the installed `src/vandesign` wheel, backup live config and audit/rollback, then explicitly approve and perform a controlled switch/restart and a targeted disposable-design smoke. Do not silently replace the user's live installation.
3. **G3 remaining acceptance:** only the outstanding F0/overhead F3 coverage; no wholesale replay of completed fixtures. In parallel, conduct one **bounded** G0 provenance search and keep UNKNOWN if it cannot be authenticated.
4. **G4 smallest structural regeneration:** one scoped ownership-safe shelf count change with offline tests, a disposable real-Fusion geometry/cut check, rollback/manual-divergence handling and a single reviewable PR. Expand only after that operation is proven.
5. **G5 scope and release checkpoint:** specific supported features, traceable reports, deterministic cut-list **preview** and release acceptance; not production CAD/CNC approval.
6. **Then** V6 furniture, V7 measured vehicle geometry, V8 constrained AI layouts, V9 manufacturing, V10 production orchestration per [roadmap](docs/ROADMAP.md).

Every new milestone follows [AGENTS.md](AGENTS.md): one milestone/one PR, proportionate evidence, clear PASS/FAIL/UNKNOWN and regular reviewed integration. All unverified safety/structural/manufacturing claims remain explicitly unsupported.
