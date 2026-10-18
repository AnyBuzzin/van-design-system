# Single authorised socket diagnostic

Astra sent exactly one `fusion_mcp_read` request with `queryType=document`, `operation=open` through the unmodified established socket/session client. No Fusion Python script was submitted, no helper executed, no retry or alternative diagnostic made.

**Communication PASS:** service returned success and six distinct open-document records with identities, names, saved/dirty/read-only fields. [Sanitised raw response](response.sanitized.json), [summary](RESULT.json). All six are saved; five are dirty. Original G3 overhead is clean. Both G4 fixtures remain dirty. The proposed bed fixture name is absent.

**State requiring review:** V5 demonstration base, tall and overhead report read-only; the G3 overhead and both G4 fixtures report editable. No state was changed. The cause/timing of these read-only flags is UNKNOWN; this diagnostic does not establish unchanged historical editability. Saved versions and editable-document capacity are not returned by this query. Do not infer full qualification readiness or all-document preservation from this single observation.

Owner now accepts the exact reviewed helper's internal pre-mutation identity/version/dirty/editability/capacity checks if complete and consistent before geometry. Hub identity is not a gate for this unsaved-only qualification. That clarification does not authorise executing the helper now. Jack must confirm communication prerequisite satisfaction and assess the observed state; return to owner before any bed execution.

No document creation/save/close/discard/edit, service restart, Runner/config change or candidate import occurred. Prior failed PowerShell diagnostic and evidence remain preserved. The raw response and client stdout are retained privately. Published response substitutes SHA-256 digests for document and project IDs, retaining all other fields and outcomes. Manifest links private original and published hashes. No session credential is published.
