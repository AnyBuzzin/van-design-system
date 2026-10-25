# PR #14 compatibility checkpoint — 2026-10-15

Reviewed PR14 head: 800b34e7428a285bf1146523bdb575b3fc84db5a.
PR13 head: 9a94947176416531be2305a4c8a2dfe2a8a89d39.

## Results

- PASS: recorded reviewed-wheel SHA-256 matches the actual local wheel (see bundle-audit.json).
- PASS: both generated bundles have all 31 manifest entries present with matching hashes; their 29 Python package files match the reviewed wheel byte for byte. Unexpected non-cache files are rejected by the audit. Python cache files are not deployment sources and are excluded.
- PASS: isolated installed-distribution check, version 0.5.0, canonical generator identity/default hash and CAD-neutral imports without adsk (installed-check.json).
- PASS: 8 focused compatibility/deployment tests, including historical source parity, legacy API, overwrite refusal, isolated mocked launchers and existing runner loader resolution (focused-tests.txt). These are OFFLINE tests.
- PASS: PR13 head is an ancestor of PR14 head. No diff in legacy/v4-verified or prototypes/claude-v5/VanCabinetJoineryV5 between those heads.
- UNKNOWN / BLOCKED: actual Fusion runtime origin, default BRep validation, dado participant audit, parameter edit/restore and original-geometry recovery. No live jobs or CAD operations were attempted in this checkpoint.

The read-only runner heartbeat was marked stopped, with utc 2026-10-15T01:48:14.905+00:00 and runner_version 0.4.0. Its started_utc field is later than its final heartbeat; this inconsistent/stale file is not proof of a currently responsive process. Its installed configuration still targets historical G3/prototype folders, not the reviewed generated bundles. Restart alone would not qualify PR14.

## Smallest manual route, without replacing the runner

1. In Fusion, leave all existing tabs untouched; File > New Design. Keep only the new empty unsaved tab active. If editable capacity is unavailable, stop; do not change existing document status.
2. Utilities > Scripts and Add-Ins > Scripts > add/select a script folder:
   C:\Users\Buzz\Documents\Codex\2026-10-15\referenced-chatgpt-conversation-this-is-an-3\work\review-fusion-bundles\VanCabinetJoineryV5
   Select VanCabinetJoineryV5 and Run. Do not select the repository's unbundled launcher or historical installation.
3. Preserve the generated reports under that bundle's reports directory. A successful build message alone does not close this checkpoint. Actual in-process module-origin evidence must also be captured before claiming authoritative-runtime loading; the current report does not include that field.
4. On this new disposable document ONLY, Modify > Change Parameters. Record the original Cab_Width expression; increase it by 10 mm. Rerun the same generated script to measure actual BRep, then restore the exact original expression and rerun. Retain all three reports; require all measured checks PASS and restored geometry equal to baseline within existing tolerances.
5. Run the existing VanDesignCutAuditG3 script on this disposable tab and preserve its report. Its folder is prototypes/claude-v5/tools/VanDesignCutAuditG3 in the repository. Require each dado cut's exact intended participant; missing/unreadable evidence remains UNKNOWN/FAIL.

This is a pending procedure, not an executed Fusion result. No existing document should be saved, closed or edited. Alternatively, a separately approved runner deployment/configuration change could enable autonomous testing; that change was explicitly outside current authorization and was skipped. No installation or queue was changed.

## Integration readiness / Jill's next review

Review PR13 first as the aggregate integration base, then PR14 as its package-only child. Select either the aggregate route or the original sequential stack, never both. After an eventual PR13 merge, rebase/retarget PR14 as appropriate and recheck its diff; do not merge while live deployment qualification is open. Both PRs remain draft and unmerged.

No new packaging defect was reproduced by the focused checks, so no production code fix or new test framework was introduced. Jill should review installed-wheel provenance/deployment selection, the unchanged migrated CAD methods and preserved legacy API, and the live evidence above when available. The original G0/deferred G3/G4 gate limitations remain open. Full campaigns were not repeated. No production, manufacturing or real vehicle-fit approval is implied.

This checkpoint adds only a reproducible read-only artifact audit and evidence. The audit can be rerun with an isolated interpreter using audit_bundle.py <original-work-directory>. Existing untracked editor/cache files were not committed.
