# VanDesign roadmap and stage gates

**Current authoritative roadmap as of 2026-10-15.** [Current project status](../PROJECT_STATUS.md) is the operational record. The architecture's **V5 G0–G5 numbering** governs V5; older starter roadmap labels were superseded and historical Claude handovers must not be treated as live assignments.

**Development baseline:** `develop`, aggregate verified merge `b799db8` (PR #14). `main` is a separate stable line; **no G5 or manufacturing release has occurred**.

## V5 gates — completion requires evidence, not feature existence alone

| Gate | Intended deliverable | Status / next proof |
| --- | --- | --- |
| **G0** — V4 exact tested baseline | Cryptographically recorded actual executed V4 `.py` + `.manifest` associated with original Fusion run | **OPEN**, [issue #1](https://github.com/AnyBuzzin/van-design-system/issues/1); bounded provenance investigation, never substitute a candidate archive silently |
| **G1** — CAD-neutral domain core | Typed dimensions, versioned specs, frames, explicit IDs/cuts, one distributable runtime | **Integrated and package-verified** in `src/vandesign`; wheel and legacy APIs exercised, but broader engineering qualification follows feature gates |
| **G2** — Fusion adapter | Parametric panels, explicit cut participants, BRep verification and report generation | **PASS for original fixture**: A–E 58/58 each, independent dado ownership audit |
| **G3** — one-core cabinet variants | Base, tall and overhead variants with typed data specs and actual Fusion validation | **IMPLEMENTED / PARTIALLY ACCEPTED / OPEN**: substantial base/tall/F3 partial evidence; finish F0 legacy regression and outstanding overhead F3 depth/height/negative/persistence/cut ownership without repeating completed work |
| **G4** — safe change/regeneration engine | Preview changes, stable ownership, drift/manual-change handling, rollback and scalar/structural updates | **WIDTH-ONLY SUBFEATURE ACCEPTED / OPEN**: base width update measured in Fusion; next prove ONE structural change (e.g., shelf count), restoring original on failure and explicitly dealing with manual divergence |
| **G5** — V5 engineering release candidate | Supported-version contract, reproducible installation, traceable specification/geometry validation, reviewed cut-list preview, explicit limitations and release acceptance | **NOT RELEASE-QUALIFIED**; begin only after scoped G3/G4 gaps and release policy defined |

### G5 acceptance contract (planning, not implementation authorisation)

The first G5 checkpoint should state **exactly which V5 cabinet variants and transformations are supported**; retain immutable source/parameter/design identity and a deterministic test/report record; generate a **non-manufacturing cut-list preview** derived from verified panels; compare preview measurements against the expected panel bodies; and record explicit failures/unknowns, versioned artifacts, and human release sign-off. Manufacturing-grade cut optimization, tooling, toolpaths, CNC, structural load certification and commercial compliance belong to separate later gates.

Do not count the currently demonstrated interior or vehicle-space fixtures as automatic G5 acceptance. Review whether such demos are in G5's supported scope before adding qualification tasks.

## Sequencing to finish V5 efficiently

1. **Stabilize the integrated baseline:** update stale documentation/agent directions, close stale administrative items, confirm integrated CI and add lightweight branch protection.
2. **Transition the installed Fusion runner safely:** migrate from pinned historical paths to generated reviewed wheel bundles with backups and owner-approved cutover, then one disposable smoke. This is an operational prerequisite for efficient G3/G4 live tests, not a new product feature.
3. **Finish missing G3 acceptance only:** F0 and remaining overhead F3 tests (including owned dado participants and persistence), not a broad campaign restart. Do one bounded G0 provenance check without claiming closure if the original files remain unauthenticated.
4. **Complete G4's next smallest structural edit:** one safe feature at a time (for example, add/remove shelf), ensuring existing IDs/ownership, manual divergence detection and rollback. No sprawling general-purpose reconciliation engine upfront.
5. **Reach G5 engineering release candidate:** formal contract, traceable reports, cut-list preview and strictly scoped evidence; then plan staged expansion if accepted.

Each action starts on current `develop`, has its **own concise reviewable PR**, runs only proportional checks and integrates upon owner approval. Never build another long chain of dependent unmerged PRs. See [AGENTS.md](../AGENTS.md).

## Existing product experiments (not substitutes for the gates)

Real Fusion has demonstrated a first bed-and-kitchen interior (95/95 BRep checks), configurable bed/kitchen positions (171/171 across nine stages), and a simplified rectangular vehicle with two box wheel arches and a measured straight kitchen aisle (198/198 and 22 presave checks). Its nominal geometry and collision preflight are **not** measured real-vehicle integration, full navigation clearances or structural/manufacturing approval. Original results and limitations are linked from [project status](../PROJECT_STATUS.md).

## Later product roadmap — follow in order only after V5 release scope

- **V6 — Furniture library:** richer beds, drawers, worktops, partitions and later curved/intricate forms through stable core interfaces.
- **V7 — Measured vehicle integration:** actual van measurements, datums, mounting, tolerances and physical collision/access volumes.
- **V8 — Constrained AI layout intelligence:** AI proposes typed layouts, deterministic core rejects impossible designs, people approve.
- **V9 — Manufacturing pipeline:** qualified BOM, cut lists, nesting, tooling and CAM/CNC interfaces.
- **V10 — Production orchestration:** approved jobs, controlled revisions, traceability and as-built evidence.

**Do not implement later capabilities simply to keep agents busy.** No verified manufacturing, road-legal, load-bearing or measured vehicle-fit claims currently exist.
