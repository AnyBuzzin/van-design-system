# VanDesign agent workflow

Start with [current status](PROJECT_STATUS.md), then [Issue #36](https://github.com/AnyBuzzin/van-design-system/issues/36) and new feedback on the active task. Read implementation files and relevant evidence as needed. Do not reread the entire archive or roadmap every session. Latest explicit owner instructions take precedence; old handovers are historical.

## Work continuously

1. Pick the highest-priority ready task already approved in Issue #36. Check existing branches/PRs to avoid duplicate work. Use integrated develop and one focused PR per useful increment; avoid long dependent stacks.
2. Put the goal and acceptance checks in the existing issue or PR. A few sentences suffice; no separate contract, planning document or handover file unless technically necessary.
3. Implement the smallest useful change with the existing Python core, Fusion adapter and Runner. Do not add coordination frameworks or speculative features.
4. Run checks proportionate to changed behaviour. Reuse verified evidence for unchanged components; repeat tests only for a change, failure or specific evidence gap. Documentation-only work needs factual/link/diff checks and existing required CI, not a new test campaign.
5. Hand the exact change and results to the reviewer. Fix substantive findings. Integrate when the existing merge permission and checks allow, then continue the next ready task without another owner prompt.
6. If an action is blocked, record the specific reason and continue independent approved work. Ask the owner only for a concrete owner-reserved decision, with a reviewable proposal.

Astra implements/tests; Jack reviews against requirements and evidence; Vision coordinates available sessions and prevents duplicates; Jill resolves product/architecture questions when needed. Use only the roles needed for the task. Do not invent an assignment for every agent or wait for a coordinator when a ready task can proceed.

## Report once, link rather than copy

- PR: what changed, actual PASS/FAIL/UNKNOWN/NOT RUN results, evidence links and material limits. That is also the technical handover.
- Active issue: link the PR and give only the new decision, blocker or completion. No repeated narrative, routine acknowledgements or status-only PRs.
- PROJECT_STATUS.md: the only current-status page; update briefly when accepted capability, active work or a blocker changes. Roadmap is future direction; changelog is history.
- Keep one concise milestone summary with links to reproducible raw measurements/logs. Preserve failures and existing evidence; do not create parallel copies or delete useful records to meet a file quota.
- Give the owner one brief end-of-session report. Escalate material blockers when needed; keep decision requests under about 150 words.

## Engineering rules

- src/vandesign is the sole maintained runtime. Preserve V4/prototype archives and unresolved original-source provenance. Keep CAD-neutral millimetres in core; isolate adsk imports and unit conversion at the Fusion boundary. Build deployment bundles from the reviewed installed wheel with verifiable hashes.
- Preserve stable IDs, parametric expressions, backward-compatible parameter/schema identities and explicit exact cut participants. Refuse ambiguous ownership or invalid inputs. Composition provenance is not a cabinet stored specification.
- Check changed CAD behaviour against actual BRep bounds/net volumes, contacts, cut participants and interference. Arithmetic, mocks and screenshots alone cannot qualify live CAD. Missing or invalid observations are FAIL/UNKNOWN.
- Protect existing documents, unsaved changes, private identifiers, Runner/configuration and history. Never weaken tests or erase negative outcomes to obtain PASS. Manufacturing, loads, anchoring, vehicle fit and CNC require their own evidence.

## Authority

Offline work in the approved queue proceeds now. Delegated develop merges and fresh disposable live Fusion tests require the existing [staged activation conditions](https://github.com/AnyBuzzin/van-design-system/issues/36#issuecomment-6250181462), as updated by the current Issue #36 body. Verify activation; do not add new approval layers. Shared-login role labels are not separate GitHub account approvals.

Main/releases, security settings, permanent Runner changes, protected-design changes and persistence operations retain their existing owner boundaries. No force push or sensitive-ID publication. Historical tab/capacity causes may stay UNKNOWN while a safe current baseline is established.

Use existing direct messages only where available; GitHub records decisions. Posts do not wake dormant agents or guarantee unattended execution. Stop the affected action on unexpected state; preserve evidence and continue safe work.

For detailed geometry rules, read [precision and ownership](docs/standards/precision-and-ownership.md) when relevant.
