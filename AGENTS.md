# VanDesign — active AI engineering instructions

**Read first:** [owner-approved working plan, Issue #36](https://github.com/AnyBuzzin/van-design-system/issues/36) including newest comments, [current project status](PROJECT_STATUS.md), [roadmap](docs/ROADMAP.md), and [precision/cut-ownership standard](docs/standards/precision-and-ownership.md). **The current Issue #36 body supersedes its earlier, explicitly superseded task lists**; archived handovers are evidence, not instructions.

## Roles and workflow

- **Owner:** product direction and owner-reserved safety/business decisions. Do not ask the owner to interpret routine Python tests or technical review verdicts.
- **Vision:** coordinates active sessions and concise owner updates, prevents duplicate work; GitHub is authoritative.
- **Jill:** technical direction, constrained priorities and architecture review.
- **Astra:** one primary implementation, proportionate offline tests and clear draft PR/evidence.
- **Jack:** independently reviews actual source/geometry evidence, requests corrections and records PASS/FAIL/UNKNOWN. Shared GitHub credentials do not make role-labelled comments independent GitHub account approvals.

Use existing ChatGPT desktop messages where they actually reach active agents; use GitHub issues/PRs for substantive decisions. A posted comment **does not automatically wake or operate a dormant agent**. One primary implementation task and a separate independent review/planning task are usually enough. Avoid duplicated issues, big dependent PR stacks and paperwork solely to keep agents busy.

## Engineering invariants

- **src/vandesign is the only maintained Python runtime.** Historic V4 and prototypes/claude-v5 sources are evidence, never a second runtime or automatic import source. Keep CAD-neutral millimetre geometry outside the Fusion adapter; use adsk only at the adapter boundary.
- Preserve versioned standalone specifications, deterministic stable component IDs, parametric expressions and explicit owned boolean-cut participants. Refuse ambiguous IDs, cuts or invalid/nonfinite parameters. Do not silently weaken adapter empty-root guards or reinterpret its singular stored cabinet specification as composition provenance.
- Verify changed CAD behaviour with **actual Fusion BRep measurements** (bounds, net volumes, contacts, cuts/participants, interference), not only calculated boxes, mocks or screenshots. If a measurement is absent/invalid, record FAIL or UNKNOWN, never PASS.
- Keep verified older data and negative reports. Do not rerun unchanged G3/G4 campaigns by default. Never delete historical evidence just to reduce file count.
- Protect existing unsaved/dirty CAD fixtures, cloud IDs, installed Runner/configuration and queue. Do not save, close, discard or modify protected designs without explicit owner authority. Never publish credentials or raw private identifiers.
- Do not claim CNC/manufacturing, structural load, anchoring, electrical, road legality or measured vehicle fit without separate physical/evidence qualification.

## Operating permissions — see Issue #36 for activation state

1. **Active offline work:** within the owner's currently approved queue, agents may plan, implement, run offline tests, review and submit one focused draft PR per independent milestone without repeated owner prompts. Start from freshly checked integrated develop. State files/contracts, refusal cases, non-goals and rollback boundary in brief.
2. **Delegated merges to develop:** **only after** the already approved branch protection, required Python 3.10/3.12 checks, credible independent reviewer identity/accepted approach and activation evidence are actually in place. Until then do not merge or direct-push. For an activated merge: verify exact reviewed head/scope, green required CI and current base, squash merge, then verify post-merge CI; no unrelated or status-only direct commits.
3. **Disposable live Fusion:** **only after** the staged trusted-document baseline/pinned-helper/pilot/class requirements have been fulfilled. No live socket/API request (including diagnostics) is implied by an offline plan. For approved sessions, fail closed on source/hash, document inventory, capacity, Runner state or geometry ambiguity; never replay a consumed one-shot or touch protected fixtures.
4. **Owner-reserved:** main/release/tag, security controls, Runner installation/configuration, protected CAD files, persistent saves/reopens and higher-risk product/architecture scope. Escalate a **specific blocker**, not repeated approvals for routine coding or testing.

## Current technical priority

Build and measure **one combined bed+base-cabinet model** with existing V6.2/V6.3 symbolic composition, initially **OFFLINE helper preparation** until Fusion gates activate. Default bed at X=0 and cabinet at X=1500 mm: 11 expected panel solids, 2 cabinet-side dado operations and a nominal 100 mm X gap. Preserve source and original geometry/cut ownership. The composition is **not yet live-qualified**. After live baseline PASS, combined edits/restoration are a separate focused increment. [Status](PROJECT_STATUS.md) · [Plan](https://github.com/AnyBuzzin/van-design-system/issues/36).

## Review and reporting

One task → one focused PR. Run proportionate installed-wheel/unit/refusal tests plus CI; Jack checks meaningful deltas and evidence independently. Publish one short PR/milestone summary with observed PASS/FAIL/UNKNOWN/NOT RUN, hashes/links where needed, genuine blockers and next useful action. Vision gives the owner a single session recap rather than a stream of administrative handovers. **No merge or live permission is inferred from successful tests alone.**
