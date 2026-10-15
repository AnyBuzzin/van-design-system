> **FINAL STATUS (2026-10-15):** This is the preserved *pre-integration investigation*, not the current roadmap. The original eight-head stack and source-preserving package migration were integrated into `develop` together by [PR #14](https://github.com/AnyBuzzin/van-design-system/pull/14), merge `b799db8`; GitHub Python 3.10/3.12 post-merge CI passed. [PR #13](https://github.com/AnyBuzzin/van-design-system/pull/13) became merged via ancestry, **not a second separately executed merge**. The original duplicate-package blocker was corrected in `src/vandesign`, and the reviewed `base@1` wheel-built bundle passed its [actual Fusion checkpoint](pr14-checkpoint-evidence/live-20261015/FINAL_REVIEW.md). The text below correctly records **earlier** failures and decisions, not the final merged state. Historical G0 / deferred G3 / broader G4 / G5 gates remain open. See [current project status](../../PROJECT_STATUS.md).

---

# Consolidation review — 2026-10-15

Jason approved consolidation. This branch prepares the complete accumulated stack; **nothing has merged to develop or main**. Original branches and draft PRs remain open. Eight non-fast-forward merges preserve each source head without rewriting history.

## Exact order and base

develop f77f7a0 -> #3 0dfd34a -> #5 4d4345b -> #6 917800d -> #7 ce09a53 -> #8 a4341be -> #9 820ec95 -> #10 f0826c6 -> #12 c95d131.

Every preceding head is the exact merge base of the next. Full SHAs and per-layer diff statistics are in evidence/graph.txt and evidence/diff-stats.txt. main f5a7ac8 is a separate line; its construction-time validation fix is already represented by 71ceff7 in #3. No main merge is proposed.

All eight original PR heads had successful Python 3.10/3.12 check runs; no submitted PR reviews were returned. Evidence acceptance comments are distinct from code review. API snapshots retain descriptions, comments, checks and issues #1/#4/#11.

## Blocking architecture decision: one authoritative package

Recommendation for a separately reviewed migration: make src/vandesign the sole distributable runtime, port the existing V5 package without changing its expressions/IDs, and keep Fusion entrypoints as launchers/deployment bundles generated from that source. The prototype cabinet generator is the current authoritative V5 geometry; never copy its formulas into a second implementation.

Current failure reproduced in evidence/integrity-audit.json: selecting src permits vandesign.core.joinery but cannot import vandesign.modules.cabinet; selecting the prototype permits cabinet but cannot import core.joinery. pyproject packages only src, version 0.1.0; bundled runtime reports 0.5.0. Separate suite processes and sys.path insertion hide this conflict. Both roots use regular packages, so this is not a safe namespace composition.

Smallest next reviewed change:
1. Preserve the public DadoShelf constructor/validation/properties via a compatibility facade over the existing V5 expression/parameter machinery, with boundary regression tests. Decide whether invalid legacy inputs retain their exact prior behavior.
2. Adopt cad/fusion as adapter location; adapters/fusion is currently a placeholder. Keep all adsk imports at the CAD boundary.
3. Retain thin Fusion launchers and explicit installed-source manifests. Decide release version separately from schema/generator identity; changing GENERATOR_ID can affect compatibility.
4. Test built wheel imports in a clean process, compatibility facade, no-adsk core, guarded Fusion loader paths and deployment packaging from the same source. Validate the migrated adapter on a fresh disposable design only after review.
5. Preserve G2 frozen source/hash evidence rather than editing golden fixtures to conceal a migration. Retain historical prototype sources as explicitly non-runtime provenance if needed; no deletion is authorised.

This consolidation deliberately does not implement a package migration or claim G1 complete. The installed runner still uses a frozen G3 folder for cabinet operations and the original repository for demo operations. Its source paths/configuration were read only; no installation, reload, queue job or design mutation occurred.

## Provenance and evidence

G0 remains blocked by issue #1: the exact .py AND .manifest executed in the original successful V4 session need authenticated association with that session and its report. Downloaded VanCabinetJoinery_V4.py is only a candidate, not proof. Committed V4 rev2 blobs match SHA256SUMS; Windows working-tree hashes differ due to CRLF. Both hashes are recorded. No baseline/archive bytes were changed.

G3 is partial, not untested and not complete. Newly preserved original G3-F2-F3-partial-evidence.zip records tall build/edit/restore/persistence and 6/6 cut audit; overhead build/dado/ply/width checks passed. Overhead depth/height/negative/persistence/cut audit and F0 legacy A–E under G3 remain deferred. Original campaign was stopped by the owner; it was not restarted here. Issue #4 stays open. Other local F1 archives are indexed by hash, not fully re-reviewed here.

PR #7 has a prior independent acceptance comment for width-only base@1 updates. Rechecked original G4 ZIP SHA-256 a409215f11543f65e512c4106b47f8ff7cb78e656b79cd44432edfcc86d11a74; all 62 manifest entries match bytes/hash. The runner archive manifest also verifies. General structural regeneration and manual-feature conflict resolution remain unimplemented.

Interior/configurable/vehicle reports and refusal/persistence evidence remain unchanged. Latest vehicle demonstration records 198 checks and 22 presave checks; this session does not claim fresh Fusion execution. The new vehicle-profile saved designs have no reopen evidence. Nominal envelopes/box arches are not measured vehicle fit.

## Validation and Windows integration lesson

Python 3.12.14, isolated environment, editable install succeeded. Foundation 5/5, prototype 119/119, runner 69/69; compileall succeeded. Existing tests cover frozen generator expressions/IDs, ownership/census/refusals, width rollback, queue failures, layering and legacy layouts. Logs are retained.

Initial sequential merge checkout left three profile fixtures CRLF because they predated the final .gitattributes addition; 119 tests ran with three failing subcases. git restore skipped rewriting otherwise unchanged files. Only those three files were materialized from exact HEAD blob bytes after checking their difference was CRLF-only; tracked content remains identical. Both failed logs are preserved. A fresh checkout respects #12's narrow LF rule. Do not normalize archives, weaken assertions or discard historical failures. Issue #11 remains open until #12 or an explicitly reviewed fix lands.

CI is required on the integration head for both 3.10 and 3.12. This branch changes documentation/evidence only above the original stack; no extra geometry campaign is justified.

## Stale descriptions and acceptance

PR #3's “no merge approval yet” predates Jason's approval; its architecture/provenance blockers remain real. #5's “NOT FUSION-VERIFIED” omits partial actual evidence. #7's “independent review pending” is superseded by its review comment. #8's pending JSON review is superseded by demos/evidence/independent-report-review.json. Earlier #9/#10 limits should be read with later persistence evidence and #12's LF fix, without retroactively changing historical test outcomes. Original PR bodies are preserved; this document supersedes their aggregate status.

Before sequential develop merges: approve package migration/compatibility and evidence sufficiency, resolve G0 provenance or explicitly accept an experimental integration gate with G0 open, complete code/safety review, and require integrated CI. Then merge #3, retarget each next child to develop in the order above, recheck its actual diff/checks before each merge. Do not merge this aggregate PR as well as the whole stack without deciding a single delivery route. No branch deletion or main merge.

## G5 blockers

- G0 exact executed V4 source association and report.
- G1 single installed/runtime package, release/schema policy and compatibility/deployment validation.
- Remaining G3 F0/F3 evidence, particularly overhead persistence and cut ownership.
- G4 structural changes/manual override divergence beyond the demonstrated width-only path.
- Traceable release criteria, reports/cut-list preview and approved scope; no manufacturing export/CAM qualification.
- Review final vehicle persistence if that demonstration is included in the release scope.

The smallest safe current outcome is this draft integration PR to develop for architecture and evidence review.

