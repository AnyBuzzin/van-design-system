# Jack — independent G3 persistence safety review, 2026-10-17

Reviewed PR #21 head `c968938d0535a8245d99058a1f0c80e377d4a9a2`, the published original evidence, local API artifacts, queue journals and the native Fusion application log. No Fusion operation, configuration change, geometry replay or merge was performed during this review.

## Findings

- **Cabinet model persistence: PASS for this fixture.** Independently recomputed complete pre/post snapshot equivalence at the recorded absolute tolerance 1e-6: same hashed cloud identity/version 2, stored spec, all parameter records, counts (16 parameters, 8 occurrences, 9 components, 28 timeline items), eight solid BRep bounds/volumes and validation records. Both validations PASS. This is not a broader persistence qualification.
- **Other-document preservation: FAIL.** Original unsaved, empty, unmodified Untitled was observed during reopen and its native Fusion session was subsequently released. Post-operation API inspection reports its reference invalid and only the saved fixture open. This is actual document closure, not merely evidence of a stale Python wrapper.
- **Likely cause: Fusion blank-document cleanup triggered by opening the saved file.** The harness explicitly closes only the exact dedicated clean saved document object, then calls `app.documents.open(df, True)`. The native log records the fixture close, fixture reopen, then another close with empty file path. No second explicit close appears in the reviewed script. Native cleanup is strongly supported, but its internal trigger/implementation is not proven by these logs; do not generalize safety for other unsaved/saved documents.
- **Classification: persistence harness/lifecycle safety gap, with no observed cabinet serialization defect.** The harness checks other documents after the operation, but lacks a preflight excluding a document state susceptible to implicit Fusion closure. It detected the failure correctly; preserve it as FAIL.

## Native Fusion log evidence

Original log: `%LOCALAPPDATA%/Autodesk/Autodesk Fusion 360/SCPQ9TRYQDTCYEUG/logs/AppLogFile20261017T011443.log`.
Private byte-preserved review snapshot: `%USERPROFILE%/Documents/VanDesign-Runner/issue4-live-20261017/jack-fusion-log-snapshot-20261017.log`.
Snapshot SHA-256: `ddde10bd5030e70e84e6bfe15728c5675589e99dce4d56e654aac669e0fba571`.
The selected source lines below preserve ordering; cloud identity and fixture cache path are redacted. Full log stays private because it contains account/cloud data.

```text
2817: 20261017T012101 D  .3100 [pim.PIMLocalService/emit] PIMLocalService:preDocumentClose message sent ...
2837: 20261017T012101 I  .3100 [DeferredSessionReleaseTask] Releasing document sessionWideID=9 path='[dedicated saved fixture cache path]'
2839: 20261017T012101 D  .3100 [pim.PIMLocalService/emit] PIMLocalService:documentClosed message sent ...
2853: 20261017T012101 I  .3100 Begin:	Open the Document with Lineage URI: [private cloud identity redacted]
2903: 20261017T012102 D  .3100 Sucessfully generated Avatars and sending Avatars to the UI for InActiveTab Document: Untitled, Avatars Count: 0
2927: 20261017T012102 D  .3100 [pim.PIMLocalService/emit] PIMLocalService:documentOpened message sent ...
2934: 20261017T012102 I  .3100 Opened Document : [dedicated fixture]
2935: 20261017T012102 I  .3100 End:	Open the Document with Lineage URI: [private cloud identity redacted]
2945: 20261017T012102 D  .3100 [pim.PIMLocalService/emit] PIMLocalService:preDocumentClose message sent ...
2950: 20261017T012102 I  .3100 [DeferredSessionReleaseTask] Releasing document sessionWideID=1 path=''
2952: 20261017T012102 D  .3100 [pim.PIMLocalService/emit] PIMLocalService:documentClosed message sent ...
```

The original Untitled remains visible to Fusion's logging during the open at line 2903; session 1 with empty path closes after the fixture-open records. The API inspection independently establishes that the protected blank tab is gone. Queue journals are parameter-restoration journals, not native document-lifecycle logs: their emptiness cannot prove that no tab closed.

## Other independent checks

- All 39 published artifact SHA-256 values match Git blob bytes.
- Three current runner journals have zero entries and the exact hashes published in `verification-summary.json`.
- Installed config bytes match the published original SHA-256 `70bf4288f224cef35efc1760aae594c54cf39d1676a298aa10956621d81d8378`.
- Python 3.10/3.12 CI passed on reviewed head c968938. Any subsequent documentation commit needs its own CI status; CI success does not waive this Fusion safety FAIL.
- Existing depth/height restoration, expected 800 mm invalid-height outcome and 2/2 cut ownership are retained; no reason to replay those successful tests. F0's existing evidence-equivalence disposition is unchanged.

## Smallest corrective action and approval boundary

Add a narrow precondition to this existing persistence test procedure: **abort before any save/close/open if any other document is open**. Do not close, save, rename, modify or recreate other documents to satisfy that precondition. This deliberately conservative restriction avoids trying to predict Fusion's blank-tab cleanup and is not a new runner framework or a claim about all document combinations. Check explicit fixture identity, clean/completed save and exact permitted target again immediately before the operation; retain before/after document inventories.

The fixture is reported as the sole open, saved, clean document now. That is evidence of the prior session, not permission or proof of current state: recheck read-only before any future operation. One owner-approved close/reopen of that exact dedicated saved fixture can test the corrected procedure, using the existing snapshot comparison. No depth/height/cut replay, new cloud file or extra save is necessary. Any automatic empty tab created during that isolated test is test-owned and should be identified as such; it must not be confused with a pre-existing protected tab.

**Approval required before that retest:** permission to close/reopen only `VanDesign-G3-overhead-remaining-20261017`, contingent on it being the sole open document, saved and unmodified. If the precondition fails, abort and leave all documents untouched. Do not change the live runner configuration without specific authorization; use the already available safe Python API route.

Keep Issue #4 open and PR #21 draft. No merge, G4/G5 implementation or release authorized. Do not retroactively relabel the original safety FAIL as PASS. Acceptance needs either evidence from the narrowly approved safe retest or an explicit owner disposition of this documented limitation.
