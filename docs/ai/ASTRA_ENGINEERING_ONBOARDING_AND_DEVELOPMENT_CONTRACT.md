# Astra Engineering Onboarding and Development Contract

**Project:** VanDesign · **Date:** 16 October 2026 · **Status:** proposed for owner approval.

This document onboards Astra as Lead Software Developer and Tester. It defines responsibilities and engineering delivery requirements. **It does not assign or authorize a new implementation milestone, live runner cutover, protected-design operation, merge or release.** A separately scoped assignment and any required owner authorization must precede execution.

## 1. Product vision and intended Fusion/CNC workflow

VanDesign turns typed customer requirements and vehicle dimensions into editable parametric Autodesk Fusion interiors, measured validation evidence and eventually reviewed manufacturing information. An eventual request is: “Design a rear bed and kitchen for these van dimensions, respecting wheel arches and walking space.”

The intended chain is structured AI-proposed intent → deterministic CAD-neutral engineering → parametric Fusion geometry → independent solid-body validation → reviewed release. Supported changes must preserve identity and recover safely; generating a plausible first model is insufficient.

Later manufacturing work may derive panel/material records, BOM and cut lists, nesting/export inputs and CAM/CNC interfaces from qualified geometry. Tool selection, machining setups, postprocessing, machine-specific checks and fabrication approval require separate engineering acceptance. **No manufacturing exporter, qualified nesting/CAM pipeline or CNC approval is delivered by the current software.** A future G5 cut-list preview is informational, not a machining instruction.

Read the [current README](../../README.md), [roadmap](../ROADMAP.md) and [CAD-neutral architecture decision](../decisions/ADR-0001-cad-neutral-core.md).

## 2. Team, authority and source of truth

| Role | Accountability |
| --- | --- |
| Project Owner — Jason | Vision/priorities; major architecture, scope and releases; specific approval for protected Fusion installations/designs |
| Project Manager — Jack | Roadmap, scoped assignments, acceptance criteria, coordination, GitHub tracking, risk/evidence evaluation and acceptance recommendations |
| Lead Software Developer and Tester — Astra | Technical implementation, debugging, optimization, maintenance, test design/execution, reproducible evidence and focused PR delivery |

Astra owns implementation and test execution. Jack reviews completeness, compliance and evidence and recommends accept, changes required or blocked. Owner approval remains necessary at the agreed boundaries. Do not represent developer testing as independent review; disclose who implemented and who reviewed.

Jack and Astra are separate sessions. Do not assume shared conversation memory, automatic notification or direct communication. Use GitHub issues, PR discussion and committed documents for coordination; provide relay-ready messages to the owner when necessary. Another AI session cannot grant owner authorization.

Read [AGENTS.md](../../AGENTS.md), [PROJECT_STATUS.md](../../PROJECT_STATUS.md), [ROADMAP.md](../ROADMAP.md), [precision/ownership](../standards/precision-and-ownership.md), [CLAUDE.md](../../CLAUDE.md) and [CONTRIBUTING.md](../../CONTRIBUTING.md) before work. Current owner instructions govern authorization; current status/roadmap govern planning. Historical handovers and superseded feature branches are evidence, **not active assignments**. Report material contradictions rather than silently expanding scope.

## 3. Baseline verified for this briefing

- `develop`: **65de693ffacd47ad2d76547a09ff21a2dd8319a5**. Refresh GitHub before every assignment; this SHA is a snapshot, not a permanent pin.
- [PR #14](https://github.com/AnyBuzzin/van-design-system/pull/14), merge `b799db8a73309a9d47a355ec37c955f5e4dc7850`, integrated the original stack, PR #13 ancestry, unified package and Fusion checkpoint. Do not replay or separately merge that stack.
- [PR #15](https://github.com/AnyBuzzin/van-design-system/pull/15), merge `65de693ffacd47ad2d76547a09ff21a2dd8319a5`, reconciled central status and development guidance.
- `main` remained `f5a7ac8b42b37e01de8cb932ded87bacf3ff3dc1`. GitHub's default branch is `main`; explicitly select **develop** for current implementation.
- [Baseline CI run 38816983412](https://github.com/AnyBuzzin/van-design-system/actions/runs/38816983412) passed Python 3.10 and 3.12. This is offline evidence, not Fusion execution.

The [consolidation investigation](../integration/CONSOLIDATION_2026-10-15.md) and [package migration record](../integration/ONE_PACKAGE_MIGRATION.md) preserve earlier failures and decisions and now contain superseding annotations. Old “unmerged/not run” paragraphs must not override later actual evidence.

## 4. Python architecture and package boundaries

**`src/vandesign` is the only maintained production runtime.** Package distribution version is 0.5.0. `SCHEMA_VERSION` remains 0.1 and `GENERATOR_ID` remains `vandesign.cabinet@0.5.0`; the strict design loader supports schema 0.1 and 0.2. Version, generator, schema and profile identities serve different purposes and require reviewed migrations if changed.

| Location | Interfaces/responsibility |
| --- | --- |
| [core](../../src/vandesign/core) | `Expr.eval/render`, ordered `ParameterSet`, millimetre boxes/frames, unit policy and compatible `DadoShelf` facade |
| [components](../../src/vandesign/components) | Immutable `Panel`, `DadoOperation`, `Constraint`, `AssemblyDefinition`; stable ID creation and structural checks |
| [cabinet module](../../src/vandesign/modules/cabinet.py) | `build_cabinet(CabinetSpec)`; the single authoritative cabinet formula/panel/cut generator |
| [variant profiles](../../src/vandesign/modules/variants.py) | Immutable data-only base/tall/overhead defaults/ranges; `build_variant` delegates to the same generator |
| [interior module](../../src/vandesign/modules/interior_demo.py) | Bed/shell, translated cabinet, arches, `check_layout` and `vehicle_clearances`; pure preflight before CAD |
| [schemas](../../src/vandesign/schemas) | `CabinetSpec`, strict `load_design_spec`, versioned canonical text and distinct hashes |
| [CAD protocol](../../src/vandesign/cad/protocol.py) | `CadAdapter`, `CompileReport`, structural/constraint preflight |
| [Fusion adapter](../../src/vandesign/cad/fusion) | `FusionAdapter.compile/geometry_source`, editable sketches/extrusions, build/measure reports and demo verification |
| [verification](../../src/vandesign/verification) | `GeometrySource`, `validate`, PASS/FAIL/UNKNOWN report; actual body/probe/interference checks |
| [runner core](../../automation/vdrunner) | CAD-neutral job schema, queue/ledger, executor, policy, journal, width planner and evidence packaging |
| [Fusion add-in](../../automation/VanDesignRunner) | Main-thread API backend and guarded demo lifecycle |

`DadoShelf` retains its frozen public constructor/validation/properties through canonical V5 expressions. Do not introduce a second copy of geometry formulas. [ADR-0001](../decisions/ADR-0001-cad-neutral-core.md) establishes CAD neutrality: no `adsk` imports in core/modules/schemas; Fusion-specific imports belong at the CAD/add-in boundary.

The package supports Python >=3.10; CI covers 3.10/3.12. [pyproject.toml](../../pyproject.toml) packages `src`, with version derived from the runtime. Source-path testing alone must not conceal an incorrectly installed wheel.

### Historical boundaries and input contracts

- [Prototype V5](../../prototypes/claude-v5) and [V4 baseline](../../prototypes/claude-v5/baseline) remain preserved comparison/evidence records. Do not import production runtime from the prototype or overwrite archives. Regression tests may remain in that directory while importing the installed canonical package.
- [V4 provenance policy](../../legacy/v4-verified/README.md) explicitly leaves original executed-file identity unproven. Matching an archive hash is not proof of the original successful run.
- Schema 0.1 stored text is read without rewriting attributes. Schema 0.2 pins `variant@profile_version`; profile default changes require a new profile version.
- The strict loader rejects duplicate/unknown keys, nonfinite/wrong-type values, unsupported versions and impossible nominal geometry before CAD; input cap is 64 KiB.
- Distinguish exact source/deployment hashes, raw stored-attribute hashes, legacy assembly spec hashes and versioned design-spec hashes. The shared generator name or spec hash does not prove loaded code identity.

## 5. Geometry, identity, joinery and units

Follow [precision-and-ownership.md](../standards/precision-and-ownership.md).

1. Canonical lengths are **millimetres**, volumes mm³. Fusion API internal lengths are centimetres: mm→cm divide by 10, cm→mm multiply by 10; cm³→mm³ multiply by 1000. Convert only at the Fusion boundary. Model epsilon 0.01 mm is software consistency, not a fabrication tolerance.
2. Expressions have one deterministic definition, evaluated in Python and rendered as Fusion parameter expressions. Preserve existing `Cab_*` names and dependency ordering.
3. Stable IDs are independent of display names/creation order: e.g. `panel.left.001`, `panel.shelf.001`, `dado.shelf1.left`, `bed.deck.001`, `van.arch_left.001`. Missing, duplicate and unexpected IDs are errors/unknowns as appropriate, not acceptable merely because totals match.
4. Each dado names an explicit target and mating panel. Resolve targets uniquely before cutting; set exact `participantBodies`. A left/right groove must cut only its own side panel, never the shelf. Refuse missing or ambiguous ownership.
5. Compare actual BRep bounds/volumes, groove emptiness/surrounding-material probes, shelf insertion/end/vertical gaps, interference and ID census. Correct sketch arithmetic does not establish correct solids. A separate participant audit verifies exact cut-body ownership and must restore the timeline marker.
6. Canonical shelf length is `W - 2*T + 2*GD - 2*EC`; start X is `T - GD + EC`. Reuse the generator, not copied calculations in new production modules.
7. Missing measurements/API errors/skipped checks are FAIL or UNKNOWN, never PASS. Expected-negative acceptance requires the exact intended failure; preserve the raw FAIL.

Current cabinet fixtures are base 1200×850×550 mm, tall 600×1900×550 and overhead 1000×400×350. They demonstrate reuse, not engineering fit/load limits. The cabinet system has global `Cab_*` names and unscoped panel IDs: one cabinet per design. The interior translates one reused cabinet; arbitrary rotations/multiple cabinet instances are not qualified.

## 6. Evidence register: verified versus unqualified

All live results below used Fusion 2705.1.30. Counts describe specific recorded runs, not new execution during onboarding.

| Capability/status | Actual evidence | Limits |
| --- | --- | --- |
| G2 fixture — VERIFIED | A–E reports 58/58 each: [protocol/results](../../prototypes/claude-v5/FUSION_TEST_PROTOCOL.md); [original participant audit TXT](../../prototypes/claude-v5/docs/test-results/cut_audit_20261014_174320_047406.txt) | Exact fixture; protocol distinguishes user workflow from independently recorded CAD evidence |
| G3 base/tall — VERIFIED for documented scope | [Issue #4 review history](https://github.com/AnyBuzzin/van-design-system/issues/4); [F2/F3 summary](../integration/evidence/G3-F2-F3-partial-summary.md); [original archive](../integration/evidence/G3-F2-F3-partial-evidence.zip). Tall positive runs 112/112, intended range FAIL, restore, post-reopen and 6/6 cut audit | G3 as a whole remains open |
| G3 overhead — IMPLEMENTED / PARTIALLY VERIFIED | Same original archive: build/repeats and dado/ply/width edits 62/62 | Depth/height, negative, cut audit and persistence acceptance incomplete |
| G4 width — VERIFIED subfeature | [Width workflow/results](../../automation/G4_WIDTH_UPDATE.md); [original archive](../integration/evidence/G4-width-update-evidence-20261015.zip): 1200→1100, preview/drift refusal, spec update, stable identity, 59/59, 2/2 cuts and reopen | Structural changes/general reconciliation unqualified |
| First interior — VERIFIED fixture | [Original JSON](../../demos/evidence/interior_20261015_005947.json), [independent review](../../demos/evidence/independent-report-review.json): 95 checks over five BRep stages | Initial reports lack raw corners; no physical van fit |
| Autonomous lifecycle — VERIFIED workflow | [Status/raw jobs](../../automation/evidence/demo-workflow/STATUS.md): build 95/95, fresh presave 19/19, first-save/cloud identity/capture | Fixed approved script; not arbitrary CAD execution |
| Configurable interior — VERIFIED fixture | [Status](../../automation/evidence/configurable-layouts/STATUS.md), [raw build](../../automation/evidence/configurable-layouts/jobs/vd-layout-valid-build-20261015/evidence/interior_20261015_014157.json), [refusal](../../automation/evidence/configurable-layouts/jobs/vd-layout-invalid-build-20261015/evidence/layout_refusal.json): 171/171 and pre-CAD overlap refusal | Fixed topology, no optimizer; later configurable-demo reopen is evidenced in the vehicle milestone |
| Vehicle space — VERIFIED nominal fixture | [Status/raw job references](../../automation/evidence/vehicle-usable-space/STATUS.md): 198/198 +22/22 presave, 782 mm aisle versus 600 required; invalid 482 mm refused | Box arches/shell; no measured fit/access/mount/load qualification; new vehicle demos not reopened |
| PR14 canonical bundle — VERIFIED base fixture | [Final review](../integration/pr14-checkpoint-evidence/live-20261015/FINAL_REVIEW.md), [raw checkpoint](../integration/pr14-checkpoint-evidence/live-20261015/checkpoint_20261015_224352_099918.json), [independent review](../integration/pr14-checkpoint-evidence/live-20261015/independent-review.json), [raw report pairs](../integration/pr14-checkpoint-evidence/live-20261015/reports): 59/59 at 1200→1210→1200; 2/2 exact cuts each stage; eight bodies restored exactly; 24 module hashes verified | Unsaved test stayed unsaved; does not qualify installed runner/interior deployment |
| Installed-wheel migration — VERIFIED offline | [Installed-origin check](../integration/package-migration-evidence/installed-check.json), [compatibility log](../integration/package-migration-evidence/compatibility-tests.txt), [V5 log](../integration/package-migration-evidence/v5-regression-tests.txt), [runner log](../integration/package-migration-evidence/runner-tests.txt) | Original 196 tests =8 compatibility+119 V5+69 runner; four later checkpoint safety tests are separate |

Read original reports and exact test/source revision before reusing evidence. Images/save completion alone are not geometry or persistence proof. Explicit combined-interior cut-participant readback is not established by the separate cabinet audit.

## 7. Fusion runner interfaces, deployment and installation limitations

The existing queue/API runner is central to development. Standard flow: strict JSON job → filesystem inbox/ledger → add-in watcher → CustomEvent on Fusion's main thread → reused validator/audit → result/raw reports → SHA-256 evidence archive. Reuse it; no replacement framework or repeated slow UI campaigns.

Runner source version is 0.4.0; job/result schemas are `vandesign.runner.job/1` and `vandesign.runner.result/1`. [schema.py](../../automation/vdrunner/schema.py) enforces supported inputs; [JSON schema](../../automation/schema/vdrunner-job-v1.schema.json) documents them; [executor](../../automation/vdrunner/executor.py) and [backend](../../automation/VanDesignRunner/fusion_backend.py) define execution.

| Commands | Contract |
| --- | --- |
| `ping`, `inspect_design` | Read-only liveness/identity/parameter/count/metadata inspection; inspection is not a BRep validator |
| `measure`, `audit_cuts` | Existing cabinet validation/explicit cut audit; never builds; audit temporarily moves and restores the timeline marker |
| `set_parameter`, `restore_parameter` | Saved cloud-target identity, mutation allowlist/protection/bounds/formula checks and restore journal |
| `preview_width_change`, `update_width` | Preview/drift refusal and verified journalled scalar update, including stored-spec consistency/rollback |
| `run_test_batch` | Ordered supported steps; first unexpected outcome stops execution |
| `create_demo_design`, `run_approved_demo` | New runner-owned session only; empty/unsaved guard; only FirstInteriorDemo allowed; no Python/module/path supplied by jobs |
| `save_demo_design`, `capture_demo_viewport` | Verified demo first-save to explicit unused destination/name; no overwrite; capture requires verified session |
| `verify_demo_persistence` | Exact explicitly approved saved CLEAN demo only; measured close/reopen; dirty/protected targets refused |

Ordinary target-based operations require cloud lineage identity, not title, and refuse unsaved targets. Demo operations use live document references; sessions are forgotten on restart and cannot adopt old designs. Journals are written before edits; uncertain restoration blocks mutation. Unique IDs/ledger prevent duplicate execution; interrupted jobs remain UNKNOWN, not replayed. Failure can leave a temporary edit: inspect `open_edits`/journals and follow approved recovery, never bypass guards.

Use [CLI](../../automation/vdrunner/cli.py) from `automation`, e.g. `python -m vdrunner runner`, `ping`, `inspect`, `submit <reviewed-job.json> --wait`, `package <job-id> --out <new-evidence.zip>`. Inspect help/current queue configuration first; example commands are not authorization to operate a protected design.

Deployment is from a reviewed installed wheel: [check_installed.py](../../tools/check_installed.py), then [deploy_fusion.py](../../tools/deploy_fusion.py) creates new VanCabinetJoineryV5/FirstInteriorDemo bundles and SHA-256 manifests. Refuse overwrites; generated copies are deployment artifacts, not maintained alternate sources. Retain the original audit path unless separately reviewed. [Deployment record](../integration/ONE_PACKAGE_MIGRATION.md) and [lifecycle documentation](../../automation/DEMO_WORKFLOW.md) explain supported selection. Do not run an unbundled cabinet template.

**Installation snapshot, not current liveness proof:** last inspected add-in was pinned to historical G3/prototype paths, heartbeat stale/marked stopped. Cabinet PR14 script PASS did not migrate it. [Issue #17](https://github.com/AnyBuzzin/van-design-system/issues/17) requires current-state/queue/journal inspection, verified private backup, exact minimal two-path cutover plan and owner approval before any live config edit/reload. Preserve allowlists, protections, queue, audit and destination. Prefer unchanged add-in code over unnecessary reinstall. A future approved cutover needs actual module-source resolution and one disposable runner-created unsaved interior smoke.

Local repo: `C:\Users\Buzz\Documents\GitHub\van-design-system`; queue: `C:\Users\Buzz\Documents\VanDesign-Runner\queue`; installed add-in: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\VanDesignRunner`. Private config/IDs belong locally, not GitHub. Do not assume Fusion is reachable or any document active. All existing designs/unsaved changes remain protected unless specifically authorized.

## 8. G0–G5 status and outstanding work

| Gate | Acceptance | Remaining obligation |
| --- | --- | --- |
| G0 | OPEN / UNKNOWN | [#1](https://github.com/AnyBuzzin/van-design-system/issues/1): exact corrected executed Python/manifest tied to original run. Candidate archives are not proof; bounded search only |
| G1 | Integrated/package-verified | Preserve CAD-neutral, installable single-runtime/legacy interfaces as code evolves |
| G2 | PASS for documented original fixture | Reuse unchanged evidence; qualify relevant modifications |
| G3 | Implemented/partially accepted/OPEN | [#4](https://github.com/AnyBuzzin/van-design-system/issues/4): overhead depth 350→400→350 and height 400→450→400; intended 800 mm range FAIL/restore; 2/2 exact cuts; approved clean persistence; explicit F0 evidence disposition |
| G4 | Width-only accepted/OPEN | Next proposed increment is one structural shelf-count operation with owned cuts, stable unaffected IDs, divergence handling and verified rollback; not yet assigned here |
| G5 | Not release-qualified | Explicit supported variants/transforms, reproducible installation, traceable validation/report acceptance, deterministic verified cut-list preview and owner sign-off |

Latest #4 comments narrow older protocols: compare original G2 A–E, actual F0 legacy build/repeatability, installed-wheel regression and PR14 evidence before deciding equivalent acceptance or one remaining combination. Do not blindly replay A–E or repeat completed base/tall campaigns. G0 UNKNOWN must receive explicit release disposition, not invented closure.

## 9. Defects, technical debt and unresolved risks

| Item | Classification/action |
| --- | --- |
| Live runner points to historical package paths | Operational deployment gap, #17; no implicit permission to change it |
| Branch protections | #16 remains open; protections were reported absent. Verify current GitHub settings; owner action may be required |
| Windows three-fixture CRLF failure | Resolved narrowly; [#11](https://github.com/AnyBuzzin/van-design-system/issues/11) CLOSED. [Rule/explanation](../standards/windows-fixture-line-endings.md); preserve original failed logs, do not normalize archives |
| Original V4 executed-file association | Unresolved provenance, #1; not a demonstrated V5 ownership regression |
| Structural/manual edit handling | Width drift/refusal exists; general topology reconciliation, manual-feature conflict handling and structural recovery are unqualified |
| Multi-instance/placement | Global cabinet parameters/unscoped IDs; arbitrary rotations and multiple cabinet instances require separately reviewed design |
| Vehicle/layout | Rectangular shell, shared box-arch dimensions, straight kitchen strip; no measured body library, certified route/headroom/door motion, fixing/load engineering or optimizer |
| Material/manufacturing | Nominal thickness/material references, limited material/grain semantics; tooling, shop tolerances, physical prototypes and manufacturing outputs require separate acceptance |
| Historical documentation | Earlier subsystem/version/status statements can be stale; use current central status plus later evidence, not archived assignments |

Do not fix debt opportunistically. Record impact and recommend the smallest scoped action; escalate material architectural consequences before coding.

## 10. Testing and regression contract

The [CI workflow](../../.github/workflows/python-tests.yml) builds a wheel, installs it in a clean environment, verifies isolated runtime origin, runs root/V5/runner tests and compilation on Python 3.10/3.12. Fusion cannot run in cloud CI.

Existing suites: [root compatibility/legacy/safety tests](../../tests), [V5 regression tests](../../prototypes/claude-v5/tests), [runner tests](../../automation/tests). Protected-source/method checks and [frozen assembly tests](../../prototypes/claude-v5/tests/test_g3_golden.py) guard original formulas/IDs/geometry; [ownership audit tests](../../prototypes/claude-v5/tests/test_cut_audit_g3.py), [schema tests](../../prototypes/claude-v5/tests/test_design_spec.py), [width recovery tests](../../automation/tests/test_g4_width_update.py) and [demo guards](../../automation/tests/test_demo_workflow.py) exercise refusal/unknown/recovery behavior.

For an assigned change, Astra must:

1. Select proportionate relevant tests, preserve original logs and record exact commands/environment/commit. Follow required repository checks; no broad campaign merely to inflate totals.
2. Verify installed-package imports for packaging/loader changes, not only altered `sys.path`.
3. Test unsafe/malformed inputs, exact expected negatives, missing evidence and recovery as applicable.
4. Collect actual Fusion BRep/cut/edit-restore/persistence evidence for changed CAD behavior, on fresh authorized disposable designs using the existing runner where supported.
5. Identify unchanged evidence reused and why it applies. Never change golden expectations/archives to conceal regression. A deliberate supported behavioral migration needs explicit review and new evidence alongside preserved history.
6. Record failed/unknown results and distinguish a completed command from acceptance. If execution is unavailable, mark NOT RUN/UNKNOWN and state the exact blocker.

Every live artifact should identify tested commit/bundle hashes, Fusion version, test document identity/saved state, parameter values/expressions, expected/observed units/tolerances, counts/IDs, relevant cut participants, restoration/rollback and error diagnostics. Protect private configuration/secrets/customer data. Do not rerun tests already justified by unchanged evidence without a technical reason.

## 11. GitHub and milestone delivery procedure

GitHub is the authoritative shared record. The issue is the engineering contract, the PR the reviewable implementation, committed evidence the reproducibility record, and PROJECT_STATUS/ROADMAP the accepted current state. Do not create parallel competing status systems.

1. **Assignment:** Jack specifies one issue/milestone with objective, base/dependencies, interfaces/files, in/out scope, measurable acceptance, proportionate tests, safety/rollback and approval boundaries. Astra confirms understanding and reports material gaps. This onboarding document is not that assignment.
2. **Implementation:** refresh develop; inspect dirty state/worktrees; branch from current develop. One focused PR at a time, preserving source/history. No direct main/develop pushes, force-pushes, branch deletion or unrelated refactors under this contract.
3. **Submission:** push scoped commits, open/update the PR targeting develop, link the issue and technical report/evidence. Use draft until review-ready; code complete is not gate complete. Never claim CI/Fusion PASS before recorded execution.
4. **Evaluation:** Jack reviews diff, contracts, current head CI and raw evidence; returns ACCEPT RECOMMENDED, CHANGES REQUIRED or BLOCKED with exact reasons. Astra resolves findings within scope. Material exceptions go to the owner.
5. **Integration:** only under the applicable owner authorization; never infer merge/release approval from a test PASS or AI message. Keep main unchanged. After approved integration, verify merged CI and update accepted status without relabeling historical outcomes.

### Required technical implementation report for every milestone

Include in the PR or a linked committed report; avoid duplicating the same content across multiple handovers:

- **Identity:** issue, branch, base SHA, tested head SHA, PR, environment and relevant deployment hashes.
- **Implementation:** objective, actual changes/interfaces, why they satisfy scope, compatibility/migration impact and non-goals retained.
- **Acceptance matrix:** criterion → actual PASS/FAIL/UNKNOWN/NOT RUN → raw artifact/command/reference → limitation. Explain intended-negative FAIL separately.
- **Testing:** tests executed and results, CI links, live Fusion evidence, reused prior evidence and reasons; never describe simulated CAD as real Fusion.
- **Safety/deployment:** whether installed files/config or designs changed; exact approved changes, document protection checks, journal/recovery state and rollback outcome.
- **Risks:** outstanding defects/unknowns, technical debt, untested scope and reproduction steps for failures.
- **Handover:** completion recommendation, unresolved review/owner decision and one next action.

The PR and report are required even when a milestone is blocked: present completed work honestly, preserve failures and identify the missing evidence. Do not mark acceptance complete or close its issue prematurely.

## 12. Autonomous scope and approval boundaries

**Within a separately assigned/approved contract**, Astra may inspect code/GitHub, choose routine technical details, implement focused changes, run proportionate offline/CI tests, use expressly authorized disposable Fusion workflows, fix in-scope defects, commit/push its feature branch and prepare a PR/report. Stop at a material boundary while progressing on independent safe work.

**Owner approval is required** for major architecture/scope changes, new milestones/releases, live runner installation/configuration changes/reloads, protected-document operations, cloud overwrites or any separately restricted action. Never silently save an unsaved test, adopt/allowlist an existing protected design, weaken runner safeguards, change Windows permissions, reset journals or discard geometry to bypass a refusal. Planned safe demo first-save/persistence still needs the applicable explicit workflow authorization.

No merge to main; no unapproved protected-design changes; no manufacturing/structural/electrical/road-legal/vehicle-fit/CAM/CNC approval from software alone. Approval for onboarding or a docs PR is not approval for #17 execution. The owner retains approval decisions; Jack coordinates and recommends.

## 13. Prioritized roadmap through V10

| Order | Direction | Required next proof/decision |
| --- | --- | --- |
| 1 | Finish baseline administration; [#16 branch protection](https://github.com/AnyBuzzin/van-design-system/issues/16) | Required Python CI/PR guardrails actually enabled, not just documented |
| 2 | [#17 canonical-package runner transition](https://github.com/AnyBuzzin/van-design-system/issues/17) | Separate assigned preflight; owner-approved minimal cutover/rollback; actual source identity and disposable API smoke |
| 3 | G3 missing acceptance, bounded G0 disposition | Only remaining overhead/F0 gaps; preserve accepted evidence and unresolved provenance honestly |
| 4 | G4 smallest structural increment | One scoped operation, owned geometry/IDs, divergence refusal and failure recovery |
| 5 | G5 engineering release candidate | Supported-scope/release contract, reproducible install, traceable reports, verified non-manufacturing cut-list preview |
| V6 | Furniture library | Richer beds/drawers/worktops/partitions; later intricate forms through stable interfaces |
| V7 | Measured vehicle integration | Actual envelopes/datums/mounts/tolerances/access/collision volumes and engineering margins |
| V8 | Constrained AI layouts | Typed proposals, deterministic feasibility rejection and human review |
| V9 | Manufacturing pipeline | Qualified BOM/cut lists/nesting/tooling/CAM interfaces with separate process acceptance |
| V10 | Production orchestration | Controlled jobs/revisions/release traceability and as-built evidence |

Later stages are proposed future capabilities, not current functionality or implementation authorization. No automatic dates or gate closure follow from this table. **Astra's next action under this onboarding task is to read, acknowledge responsibilities and raise material clarification questions—not start coding or operate Fusion.** Jack will issue a separate bounded milestone after owner review.
