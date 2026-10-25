# Guarded persistence verification — refused, 2026-10-17

The owner authorized one final close/reopen of the existing dedicated G3 overhead fixture only if it was saved, clean and the sole open document. No other document may be changed to satisfy the guard. Jack's [independent review](../jack-persistence-review.md) was read before the check.

**Result: REFUSED before any persistence operation.** The [read-only API preflight](preflight-refusal.json) found exactly one open, active document, `VanDesign-G3-overhead-remaining-20261017`, with the authorized cloud identity and complete saved version 2. However, **isModified=true**: it has unsaved changes. That fails the owner's clean-state condition. The cause of the dirty flag is UNKNOWN; this record does not attribute it to an owner edit or Fusion behavior.

No save, discard, close or reopen was attempted. No geometry, regression or cut-ownership tests were repeated. No configuration/allowlist change, installation, merge or release occurred. The installed configuration still hashes to `70bf4288f224cef35efc1760aae594c54cf39d1676a298aa10956621d81d8378`. Existing evidence, including the original safety FAIL and Jack's cabinet-persistence PASS, remains unchanged. The user's subsequent “continue” was applied to evidence publication; it did not waive the explicit clean-state restriction.

There is no post-reopen inventory or new persistence PASS because the guarded operation did not execute. Identity/version/document flags at refusal are recorded, with the cloud ID hashed consistently with earlier evidence. The private original API response remains in `issue4-live-20261017/guarded-persistence/preflight.private.json`; its hash is included in the publication.

**Next required owner action:** inspect the dedicated fixture's unsaved state and decide how it should be resolved. Do not automatically save potentially unexpected changes or discard them. Once the owner has resolved that state, recheck all conditions before any approved attempt. Jack should review this refusal in existing draft PR #21; G3 remains OPEN and no G4/G5 progression is authorized.
