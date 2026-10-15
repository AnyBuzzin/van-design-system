# Claude engineering handover — VanDesign V5 G3 cabinet variants

**Date:** 2026-10-14
**Repository (private):** https://github.com/AnyBuzzin/van-design-system
**Starting branch:** `feature/v5-g3-cabinet-variants` (branched from `feature/v5-fusion-adapter`)
**Existing G2 PR:** https://github.com/AnyBuzzin/van-design-system/pull/3 — **DRAFT; DO NOT MERGE**
**Completed G2 test issue:** https://github.com/AnyBuzzin/van-design-system/issues/2
**New G3 engineering task:** https://github.com/AnyBuzzin/van-design-system/issues/4

## 1. Important architecture correction

Read the project architecture's **Section 12**: **G3 means three cabinet variants** — base unit, tall cabinet, overhead cupboard — from the **same deterministic CAD-neutral generator**. **G4**, not G3, is the incremental change/regeneration engine, including structural edits, ownership tracking, and manual-divergence handling. Do not silently swap these milestones.

Architecture principle: AI proposes typed intent; the Python core determines geometry; the Fusion adapter creates parametric CAD; actual solids are independently verified; the human authorizes manufacturing releases. No AI/CAM/manufacturing claims at this gate.

## 2. Proven evidence — REAL Fusion 360, not simulated

Fusion **2705.1.30**; saved design **`v5-smoke-test`**. The user ran all smoke-test scenarios in the same design, each with **RESULT: PASS — all 58 checks passed**:

| Scenario | Inputs changed | Actual shelf length | Per-side insertion |
|---|---|---:|---:|
| A | W1200 / ply18 / dado6 / clearance0.3 | 1175.4 mm | 5.7 mm |
| B | dado10 | 1183.4 mm | 9.7 mm |
| C | W1000, dado10 | 983.4 mm | 9.7 mm |
| D | W1200, ply15, dado10 | 1189.4 mm | 9.7 mm |
| E1 | User-directed save/close/reopen, measure at ply15/dado10 | 1189.4 mm | 9.7 mm |
| E2 | After reopening, change dado8, retain ply15 | **1185.4 mm** | 7.7 mm |

**Correction:** an earlier human test protocol erroneously stated **1179.4 mm** for E2; **1185.4 mm** is correct because plywood remains **15 mm**: 1200 − 2×15 + 2×8 − 2×0.3 = 1185.4. The code and real-Fusion result were correct. Save/reopen was user-performed per instructions; the report itself confirms preserved named document, `measure` mode and dimensions but cannot independently timestamp the close action.

Validation covered derived user parameters, panel bounding boxes and volumes, 12 BRep groove containment probes, shelf volume unchanged by cuts, clearances and zero **joined-panel** interference pairs. Do **not** rephrase the joined-only interference result as a collision test of every possible part.

A separate **read-only Fusion API cut audit** conclusively returned:
- `dado.shelf1.left` -> **Cut**, **one participant only**, `01 Left Side` (`panel.left.001`), PASS.
- `dado.shelf1.right` -> **Cut**, **one participant only**, `02 Right Side` (`panel.right.001`), PASS.
- No shelf participant on either cut; timeline returned to end; **OVERALL PASS**.

Archived audit: [cut_audit_20261014_174320_047406.txt](../../prototypes/claude-v5/docs/test-results/cut_audit_20261014_174320_047406.txt).
Official scenario evidence/limits: [FUSION_TEST_PROTOCOL.md](../../prototypes/claude-v5/FUSION_TEST_PROTOCOL.md).
Reports A–E were supplied in chat; not all original JSON files are present in the repository.

Current CI passed on the V5 feature branch across Python **3.10 and 3.12**; original uploaded source's **30/30** offline tests also rerun successfully in the independent review container. The current prototype test suite adds one mocked reporting test (31 tests). These are NOT substitutes for the above Fusion evidence.

**G2 smoke-test verification is complete for this tested fixture.** This is not a production/manufacturing approval or universal guarantee for other geometry.

## 3. Verified baseline and unresolved provenance

Working G2 files are on `feature/v5-fusion-adapter`, especially:
- `prototypes/claude-v5/VanCabinetJoineryV5/vandesign/modules/cabinet.py` — single source of panel, shelf, dado geometry and parameter expressions.
- `.../schemas/cabinet_spec.py` — `CabinetSpec`, module currently hardcoded to `base_cabinet@1`.
- `.../cad/fusion/adapter.py` — parametric geometry, tagged entities, explicit `participantBodies`.
- `.../cad/fusion/runner.py` — build once, measure an existing cabinet, save JSON/TXT reports.
- `.../verification/validate.py` — BRep readback PASS/FAIL/UNKNOWN.
- `prototypes/claude-v5/tests/` — source tests.

**G0 open:** `baseline/VanCabinetJoinery_V4_rev2.py` hashes match Claude's delivered archive, but exact identity of the user's original successfully tested V4 local file is not independently confirmed. Track under [issue #1](https://github.com/AnyBuzzin/van-design-system/issues/1). Keep that archive unchanged.

**Integration review:** The repository also has a separate `src/vandesign` starter package. The working V5 prototype embeds its own `vandesign` package. Do **not** copy-paste formulas into the foundation or pretend the two are merged. Provide a proposed migration/interface map for a later reviewed integration PR.

## 4. Current limitations found in review

1. Only the base cabinet module identifier exists today; no explicit versioned base/tall/overhead variant contract yet.
2. `FusionAdapter.compile()` rejects a nonempty root; `Cab_*` parameters have document-wide names. **G3 means separate new Fusion designs for each variant**, not multiple cabinets in one design.
3. Structural shelf/door-count changes are fresh builds; the runner only **measures** an existing tagged design, never reconciles its structure. Structural regeneration belongs to G4.
4. Stored `spec_json` / `spec_hash` preserve the **initial** design intent while report fields `parameters_read_from_fusion` reflect **live** user edits. Do not claim the stored spec is auto-updated to match live params.
5. Measured material thickness, mounting/overhead load engineering, arbitrary manual Fusion edits, full collision matrix, CAM/exports, van envelopes and approval pipeline are unimplemented.
6. Some imported README/status lines still reflect their **pre-Fusion** state; current authoritative evidence is issue #2, the test protocol and audit above.

## 5. Immediate task for Claude: G3, not G4

Work **only** on `feature/v5-g3-cabinet-variants`. Before editing, inspect `AGENTS.md`, `CLAUDE.md`, `prototypes/claude-v5/`, tests and issue #4.

**Deliverable A — design proposal (first):**
- Specify an explicit, backwards-compatible typed variant contract (e.g. named `base`, `tall`, `overhead` profiles/presets), with schema versioning and migration policy. Preserve default `CabinetSpec` behaviour and `base_cabinet@1` compatibility.
- Propose physically plausible dimensions, shelf counts and door counts for illustrative G3 fixtures; **label them proposed** until approved. Do not imply verified mounting safety for overhead cabinetry.
- Show a single-code-path architecture: shared `build_cabinet`, no three copies of geometry formulas. Keep non-Fusion code free of `adsk`.
- Explicitly state what remains in G4 and how the eventual core-package reconciliation should be performed without disrupting tested scripts.

**Deliverable B — implementation after proposal/review:**
- Add variant presets/configuration, generator updates only where necessary, and named regression fixtures for all three variants.
- Validate schema compatibility, expected counts/IDs/target-body ownership, parameter dependency expressions, bbox/volume probes and deterministic regeneration of pure assembly specs.
- Keep existing A–E formula outcomes and V5 cut targeting unchanged. Fail closed on unknown geometric evidence, never return an optimistic PASS.
- Supply a reproducible G3 Fusion test protocol: **fresh empty parametric design for each variant**, save/reopen, independent reports, explicit cut targeting. Check actual result, don't assume a universal 58-check count.

**Deliverable C — precise return package:**
- File-by-file change list/diff against this G3 branch, test commands and raw test summary, assumptions, compatibility risks, unsupported cases, and a separate list of steps the user must perform in Fusion.
- Be clear that **offline green != real Fusion PASS**; do not mark G3 complete until the user executes three successful real-Fusion variant tests.
- Keep PR #3 draft/unmerged and V4 archived baseline untouched. Do not start vehicle fitment, multi-cabinet layouts, G4 structural changes, CNC/CAM or manufacturing outputs.

## 6. Questions to resolve before coding deeply

What variant properties are genuine engineering differences versus simply named parameter presets? How will a design and validation report record its variant/preset version without breaking the existing stored `base_cabinet@1` JSON? How should an overhead cabinet represent future mounting constraints (UNVERIFIED/NOT IMPLEMENTED today)? Can G3 be done without modifying the verified adapter, except for minimal backwards-compatible configuration/reporting changes?

**First response requested from Claude:** Send an architecture proposal and a concise G3 plan, with file-level scope and proposed fixture dimensions. Await approval before changing the verified CAD geometry.
