# Publication correction — 18 October 2026

Addresses [Jack's independent review](https://github.com/AnyBuzzin/van-design-system/pull/27#pullrequestreview-5560589288). Both stages' bounded engineering observations remain unchanged; this is only a publication correction.

Exactly16 G4-stage artifacts contained46 occurrences of6 Fusion cloud document IDs. Corrected copies use `redacted-sha256:<SHA256 of exact original UTF-8 ID>`, the same mapping as stage one; all5 shared document identities remain comparable. The original filter incorrectly expected a colon after `adsk`, missing Fusion's dotted namespace. The previous claim that all IDs were redacted was incorrect for these16 files.

Corrected artifacts:

- `before-runner-restore.json`, `capacity-preflight.json`, `final-state.json`, `first-save.json`, `no-op-proof.json`, `protected-before.json`.
- Both `job.json` and `result.json` in each of `jobs/v5demo-g4-20261018-no-op`, `preview-one`, `preview-two`, `to-one` and `to-two` (the latter four retain the same `v5demo-g4-20261018-` prefix).

[Machine-readable check and exact file list](PUBLICATION-CORRECTION-CHECK.json). Scanned all175 pre-correction PR files, including known bare lineage tokens, raw/URL-encoded and JSON-escaped identifier forms. No further affected artifacts found; no original IDs remain in the corrected publication. All170 copied-artifact hashes validate. The16 affected `published_sha256` values and `sanitized` flags were refreshed; all `original_sha256` values remain unchanged and match untouched private originals. Every corrected artifact is byte-for-byte identical to its previously published version except the identity substitutions. Measurements, engineering results, PASS/FAIL/UNKNOWN classifications and negative outcomes are unchanged. Other evidence artifacts were not modified.

## Historical exposure and owner decision

**Earlier public commits retain the exposed identifiers**, including reviewed head `2612a8a3a8b60a81ed357f6bef69d1846fef8ab9`. Correcting the current branch does not remove historical commits, existing clones, cached views or prior downloads. No Git history rewrite, force-push or hosting-side removal was attempted. No credential leak is asserted. The owner must separately decide whether to request historical-exposure remediation; any history rewrite/removal would require explicit approval and coordination. This correction makes no claim that historical exposure has been erased.

No Fusion operation, Runner/configuration change, design operation, test replay, cache cleanup, merge or release occurred. Both G4 fixtures and all existing unsaved changes remain untouched. PR27 stays draft; request Jack's focused independent re-review of sanitization, integrity and identity comparability before any owner merge decision.
