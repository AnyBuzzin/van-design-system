# Rules for AI coding assistants

Read [README.md](README.md), [PROJECT_STATUS.md](PROJECT_STATUS.md), [docs/ROADMAP.md](docs/ROADMAP.md), and [docs/standards/precision-and-ownership.md](docs/standards/precision-and-ownership.md) before modifying code. **PROJECT_STATUS.md is the current status; archived handovers and old PR descriptions are historical snapshots.**

## Engineering invariants

- `src/vandesign` is the **one authoritative maintained Python runtime**. Do not import V5 production code from the preserved `prototypes/claude-v5` historical source tree. Generate Fusion deployment bundles from the reviewed installed wheel, with verifiable hashes.
- Preserve the exact V4 archive; do not assert its original executed-file provenance until [G0 issue #1](https://github.com/AnyBuzzin/van-design-system/issues/1) is independently resolved.
- Keep CAD-neutral math in core; isolate all `adsk` imports to the Fusion adapter. Canonical lengths are millimetres, with conversion at the Fusion boundary only.
- Give components stable IDs independent of display labels. Require explicit, exact `participantBodies` for every boolean cut. Refuse ambiguous cut ownership.
- Treat unavailable measurements, failed API calls or skipped checks as FAIL or UNKNOWN, never PASS. Verify actual Fusion BRep bodies, cut ownership and restoration where changed; arithmetic-only tests do not establish CAD correctness.
- Preserve backwards-compatible parameter names and schema/generator identities unless a deliberate reviewed migration is authorised.
- Protect existing Fusion documents, unsaved changes, cloud identities, installed runner configuration and history. Never save, close, discard or alter protected designs without explicit owner authorisation. Use fresh disposable designs for tests.
- Preserve original test reports and negative outcomes. Keep tests reproducible; avoid changing golden fixtures or loosening assertions just to obtain a PASS.
- No manufacturing, CAM/CNC, structural, electrical, vehicle-fit or road-legal approval without its own qualified evidence.

## Development workflow — adopted 2026-10-15

1. **One milestone, one focused PR.** Start from integrated `develop`; review scope against the authoritative V5 gates before adding a feature. Do not build another long dependent PR stack.
2. Write a short contract: objective, files/interfaces affected, acceptance checks, explicit non-goals and rollback/safety boundaries. Existing designs and historical source are not disposable test fixtures.
3. Implement the **smallest useful increment**. Reuse the deterministic core and existing runner; do not introduce new frameworks, architecture rewrites or later-roadmap features simply because they are possible.
4. Run **proportionate tests**: offline/installed-wheel checks and CI first; only focused real-Fusion BRep, cut, restore, or persistence tests for behaviours actually changed. Reuse established verified evidence for unchanged components. Do not repeat whole G3/G4 campaigns by default.
5. Every PR and handover must identify actual PASS/FAIL/UNKNOWN evidence, link raw artifacts, state supported scope and known limitations, and say whether any installed Fusion/runner changes were made. Distinguish observed behaviour from AI-reported claims. Never invent or round up completion.
6. Review and integrate each accepted milestone promptly after appropriate approval. Keep `main` unchanged until separate release authorisation; use `develop` for development integration and keep CI green.
7. Update central status/roadmap when acceptance genuinely changes. Avoid duplicative status reports, PR handovers, and busywork assigned solely to keep agents occupied.
8. When a change needs approval, stop at that specific boundary and progress on independent safe work. Do not bypass safety controls or assume access to a live Fusion environment.

**Current scope:** Finish baseline stabilization, pinned-runner deployment migration, remaining G3 qualifications and the smallest G4 structural-change acceptance **before** G5; follow V6–V10 only in the approved order. See [PROJECT_STATUS.md](PROJECT_STATUS.md).
