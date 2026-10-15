# VanDesign — Complete Engineering Handover to Claude

**Project:** VanDesign V5 · **Current delivery gate:** G3 — three cabinet variants from one verified CAD-neutral core  
**Handover date:** 14 October 2026 · **Owner:** VanDesign project owner · **Status:** IMPLEMENTATION AUTHORISED WITH GUARDRAILS  
**Repository:** https://github.com/AnyBuzzin/van-design-system · **Development branch:** `feature/v5-g3-cabinet-variants`  
**G3 task:** https://github.com/AnyBuzzin/van-design-system/issues/4 · **G2 draft PR:** https://github.com/AnyBuzzin/van-design-system/pull/3

> **Direct instruction to Claude:** The revised G3 proposal v2 has been reviewed and approved with the conditions in this document. **Do not restart architecture discussions or request another approval after each commit. Start implementation now**: establish C0 golden tests, then proceed through C1–C5, keeping tests green and recording results. Return one complete reviewed implementation with exact diffs, CI results, and the user-facing real-Fusion test package. If you encounter an architectural incompatibility or risk to verified geometry, stop that specific change, document it, and continue independent safe work. **Never merge PR #3 or claim G3 is Fusion-verified without user-run evidence.**

---

## 1. Executive state — what is proven, proposed, and outstanding

VanDesign is a professional, deterministic cabinet/van-interior engineering system. AI assists with typed design intent; a CAD-independent Python engine determines components, dimensions, formulas, and cut ownership; Autodesk Fusion 360 is an adapter; verification measures actual BRep solids; manufacturing release requires a separate human-approved gate. **AI does not author arbitrary geometry directly.** All lengths are **millimetres** in the engineering core; Fusion API stores lengths in **centimetres**, converted only at the adapter boundary.

As of this handover:

| Area | State | Evidence / limitation |
|---|---|---|
| V4 physical joinery | User-tested in Fusion | Exact final on-disk V4 `.py` / `.manifest` identity still unresolved — [Issue #1](https://github.com/AnyBuzzin/van-design-system/issues/1) |
| G1 CAD-neutral core | Operational isolated V5 prototype | Existing foundation `src/vandesign` is **not yet reconciled** with bundled prototype package |
| **G2 Fusion smoke fixture** | **PASS** | A–E test reports, 58 of 58 checks on each run; real separate cut audit PASS; [Issue #2](https://github.com/AnyBuzzin/van-design-system/issues/2) closed |
| Existing V5 integration PR #3 | **OPEN / DRAFT / UNMERGED** | Targets `develop`; tests pass, but integration/provenance review remains |
| **G3 base/tall/overhead profiles** | **PROPOSAL APPROVED; CODE NOT IMPLEMENTED** | Offline feasibility on unchanged generator only; [Issue #4](https://github.com/AnyBuzzin/van-design-system/issues/4) stays open |
| G4 controlled change engine | **NOT STARTED** | Structural changes, change reconciliation, safe re-generation, multi-instance identity deferred |
| Vehicle fitment, mounting, CNC/CAM | **NOT APPROVED / NOT IMPLEMENTED** | No structural or manufacturing certification |

**Do not conflate code review, unit tests, simulated CAD checks, actual Fusion checks, vehicle suitability or manufacturing approval.**

### Why this handover replaces earlier fragmented messages

The older starter roadmap mislabeled G3 as change management. The **authoritative V5 architecture** (`VanDesign_V5_System_Architecture.md`, section 12) defines **G3 as three cabinet variants**, **G4 as a change engine**, and **G5 as release candidate**. `docs/ROADMAP.md` has been reconciled. Claude proposal **v2** supersedes v1. The prior handover contained an unnecessary pause after C0; the owner's latest instruction is **keep the project moving**, so completing C0–C5 autonomously under the approved contract is authorised.

---

## 2. Canonical repository, source baseline and onboarding

**Do this first, before editing any code:**

1. Clone or open the now-public GitHub repository; switch to `feature/v5-g3-cabinet-variants`. If direct access fails, use a complete ZIP of **that exact branch** — **never** use the older original Claude V5 package as the coding base.
2. Record `git rev-parse HEAD`, run `git status --short`, check the branch history and compare the checked-out files to the following **reviewed source snapshot**: `c7dd2c7b656a392feea1999919a2100e6b0a1753`. This SHA is the last observed source/documentation state **before this new handover is committed**. Later docs-only commits do not change the verified construction code. If source code has changed since, diff it and flag the differences before proceeding.
3. Read repository root `AGENTS.md`, `CLAUDE.md`, `README.md`, `PROJECT_STATUS.md`, `docs/ROADMAP.md`, `docs/standards/precision-and-ownership.md`, `prototypes/claude-v5/README.md`, `prototypes/claude-v5/FUSION_TEST_PROTOCOL.md`, and Issue #4 including review comments.
4. Inspect `prototypes/claude-v5/VanCabinetJoineryV5/vandesign/` and `prototypes/claude-v5/tests/`; **also inspect** root `src/vandesign` and `.github/workflows/python-tests.yml`. Those are available on the GitHub branch; they do not need separate files.
5. Run the current **foundation** and **prototype** unit suites and record raw logs. Existing branch has **31** prototype tests (the extra `test_runner_reporting.py` tests the current Fusion runner through a mock). Do not overwrite `runner.py` with Claude's older 30-test version.
6. Locate or import the separately provided **original `VanDesignCutAudit` script** from the attached handover package. Its source is not yet part of the repository. Preserve its read-only audit behaviour when extending it for six tall-cabinet cuts.

**Relevant repository paths** (relative):

| Purpose | Path |
|---|---|
| Pure canonical assembly generator | `prototypes/claude-v5/VanCabinetJoineryV5/vandesign/modules/cabinet.py` |
| Unchanged 0.1 cabinet data class / serializer | `.../vandesign/schemas/cabinet_spec.py` |
| Immutable panel, dado, constraint and assembly records | `.../vandesign/components/model.py` |
| Dimensions and expression engine | `.../vandesign/core/` |
| Fusion geometry creation and BRep readback | `.../vandesign/cad/fusion/adapter.py` |
| Fusion build/measure/report runner | `.../vandesign/cad/fusion/runner.py` |
| Geometric / parametric checks | `.../vandesign/verification/validate.py` |
| CAD-neutral readback interface | `.../vandesign/verification/geometry_source.py` |
| Python regression suite | `prototypes/claude-v5/tests/` |
| Verified G2 test steps and exact results | `prototypes/claude-v5/FUSION_TEST_PROTOCOL.md` |
| Exact real-Fusion cut-audit output | `prototypes/claude-v5/docs/test-results/cut_audit_20261014_174320_047406.txt` |
| Archived delivered V4 rev2 files | `prototypes/claude-v5/baseline/` — **never rewrite** |
| Separate foundation package, not yet integrated | `src/vandesign/` |
| CI | `.github/workflows/python-tests.yml` |

The V5 source lives in a self-contained prototype namespace and is **not** already the main foundation package. G3 code remains in the prototype; make a separate integration plan later, not a wholesale move into `src/vandesign`.

---

## 3. Real-world Fusion evidence — fixed regression baseline

**Fusion version:** 2705.1.30 · **Verified saved design:** `v5-smoke-test` · **Modes:** initial `build`, subsequent `measure`. The user followed a save/close/reopen sequence; the TXT reports independently show the preserved design, parameter values and `measure` result but cannot themselves prove the application-close event.

All these reports contained **58 PASS / 0 FAIL / 0 UNKNOWN** for the G2 fixture:

| Run | Parameter state (mm) | Reported shelf length | Insertion into each dado | Evidence |
|---|---|---:|---:|---|
| A | Width 1200, ply 18, dado 6, end clearance 0.3 | **1175.4** | **5.7** | User-supplied initial build TXT |
| B | Width 1200, ply 18, dado 10 | **1183.4** | **9.7** | `report_20261014_030324_809979_measure.txt` |
| C | Width 1000, ply 18, dado 10 | **983.4** | **9.7** | `report_20261014_030611_667348_measure.txt` |
| D | Width 1200, ply **15**, dado 10 | **1189.4** | **9.7** | `report_20261014_030749_282208_measure.txt` |
| E1 | User-directed save/reopen; width 1200, ply 15, dado 10 | **1189.4** | **9.7** | `report_20261014_030933_513529_measure.txt` |
| E2 | After reopen, width 1200, ply **15**, dado **8** | **1185.4** | **7.7** | `report_20261014_031006_041028_measure.txt` |

**CRITICAL E2 correction:** `1200 − (2 × 15) + (2 × 8) − (2 × 0.3) = 1185.4 mm`. An old Claude protocol erroneously said **1179.4 mm** (which assumed 18 mm ply). **The current committed G2 protocol ALREADY says 1185.4 mm**. Do not regress or rewrite it to the erroneous number.

Underlying G2 checks included `Cab_*` formulas, panel bounding boxes and volumes, groove emptiness/front openness/far/rear wall probes, shelf body remaining unmodified by groove cuts, insertion/end clearances and zero interference **among joined panels**. This is **not** an exhaustive collision test of all possible cabinets.

A separate **real-Fusion read-only cut audit** returned:

```
dado.shelf1.left:  Operation Cut=True; participant count=1;
  body '01 Left Side'; stable id panel.left.001; PASS

dado.shelf1.right: Operation Cut=True; participant count=1;
  body '02 Right Side'; stable id panel.right.001; PASS

Timeline moved back to end=True; OVERALL PASS
```

The shelf is excluded from both cut targets. Audit is in the repository; original standalone script is in the handover ZIP. **The script temporarily repositions the Fusion timeline marker and restores it in `finally`**; any extended audit must preserve this guarantee. Additional work must not change `participantBodies` or downgrade unknown API evidence to PASS.

**Latest GitHub CI at checked G3 branch source snapshot:** push run `38602249574`, `success`, including Python 3.10 and 3.12 jobs. This verifies Python behavior only, not real Fusion operation on G3 variants.

---

## 4. Binding G3 decisions — no further approval round necessary

| Ref | Decision | Implementation requirement |
|---|---|---|
| D1 | **No new geometry in G3 — approved** | Reuse `build_cabinet` and the existing BRep construction; three **data-only profiles**. No plinth, overhead fixing rail, hinges, rabbet, or other new features. |
| D2 | **0.2 schema — approved conditionally** | Read **both 0.1 and 0.2**; byte/hash-compatible legacy path; stored G2 designs remain readable without rewriting attributes. |
| A | **Strict new input loader — approved** | Reject duplicate JSON keys at every level, unknown top-level fields, malformed/oversize data. A deliberate tightening for *noncanonical manually authored* 0.1 JSON; keep original legacy serializer/class untouched. |
| B | **One new managed-ID census — approved** | Add `entities.managed_ids` comparing expected and observed **multiplicities**, missing, duplicate and unexpected IDs. Failure or unavailable enumeration = FAIL/UNKNOWN. Default base total may become 59; preserve original 58 named checks. |
| C | **No spec file → old 0.1 base — approved** | New empty design, no `cabinet_spec.json`: store identical fully resolved G2 default 0.1 JSON and hash. |
| D | **Pinned sparse-spec semantics — approved** | 0.1 sparse uses **frozen legacy defaults**, 0.2 sparse uses immutable `variant@profile_version` defaults. Store fully resolved schema-specific spec. |
| E | **Profile limits — approved as provisional fixture rules** | Base: **no** profile limits. Tall and overhead: data-only provisional ranges; out-of-range edits → named FAIL, never auto-clamp. Not safety/structural/vehicle-fit limits. |
| F | **Foundation integration — deferred** | No duplicated formulas in `src/vandesign`. Provide future integration map separately. |
| D3 | **One cabinet per Fusion design — approved** | Global `Cab_*` names and stable IDs such as `panel.left.001` remain unscoped; multi-instance support is later. |
| D4 | **No more proposal waiting** | Implementation stages C0–C5 may proceed without requesting incremental approval, provided regression gates hold and source/geometry changes stay within this contract. |

**Breaking architectural exceptions require review, not ordinary implementation details.** Never “fix” failing golden checks by changing the golden baseline to match a broken implementation.

### Important current API contracts

- `CabinetSpec` in G2 emits `{"schema_version":"0.1","module":"base_cabinet@1","parameters":...}` and rejects any other schema version through its existing `from_dict`.
- The module constant `SCHEMA_VERSION = "0.1"` feeds that serializer. **Do not simply bump it to 0.2** or silently reinterpret old designs.
- `build_cabinet(spec)` computes `AssemblyDefinition.spec_hash` using **legacy `CabinetSpec.spec_hash()`**, even for parameters that came from a new 0.2 wrapper. A new schema 0.2 **design specification hash** is a **separate concept** and must be explicitly named.
- Current actual branch `runner.py` writes **both** `parameters_read_from_fusion` (values and expressions) **and** `parameters_mm` in JSON; also writes TXT and logs failures. Preserve all these behaviors and old keys additively.
- `run_cabinet` currently builds into an empty Fusion design only; if tagged components exist, it loads stored spec and **measures without rebuilding**. This is not a structural regeneration engine.

---

## 5. Three fixture profiles — proposed test sizes, not engineering sign-off

| Property | `base@1` | `tall@1` | `overhead@1` |
|---|---|---|---|
| Width × height × depth (mm) | **1200 × 850 × 550** | **600 × 1900 × 550** | **1000 × 400 × 350** |
| Shelves / doors | **1 / 2** | **3 / 1** | **1 / 2** |
| Shelf / door count allowed | 0–4 / 1–2 | 1–4 / 1–2 | 0–2 / 1–2 |
| Width range (mm) | None | 300–900 | 300–1500 |
| Height range (mm) | None | 1400–2200 | 250–700 |
| Depth range (mm) | None | 300–650 | 250–450 |
| Expected shelf length (mm) | **1175.4** | **575.4** | **975.4** |
| `Cab_Shelf_X` (mm) | 12.3 | 12.3 | 12.3 |
| `Cab_Compartment` (mm) | **398** | **452.5** | **173** |
| Shelf Z positions (mm) | **416** | **470.5, 941, 1411.5** | **191** |
| Expected left + right dado operations | **2** | **6** | **2** |
| G2 offline check count before new additions | 58 | 108 | 58 |

Common defaults: `ply_mm=18`, `back_mm=6`, `gap_mm=3`, `dado_depth_mm=6`, `slot_clearance_mm=0.5`, `end_clearance_mm=0.3`. These three examples demonstrate code reuse only. **Tall H1900 is NOT derived from measured van clearance. Overhead is NOT a certified hanging cabinet.** No vehicle envelopes, load cases, attachment engineering or CNC outputs are approved.

Expected formulae remain authoritative in **one place** (`modules/cabinet.py`):

- `Cab_Shelf_Length = W − 2T + 2GD − 2EC`.
- `Cab_Shelf_X = T − GD + EC`.
- `Cab_Compartment = (H − (2 + shelf_count)T) / (shelf_count + 1)`.
- Shelf positions and groove Z positions remain the current canonical expressions. All `Cab_*` parameter names and expressions must remain backwards-compatible.

---

## 6. Schema and hashing policy — mandatory

### 6.1 New wrapper, old generator

Build a thin versioned input layer **around** the unchanged G2 core:

```
schema 0.1 / schema 0.2 JSON
     ↓ strict load_design_spec (reject duplicate/unknown keys)
CabinetDesignSpec:
  variant, profile_version, original_schema,
  resolved_params: CabinetSpec,
  canonical_stored_spec_json, design_spec_hash,
  migrated_in_memory, hash_scheme
     ↓ build_variant (one generator call)
G2 build_cabinet(CabinetSpec) → AssemblyDefinition
     ↓ validate(assembly, actual_geometry, profile_limits=...)
independent BRep + named profile checks + managed-entity census
```

Keep **unchanged source bytes** for `modules/cabinet.py`, `schemas/cabinet_spec.py`, `components/model.py`, `components/ids.py`, `core/*`, `cad/protocol.py`, thin Fusion entrypoint and manifest, V4 baseline files, and adapter's **geometry creation** methods (`compile`, `_rectangle_profile`, `_extrude`, `_make_panel`, `_make_dado`). Read-only instrumentation in the Fusion geometry source is permitted.

### 6.2 Backward-compatible 0.1 input

- Only `schema_version="0.1"`, `module="base_cabinet@1"`. The new loader strictly validates and **resolves** sparse 0.1 input using frozen G2 defaults; base profile has no new range checks.
- Canonical stored representation of resolved input must use the **unchanged G2 serialiser**, retaining original int/float behavior. **Never rewrite** stored 0.1 JSON in existing Fusion documents merely to upgrade it; measure mode must be read-only.
- The empty-design/no-spec-file default's actual legacy hash, independently verified, is:

  `a0a43e005535b33f069dd786dc847682734819a09bd0803650688bb5e4b0a750`

- Distinguish **raw stored attribute SHA-256** (checks bytes of unchanged saved text) from **legacy canonical spec hash** (hash of canonical text). For a previously saved 0.1 design with noncanonical whitespace or order, raw stored text may differ even when its canonical meaning is equivalent. Report both correctly when useful.

### 6.3 New 0.2 input

- `schema_version="0.2"`, `module="cabinet@1"`, `variant in {base,tall,overhead}`, integer `profile_version=1`, fully resolved `parameters` matching the original `CabinetSpec` fields.
- Canonical 0.2 JSON sorts keys, uses compact separators, explicit finite millimetre numbers normalized to floats (without allowing `bool`), and pins profile version. Stable 0.2 `design_spec_hash` is SHA-256 of that canonical JSON.
- Unsupported version, variant, profile, incorrect module, misspelled keys, duplicate keys, invalid IDs, infinity/NaN, excessive nesting/size, wrong numeric types, and impossible initial bounds are rejected with **actionable errors before CAD mutation**. Input cap: **64 KiB** for spec files.
- Profile defaults and bounds are immutable per `variant@profile_version`. A future profile change must use a new profile version rather than silently changing existing saved designs.
- **Hash separation:** `assembly_legacy_spec_hash` / `AssemblyDefinition.spec_hash` identifies the legacy core's canonical parameter spec; `design_spec_hash` identifies the **actual saved versioned 0.1/0.2 document**. Do not put a 0.1-derived hash into a field labelled the definitive 0.2 design hash. Report version, hash scheme, variant, profile and stored attribute hash on both build and measure paths.
- For G2 legacy documents: the new reader must parse, measure, report migration-in-memory without modifying root attributes, and preserve the original hash.

### 6.4 Invariants for reports and changes

Existing JSON/TXT report fields must remain usable (`parameters_read_from_fusion`, `parameters_mm`, `mode`, `document_name`, `fusion_version`, `spec`, `spec_hash` where legacy meaning is maintained, and full validation check records). Add explicit new fields instead of renaming old ones without migration. If a field is ambiguous, document legacy meaning and introduce a clearly named replacement.

Profile range checks must use **live Fusion values after user edits**, not only initial spec defaults. Missing/unreadable live parameters produce UNKNOWN, not nominal-value PASS. No silent parameter clamp. The G2 geometry checks remain identical, with new check IDs added rather than rewriting old ones.

---

## 7. Approved source changes, file by file

All paths below are within `prototypes/claude-v5/` unless stated otherwise. Reconcile exact locations against the latest checked-out branch before committing. This is the **implementation contract**, not a demand for unnecessary refactors.

| File / location | Allowed change | Acceptance guard |
|---|---|---|
| `VanCabinetJoineryV5/vandesign/schemas/design_spec.py` **new** | Strict versioned loader, 0.1 passthrough, frozen defaults, canonical 0.2 spec + hashes | Full 0.1 hash roundtrip, bad JSON rejected before mutation |
| `.../vandesign/modules/variants.py` **new** | Immutable data profiles, one call to `build_cabinet`, profile metadata/limits | No `Panel`, `Expr` or geometry creation in profiles |
| `.../vandesign/verification/report.py` | Optional numeric limit metadata for new range checks | Old check JSON layout unchanged when fields absent |
| `.../vandesign/verification/validate.py` | Add optional `profile_limits` and `entities.managed_ids` checks | Same original named checks, additional checks only; FAIL/UNKNOWN fail closed |
| `.../vandesign/verification/geometry_source.py` | Read-only `managed_ids()` protocol | Safe `None` on unavailable enumeration |
| `.../vandesign/cad/fusion/adapter.py` | Read-only census implementation, exposed original stored spec text if needed | Construction and `participantBodies` methods byte-identical |
| `.../vandesign/cad/fusion/runner.py` | Integrate versioned load, build/measure metadata, original stored-hash before/after | Preserve both original parameter-report maps, TXT/JSON, exception handling, no measure-mode mutations |
| `specs/base.json`, `specs/tall.json`, `specs/overhead.json` **new** | Fully resolved 0.2 fixture files ready to copy as `cabinet_spec.json` | Exact profile-version recording, no guessed fitting certification |
| `tests/...` **new** | Frozen snapshots, versioned spec, profile bounds, simulated geometry/fault tests | Run unchanged pre-existing 31 tests first; no default regression |
| `FUSION_TEST_PROTOCOL_G3.md` **new** | User-readable per-variant real-Fusion procedure and evidence table | One cabinet per fresh design, avoid overwriting G2 golden |
| `tools/fusion_cut_audit_g3.py` / Fusion script folder **new** | Extend original cut-participant audit to **all** dado ops | Uses stored intended target list, exactly one permitted participant per feature, no shelf target, restores timeline in `finally` |
| `README.md`, `NOT_IMPLEMENTED.md`, status docs | Accurate scope and status; existing G2 evidence links | Do not say unperformed G3 Fusion tests passed |
| `src/vandesign/` | **No G3 geometry-code edits** | Future integration design note only |
| `baseline/`, V4 files, original geometry generator | **NO EDITS** | Hash/golden test must prove unchanged |

**Be wary of circular imports** between new `schemas/design_spec.py`, profile registry, and existing `CabinetSpec`. Resolve using clear pure-data dependencies and tests; do not weaken the one-generator rule.

---

## 8. Delivery sequence — start now, maintain momentum

**Claude may proceed C0 → C5 without stopping for permission**, as long as each stage passes the stated safety gates. Keep changes on the G3 feature branch or a child working branch; create a **draft PR targeting `feature/v5-fusion-adapter`**, not directly `develop`, to keep integration separate. If Claude has only anonymous read access, supply a patch/ZIP and precise base commit SHA instead of claiming a push succeeded.

| Stage | Work | Required evidence |
|---|---|---|
| **C0 — Freeze golden source** | Record branch SHA; run prechange suites; freeze canonical base assembly snapshot for all 10 shelf-count × door-count combinations, parameter expressions, order, IDs, panels/ops and target ownership; source hash protected files | Full baseline diff and exact tests; no geometry change |
| **C1 — Versioned strict spec loader** | Implement 0.1/0.2 loader, canonical 0.2 hash, frozen 0.1 defaults, strict duplicate/unknown rejection, load metadata | Migration matrix M1–M14 green; G2 serialization unchanged |
| **C2 — Data profiles + limits** | Base/tall/overhead fixture profiles and named live range checks; independent hand-computed fixtures | One generator, no new geometry, original checks unchanged, out-of-limit FAIL |
| **C3 — Read-only managed census** | Extend `GeometrySource` and Fusion adapter for exact managed IDs and multiplicities; add extra validation check | Simulator/mock duplicates/missing/unexpected fail, API-unavailable UNKNOWN, G2 58 named checks retained |
| **C4 — Runner + fixture integration** | Wire loader and profile into build/measure, preserve report fields, versioned hashes, stored-spec checksum, three 0.2 fixture files | Default no-file build exactly legacy 0.1, old design measure read-only, mock runner suite green |
| **C5 — Audit + field-test packet** | Extend original audit script; G3 test protocol, docs, final offline test/CI, draft PR or patch | All Python 3.10/3.12 jobs success; untouched G2 source protected; **real-Fusion G3 status stays NOT RUN** |

After each commit run the existing baseline and new regression suite. If a step fails: fix or revert the step; **never fabricate green evidence or relax critical checks**. Do not add a broad architectural refactor as a shortcut.

**At the end of C5, return in one response:** exact branch and head SHA, commits and changed-file diff, why construction files are identical, implementation notes, migration/hash table, all test commands/results, CI URLs, known limitations, G3 user-facing Fusion run package, read-only cut-audit instructions, and any important unresolved decisions. The reviewer will inspect the completed change set and then guide the user through Fusion one step at a time.

---

## 9. Automated verification — minimum matrix

### 9.1 Existing suites must stay green

From repository root:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

From `prototypes/claude-v5/tests/`:

```bash
python -m unittest discover -v
```

In CI, verify **both Python 3.10 and 3.12**. Existing G3 starting branch runs all these under `.github/workflows/python-tests.yml`; the prototype suite includes the mocked `test_runner_reporting.py`. Offline `SimGeometry` is **not** Fusion.

### 9.2 Golden geometry and schema

- All 10 combinations of shelf count **0–4** and door count **1–2**, preserving G2 order, stable IDs, panel expressions, cut operations, target/mating IDs, parameter expressions and canonical 0.1 hashes; all are generated from the **pre-G3 pinned source**, not from refactored code.
- G2 default hash exactly `a0a43e005535b33f069dd786dc847682734819a09bd0803650688bb5e4b0a750`.
- Legacy sparse, int-vs-float 0.1 hashing and raw stored bytes remain distinguishable. Old saved 0.1 specs must load without upgrading their stored data.
- 0.2 full and sparse specs for base/tall/overhead round-trip deterministically; incompatible fields, versions and corrupt/duplicate JSON must produce `SpecError`.
- Versioned 0.2 `design_spec_hash` is distinct from `assembly_legacy_spec_hash`, including 0.2 base with geometrically identical parameters.
- Failed profile constraints at **initial build** must prevent CAD mutation; the same failed policy after edits must be reported as explicit FAIL without changing user parameters.

### 9.3 Geometry + fault injection

- Three variants each PASS in simulated backend, including edits to dado depth, width, ply, **height** and depth within provisional ranges; exact shelf Z redistribution and formula parity proven.
- Every shelf has exactly **two** dado ops, one cutting only `panel.left.001`, the other only `panel.right.001`; **tall has six ops** across three shelf levels. Never use a shelf as cut target.
- All original named BRep containment probes and unmodified shelf volume checks remain present and PASS in simulated validation; cutting shelf accidentally must FAIL for all variants.
- Missing grooves, unreadable parameters, unavailable BRep containment, unavailable managed IDs or failed API calls cannot return overall PASS.
- New census must identify **duplicates by multiplicity**, missing and unexpected managed IDs; a matched set of unique IDs alone is insufficient. Also test actual user parameter, component and feature count stability across repeated measure calls in Fusion.
- Report **check IDs and statuses**, not only totals; optional snapshot counts before new checks were base 58, tall 108, overhead 58. A design with zero shelves may have one fewer check due to no joined-panel interference test; do not hardcode an invariant 58 or 108.

---

## 10. Real Fusion G3 protocol — pending user-run, required for completion

**These tests have NOT yet been run in Fusion and must remain NOT RUN/UNKNOWN until reports exist.** Do not provide fake screenshots, versions, audit outputs or successes.

### F0 — safeguard legacy design

1. Before running any G3 script, **make a saved copy** of the trusted existing G2 design `v5-smoke-test`; never risk the only verified copy.
2. Run the new code on the **copy**, in `measure` mode; record raw stored G2 spec SHA-256 before and after. Confirm no new parts, features, parameters, attributes or changed geometry; all relevant G2 checks still PASS.
3. Use an independent **new empty design**, with **no spec file**, to prove the exact legacy 0.1 default; repeat **G2 A–E** and verify **1185.4 mm** for E2 at 15 mm ply/dado8.

### F1/F2/F3 — one new design per profile

Create and save **separate** history-enabled Fusion files: `v5-g3-base`, `v5-g3-tall`, `v5-g3-overhead`. For each, place the corresponding versioned fixture file as `cabinet_spec.json` next to the script before first build; do not accidentally overwrite a different cabinet's spec or run into an already populated design.

1. **Build:** run the script once in a fresh empty design. Save raw JSON and TXT, Fusion version, exact fixture and returned verdict; no FAIL/UNKNOWN accepted.
2. **Reruns:** run again twice in measurement mode. Confirm exact expected managed ID multiplicities and **no extra components, features, bodies, or user parameters**; compare counts before/after (census alone is not enough).
3. **Parametric scalar edits:** change one parameter at a time, rerun to measure, and compare actual body BRep/bboxes/volumes/groove probes. Include allowed dado depth change (6→10), plywood (18→15), width, depth, and **height** edits. Confirm tall (three shelves/six grooves) under multiple height values; example height 1900→2000 gives `(2000 − 5×18)/4 = 477.5 mm` compartment height if ply stays 18.
4. **Out-of-range negative test** (tall/overhead only): example tall height 2300 mm (above provisional 2200 max) → a **named profile range FAIL**, with the actual live value and limit. Script must not alter the value; restore valid range and remeasure PASS. Record results separately from normal PASS runs.
5. **Save → close → reopen → rerun:** report must PASS, spec identity and variant version persist, geometry remains readable.
6. **Extended cut-target audit:** iterate **every** `dado.*` extrusion; each must be a Cut operation with **exactly one** allowed side-panel body, and not a shelf. **Tall must show 6/6 PASS** and history timeline restored to end. Any missing/duplicate feature/ambiguous body = FAIL or UNKNOWN, never a pass.
7. Archive all reports under the appropriate G3 evidence folder (with private/customer data redacted, if any) and update Issue #4. Only then can G3 be proposed for completion.

**No claim of structural safety or actual vehicle fitment follows from these tests.** Each is a test cabinet profile, not a releaseable manufacturing specification.

---

## 11. Known risks, safeguards and issues not to hide

1. **0.1 → 0.2 migration:** old `CabinetSpec.from_dict` accepts ONLY 0.1; adding 0.2 at the wrong layer breaks existing Fusion files. Use wrapper and frozen defaults.
2. **Inconsistent hash meanings:** legacy `AssemblyDefinition.spec_hash` is not the full new 0.2 design hash. Keep both traceable and labelled.
3. **Duplicate managed entities:** existing `FusionGeometrySource` diagnoses duplicate component stable IDs, but does not emit a definitive named validation check for all present/missing/extra IDs. G3 adds a fail-closed census; actual rerun stability still needs Fusion evidence.
4. **Global parameters and unscoped IDs:** cannot place two G3 cabinets in one Fusion document. Do not “solve” it by changing old IDs now.
5. **Build failure partial state:** a failed Fusion construction can leave partial CAD in an unsaved design. If it happens, **close without saving** and create a new empty design. Never mask the error by running on a partially built design.
6. **Spec file location:** file next to the installed Fusion script. No spec = legacy base; specified 0.2 file selects the variant only **on first build**. Rerunning an existing managed design reads stored spec instead of the local file.
7. **Read-only marker movement:** cut audit changes timeline marker temporarily; restore in `finally`; if restore fails, report FAIL/UNKNOWN and alert user before editing design.
8. **V4 provenance:** delivered V4 rev2 archive hashes match source delivered to the project, but no independent proof yet that these exact bytes equal the final file executed by the user — Issue #1 remains OPEN.
9. **Repository visibility:** owner recently made the project public for Claude access. Public GitHub contents and commit history may be visible to anyone. Avoid committing secrets, customer names, private measurements, machine credentials, or unredacted personal data.
10. **Do not infer tests:** Python 3.10/3.12 CI green is not substitute for Fusion BRep audit; simulations are development evidence only.

---

## 12. Acceptance conditions and reporting protocol

### Development-complete condition (C0–C5)

C0 source hashes/golden snapshots from pre-change G3 parent + all unchanged named G2 tests; new data-only profiles and strict 0.1/0.2 loader; correct hash semantics and immutable schemas; fail-closed identity census and live range checks; prototype and foundation tests green on Python 3.10/3.12; full G3 user-run Fusion plan + reliable cut-audit source; documented patch or draft child PR. **This is CODE COMPLETE / AWAITING FUSION, not G3 accepted.**

### Actual G3 gate-complete condition

All three variants independently build, edit, measure, save/reopen, pass actual BRep geometry and correct left/right cut participant tests in real Fusion; no duplicate managed features after rerun; G2 legacy saved design and fresh A–E remain validated; exact tested commit SHA and raw evidence are recorded. The owner/reviewer then decides on issue closure and merge. **Do not merge G2 PR #3 or claim manufacturing approval automatically.**

### Claude's final delivery format

Provide (1) exact SHA and branch, (2) brief executive summary, (3) file-level diffs and explicit list of source files provably unchanged, (4) migration/hash behavior and sample 0.1/0.2 JSON, (5) test command/log/CI matrix, (6) full real-Fusion manual protocol and audit tool, (7) known risks and `NOT RUN` tests, (8) GitHub draft PR link or attached patch/ZIP if direct writes are unavailable, and (9) the **single next user action** required to test G3 in Fusion.

When designing user-facing instructions for the project owner, give **one precise Fusion step at a time**, request the resulting screenshot/TXT/JSON, then continue. Avoid risky manual editing of working cabinet features; prefer reproducible scripts and read-only audits.

---

## 13. Canonical links and artifacts

- [Current G3 branch](https://github.com/AnyBuzzin/van-design-system/tree/feature/v5-g3-cabinet-variants)
- [G3 Issue #4 — requirements and reviewer decisions](https://github.com/AnyBuzzin/van-design-system/issues/4)
- [Original G3 Claude handover (historical context)](https://github.com/AnyBuzzin/van-design-system/blob/feature/v5-g3-cabinet-variants/docs/ai/CLAUDE_V5_G3_HANDOVER_2026-10-14.md)
- [G2 smoke-test protocol and verified results](https://github.com/AnyBuzzin/van-design-system/blob/feature/v5-fusion-adapter/prototypes/claude-v5/FUSION_TEST_PROTOCOL.md)
- [Real Fusion G2 cut-target audit evidence](https://github.com/AnyBuzzin/van-design-system/blob/feature/v5-fusion-adapter/prototypes/claude-v5/docs/test-results/cut_audit_20261014_174320_047406.txt)
- [G2 Issue #2 — completed](https://github.com/AnyBuzzin/van-design-system/issues/2)
- [G2 draft PR #3 — do not merge](https://github.com/AnyBuzzin/van-design-system/pull/3)
- [G0 exact V4 provenance Issue #1 — still unresolved](https://github.com/AnyBuzzin/van-design-system/issues/1)
- `VanDesign_V5_System_Architecture.md` section 12 (included in optional companion file packet if Claude cannot find it in the repository)
- Claude's `G3_PROPOSAL.md` v2 in the attached handover package (user-provided review copy)
- Original `VanDesignCutAudit` Fusion script in the attached handover package, separate from committed repository sources

**Immediate instruction:** *Start C0. Use the current GitHub branch. Keep the proven generator and cut construction unchanged. Continue C1–C5 under green CI; submit full implementation for review; schedule real Fusion verification afterward.*