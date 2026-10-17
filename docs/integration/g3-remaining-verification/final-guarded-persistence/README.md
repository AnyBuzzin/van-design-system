# Final owner-approved guarded persistence safety test — 2026-10-17

**Developer result: PASS for this single isolated lifecycle test, pending Jack's independent review.** The existing dedicated fixture was clean, saved and the sole open document immediately before the operation. It closed once, leaving zero open documents, and reopened once with the same cloud identity and saved **version 2**, clean and again the sole open document. No unexpected document operation was observed. This does not erase the original safety FAIL or guarded REFUSED result, and does not close G3.

The owner specifically approved this one test after the read-only dirty-state investigation. The existing authorized Fusion Python API route and local helper were reused, as in the prior persistence workflow reviewed by Jack. No new runner command, software or configuration was introduced. No new save was necessary: the fixture already had a complete, clean saved version. There were **zero save calls**, one `close(False)` on the exact verified fixture and one `documents.open` using its existing DataFile. No other document was open or acted on.

## Guards and observed states

| Stage | Observed state |
| --- | --- |
| Native preflight | One open, active, saved, unmodified `VanDesign-G3-overhead-remaining-20261017`; authorized cloud ID |
| Immediately before close | Rechecked sole exact document object, cloud ID, name, version2, saved/clean/active and cloud-complete in the same API invocation, without processing events between final guard and close |
| After sole close | Zero open documents; otherwise the script would stop without attempting reopen |
| After sole reopen | One open active fixture, same cloud ID/version2, saved, unmodified, cloud-complete |
| Independent native after-query | Same sole fixture, saved and unmodified, confirmed outside the lifecycle script |
| Native log interval | One pre-close/close sequence for the dedicated fixture, then its open sequence at 01:42:19–01:42:21 Europe/Dublin; no additional closure observed in the captured interval |
| Runner configuration | Exact original SHA-256 `70bf4288f224cef35efc1760aae594c54cf39d1676a298aa10956621d81d8378` before/after; no allowlist or other setting changed |

## Evidence

- [Before/intermediate/after inventory and call counts](lifecycle.json).
- [Native preflight](native-preflight.json), [independent native after-query](native-after.json).
- [Postcheck, original log hash and selected native event lines](postcheck.json).
- [Exact guarded procedure, with private cloud ID replaced](guarded-lifecycle.py). Publication is evidence, not an executable request: the expected identity placeholder cannot authorize a target. A local one-attempt marker prevents repeating this approved operation.
- [Original/published SHA-256 mapping](publication.json). Full originals stay local in `%USERPROFILE%/Documents/VanDesign-Runner/issue4-live-20261017/final-guarded-persistence`; cloud identifiers are consistently hashed for publication. Native account/cache data remains private.

No geometry, regression, parameter-change, cut-ownership or additional persistence test was run. Reuse the prior accepted cabinet persistence and overhead geometry evidence, [Jack's independent review](../jack-persistence-review.md), and [read-only comparison](../dirty-state-investigation/README.md). This result qualifies only the **sole clean dedicated document** precondition and observed lifecycle; it does not establish safe persistence with other open documents or explain the earlier dirty flag.

**Handover to Jack:** independently review these guards, raw states and native event ordering, then give the G3 acceptance recommendation. PR #21 remains draft and issue #4 remains open. No merge, release, G4/G5 progression or further Fusion operation is authorized by this result. The dedicated fixture remains open, saved and clean at version2.
