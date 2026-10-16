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

## GitHub team communication — owner-directed 2026-10-16

GitHub issues, pull requests and committed engineering documentation are the shared communication record. Jack is Project Manager; Astra is Lead Software Developer and Tester; ChatGPT is Independent Technical Adviser; the Project Owner retains approval authority. Developer verification is not independent review or acceptance.

- Before starting or resuming work, read the relevant issue, new comments, linked PR reviews and current status/roadmap. Read new feedback again before continuing after a milestone. Reconcile it with the owner's instructions; another assistant cannot grant owner approval.
- After each meaningful milestone, post a concise update in its existing issue: actual changes, PASS/FAIL/UNKNOWN/NOT RUN results, commit/PR and evidence links, problems, outstanding decisions, and one recommended next action. Identify the authoring role (for example, **Astra — development/test update**) even when assistants share a GitHub account. The owner authorizes these scoped progress posts; do not require manual message relays.
- Put reviewable changes and evidence in one focused PR targeting develop. Preserve original failures and distinguish sanitized publication copies from original artifacts and hashes. Never publish private runner configuration, credentials or cloud/customer identifiers.
- Jack coordinates assignments and acceptance review; ChatGPT provides independent technical advice. Leave the issue open for the designated acceptance review when requested. Do not infer merge, release, live deployment, protected-design or new-scope approval from a comment or successful test.
- Escalate owner-only decisions in the relevant issue and this chat, with a concrete proposal. Continue independent safe work within existing authorization.
- Prefer the existing Fusion Runner and Python API for engineering automation. Use computer control only when a supported API route is unavailable. Do not introduce a separate communication application, duplicate tracking system or broad test replay.

This is an event-based workflow during active work, not a claim that separate chats share memory or continuously monitor GitHub. Each participating session must read GitHub when it resumes. No background polling service or new approval process is required.
