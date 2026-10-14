# Claude project handover — 2026-10-14

> **Snapshot, not a substitute for live GitHub state.** Before changing code, read README.md, PROJECT_STATUS.md, AGENTS.md, CONTRIBUTING.md, docs/ROADMAP.md and the latest PRs/issues.

## Mission
Build VanDesign: a reliable AI-assisted, precision-first, modular design/manufacturing platform for full campervan and mobile-business van interiors.

Architecture contract: AI proposes structured designs -> CAD-neutral deterministic engineering core calculates -> Fusion 360 adapter constructs an editable assembly -> independent BRep validation measures -> human approves manufacturing. Accurate fitment, tolerances, real vehicle reference data, long-term extensibility, and safe change propagation are core requirements.

## GitHub
- Repo: `AnyBuzzin/van-design-system` (private)
- `main`: repository foundation, core arithmetic and CI; no unverified Fusion adapter.
- `develop`: integration branch.
- `feature/v5-fusion-adapter`: full imported experimental V5 prototype under `prototypes/claude-v5/`.
- Draft PR: https://github.com/AnyBuzzin/van-design-system/pull/3 (base `develop`, must stay Draft until validated).
- Issue #1: exact Fusion-tested V4 source provenance; https://github.com/AnyBuzzin/van-design-system/issues/1
- Issue #2: V5 Fusion verification; https://github.com/AnyBuzzin/van-design-system/issues/2

## Confirmed evidence
- Working V4 cabinet had correct fit and editable parametric dado depth in user's Fusion tests.
- The V4 bug was accidental cutting of the shelf by dado cuts. Explicitly restrict boolean cut participant bodies.
- Claude's V5 archive contains 35 source files, plus docs, archived V4 rev2 and tests.
- 30 / 30 offline tests passed by independent execution in the ChatGPT analysis environment.
- Both archived baseline files match the hashes supplied in `baseline/SHA256SUMS.txt`.
- **Fusion V5 adapter has not been executed.** `Component.attributes`, `pointContainment`, complete 3D geometry, and save/reopen persistence are UNKNOWN.
- Archive hash match alone is NOT proof that its V4 files are byte-identical to the user's exact Fusion-tested copy.

## Immediate next assignment: G2 real Fusion smoke test
**Do not add AI intake, CNC exports or complex cabinets yet.**

1. Inspect the committed `prototypes/claude-v5/VanCabinetJoineryV5/` and its `README.md`, `NOT_IMPLEMENTED.md`, `REVIEW_STATUS.md`.
2. Guide installation of whole `VanCabinetJoineryV5` script folder into Fusion Scripts & Add-Ins; test only in new empty design with history on. Preserve the known-good V4.
3. Build initial model: W1200, Ply18, Dado6, End Clearance0.3 -> shelf 1175.4 mm, insertion 5.7 mm each side.
4. Change Cab_Dado_Depth to 10 mm -> shelf 1183.4 mm, insertion 9.7 mm each side, no rebuild.
5. Change Cab_Width to 1000 mm -> shelf 983.4 mm; restore 1200 before test 6.
6. Change Cab_Ply to 15 mm -> shelf 1189.4 mm.
7. Confirm target-only cuts, groove shape/opening, clearances, no unintended body interference and stable IDs and spec across save-close-reopen.
8. Collect report text/screenshots; diagnose FAIL/UNKNOWN before any PR merge.
9. Fix issues minimally on feature branch, add regression tests, report exact files, commits, and results. Do not claim Fusion verification without evidence.

## Engineering guardrails
- CAD-neutral core must not import `adsk`; Fusion-specific code is confined to adapter.
- Explicit units (millimetres at core; centimetres at Fusion API boundary).
- Stable IDs and component ownership; specified boolean cut participants, fail closed.
- No silent error swallowing; PASS/FAIL/UNKNOWN with UNKNOWN never PASS.
- Preserve `Cab_*` parametric expressions when practical.
- Treat AI suggestions as untrusted until engineering and geometric validation.
- Do not erase manually modified designs or overwrite verified V4 files.
- Structural component-count changes are not live Fusion parameters yet; require controlled regeneration.
- No claim of CNC readiness or manufacturing approval from software-only tests.
