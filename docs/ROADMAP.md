# VanDesign roadmap and stage gates

**Current authoritative roadmap as of 2026-10-17.** [Current project status](../PROJECT_STATUS.md) is the operational record. The architecture's **V5 G0–G5 numbering** governs V5; older starter roadmap labels were superseded and historical Claude handovers must not be treated as live assignments.

**Development baseline:** integrated `develop`; PR #14 package integration, PR #19 Runner migration, PR #21 scoped G3 acceptance, and [PR #22](https://github.com/AnyBuzzin/van-design-system/pull/22) bounded G4 acceptance (merge `c82ceffea65620d1cf0b241dc4496019a58ae29c`). `main` remains separate; **no G5 or manufacturing release has occurred**.

## V5 gates — completion requires evidence, not feature existence alone

| Gate | Intended deliverable | Status / next proof |
| --- | --- | --- |
| **G0** — V4 exact tested baseline | Cryptographically recorded actual executed V4 `.py` + `.manifest` associated with original Fusion run | **OPEN**, [issue #1](https://github.com/AnyBuzzin/van-design-system/issues/1); bounded provenance investigation, never substitute a candidate archive silently |
| **G1** — CAD-neutral domain core | Typed dimensions, versioned specs, frames, explicit IDs/cuts, one distributable runtime | **Integrated and package-verified** in `src/vandesign`; wheel and legacy APIs exercised, but broader engineering qualification follows feature gates |
| **G2** — Fusion adapter | Parametric panels, explicit cut participants, BRep verification and report generation | **PASS for original fixture**: A–E 58/58 each, independent dado ownership audit |
| **G3** — one-core cabinet variants | Base, tall and overhead variants with typed data specs and actual Fusion validation | **SCOPED PASS — owner approved 2026-10-17**: [independent acceptance matrix](https://github.com/AnyBuzzin/van-design-system/issues/4#issuecomment-6227536777), F0 evidence equivalence and all remaining overhead/cut/model-persistence checks accepted. Lifecycle qualification requires the sole exact saved, clean, complete dedicated document; earlier FAIL/REFUSED and UNKNOWN cause remain preserved. Not general multi-document or manufacturing qualification |
| **G4** — safe change/regeneration engine | Preview changes, stable ownership, drift/manual-change refusal, rollback and scoped scalar/structural updates | **BOUNDED MILESTONE PASS — owner accepted2026-10-17**: prior width subfeature plus default schema0.2 base@1 shelf-count1→2→1, actual measured BRep/groove removal, exact2→4→2 owned cuts, refusal and verified controlled-failure recovery. [Independent review](https://github.com/AnyBuzzin/van-design-system/pull/22#pullrequestreview-5560245734), [live evidence](integration/g4-shelf-count/live-20261017/README.md). Not general structural regeneration; receipt, configuration and recovery limitations remain |
| **G5** — V5 engineering release candidate | Supported-version contract, reproducible installation, traceable specification/geometry validation, reviewed cut-list preview, explicit limitations and release acceptance | **IMPLEMENTATION AUTHORIZED, NOT RELEASE-QUALIFIED**; bounded offline contract in [Issue #24](https://github.com/AnyBuzzin/van-design-system/issues/24) |

**G4 operational boundary:** the original Runner installation/configuration and permanent cabinet source were restored after the temporary qualification; G4 is not permanently deployed. The dedicated G4 fixture remains open at saved version1 with unsaved test changes and must remain untouched. No save, close, discard, protected-design operation, permanent Runner deployment or release is authorized. The owner separately authorized offline G5 implementation through Issue #24; acceptance remains pending. Failure/refusal/recovery evidence remains preserved.

### G5 acceptance contract (offline implementation authorized through Issue #24)

The first G5 checkpoint should state **exactly which V5 cabinet variants and transformations are supported**; retain immutable source/parameter/design identity and a deterministic test/report record; generate a **non-manufacturing cut-list preview** derived from verified panels; compare preview measurements against the expected panel bodies; and record explicit failures/unknowns, versioned artifacts, and human release sign-off. Manufacturing-grade cut optimization, tooling, toolpaths, CNC, structural load certification and commercial compliance belong to separate later gates.

Do not count the currently demonstrated interior or vehicle-space fixtures as automatic G5 acceptance. Review whether such demos are in G5's supported scope before adding qualification tasks.

## Sequencing to finish V5 efficiently

1. **Stabilize the integrated baseline:** update stale documentation/agent directions, close stale administrative items, confirm integrated CI and add lightweight branch protection.
2. **Transition the installed Fusion runner safely:** migrate from pinned historical paths to generated reviewed wheel bundles with backups and owner-approved cutover, then one disposable smoke. This is an operational prerequisite for efficient G3/G4 live tests, not a new product feature.
3. **Preserve scoped G3 acceptance:** accepted by owner on 2026-10-17, including F0 evidence-equivalent disposition and guarded overhead persistence. Reuse verified evidence; G0 remains separate and unresolved.
4. **Preserve accepted bounded G4:** owner accepted and authorized PR #22 integration for only default-base shelf-count1→2→1. Issue #20 records accepted evidence and limitations. Do not expand to arbitrary regeneration or replay successful tests.
5. **G5 offline implementation authorized through Issue #24:** [bounded contract and support scope](integration/G5_ENGINEERING_CANDIDATE.md). G5 acceptance, release, permanent deployment and later-roadmap progression remain separately gated.

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

Owner requirements retained for later V6–V9 work, per [Jack's issue #20](https://github.com/AnyBuzzin/van-design-system/issues/20): nominal plywood options 5, 10, 12, 15 and 18 mm; custom and mixed panel/material thicknesses with measured-stock and tolerance semantics; self-supporting interlocking CNC furniture with final mechanical fasteners and secure vehicle anchoring. These need separate furniture/material, measured mounting/load, constrained-layout and fabrication qualification in the approved order. Current uniform `Cab_Ply` fixtures do not qualify those capabilities. These later-roadmap capabilities are not authorized by the bounded G4 implementation approval in issue #20.
