# G5 engineering candidate — implementation contract

Issue [#24](https://github.com/AnyBuzzin/van-design-system/issues/24) and the owner authorize offline implementation from `2da3feb8dd359fe3c0d0e50d6f8fb3568176bb74`. Acceptance and release remain pending.

Add one CAD-neutral panel-preview module/command, focused tests and traceability examples. Resolve the existing assembly; never duplicate cabinet formulas. Export one row per stable panel ID with explicit role axes, nominal thickness and quantity. Keep groove references separate. Link original reports by SHA256; compare specification identity and every observed parameter before reusing measured validation. Missing evidence remains UNKNOWN; mismatched evidence is FAIL. A spec-only preview is never CAD PASS.

Acceptance: deterministic CSV/JSON parity, role/thickness checks, invalid inputs, stale/missing/failed evidence, comparisons with accepted raw G3/G4 measurements, existing regression suites, installed-wheel origin, two reproducible wheel/bundle builds and Python 3.10/3.12 CI.

No Fusion operations, installation/configuration changes, CAD attributes, persistent migrations or new dependencies. Existing validation/recovery and golden fixtures remain unchanged. The G4 fixture stays open with unsaved changes. Rollback is removal of newly generated offline outputs or reverting this feature commit; no model recovery mechanism is needed because this increment cannot mutate CAD. No structural persistence, manufacturing qualification, merge, release or V6 is implied.

## Supported candidate scope

Only one cabinet per document. This matrix intentionally omits other accepted scalar combinations: profile ranges and buildable inputs are not qualification. The preview can calculate other valid specifications, but without matching accepted evidence they remain unverified. All historical file links below are pinned to integrated commit `2da3feb8dd359fe3c0d0e50d6f8fb3568176bb74`; their original failures and publication manifests remain unchanged.

| Configuration / transformation | Accepted evidence and limit |
| --- | --- |
| Base@1, 1200×850×550 mm, ply18/back6, one shelf/two doors | [G4 raw fixture and reports](https://github.com/AnyBuzzin/van-design-system/tree/2da3feb8dd359fe3c0d0e50d6f8fb3568176bb74/docs/integration/g4-shelf-count/live-20261017), 59/59 geometry, 2/2 cuts; [independent acceptance](https://github.com/AnyBuzzin/van-design-system/pull/22#pullrequestreview-5560245734) |
| Same base, guarded structural 1→2→1 shelves | Same raw evidence: 85/85 and 4/4 at two shelves; restored 59/59 and 2/2, original inventory and108 obsolete-groove probes. Fresh receipt-bearing default fixtures only, existing Runner preview/update workflow. No arbitrary reconciliation or crash recovery. Structural save/reopen UNKNOWN, excluded. G4 is not permanently installed. |
| Tall@1, 600×1900×550 mm, ply18/back6, three shelves/one door | [Original F2 archive](https://github.com/AnyBuzzin/van-design-system/blob/2da3feb8dd359fe3c0d0e50d6f8fb3568176bb74/docs/integration/evidence/G3-F2-F3-partial-evidence.zip), baseline112/112; [independent acceptance](https://github.com/AnyBuzzin/van-design-system/issues/4#issuecomment-6227536777). Preview comparison uses archived measured bbox-deviation checks, not newly measured CAD. No tall structural edits. |
| Overhead@1, 1000×400×350 mm, ply18/back6, one shelf/two doors | [Original G3 records](https://github.com/AnyBuzzin/van-design-system/tree/2da3feb8dd359fe3c0d0e50d6f8fb3568176bb74/docs/integration/g3-remaining-verification), baseline62/62 and2/2 cuts; same G3 acceptance. |
| Overhead raw scalar depth350→400→350 and height400→450→400 | Same G3 batch reports62/62 each;800 mm produces expected validation FAIL after raw edit, not pre-mutation refusal. These are raw scalar edits, not G4 guarded commands. Stored spec can remain baseline: preview flags divergence and does not claim nominal baseline blanks describe the edited model. |
| Overhead baseline persistence | [Final guarded lifecycle evidence](https://github.com/AnyBuzzin/van-design-system/tree/2da3feb8dd359fe3c0d0e50d6f8fb3568176bb74/docs/integration/g3-remaining-verification/final-guarded-persistence). Sole exact clean, saved, cloud-complete fixture only, version2. Earlier tab-loss FAIL and dirty-state refusal remain; no general multi-document safety claim. |

Unchanged G3 compatibility and prior width subfeature remain covered by their existing regression/evidence; they are not expanded into new G5 support ranges. G0 executed V4 provenance remains OPEN. Interiors, vehicle models, arbitrary shelf counts, custom/mixed stock, grain, tool allowances, nesting, toolpaths and manufacturing/structural/vehicle-fit certification are excluded.

## Preview usage and evidence semantics

In a clean environment containing the candidate wheel:

```text
python -m vandesign.panel_preview cabinet_spec.json NEW_OUTPUT --report existing_measure_report.json
```

Omit `--report` for nominal-only output, explicitly UNKNOWN. JSON dimensions and CSV dimensions use identical six-decimal mm strings, quantity1, stable-ID sort and role-specific XYZ axes. Thickness is nominal panel geometry, not measured stock. Back thickness follows `Cab_Back`; other panels follow the existing boxes. Grooves are separate references to existing operations and never reduce blank size. No timestamp is generated in deterministic output. CSV carries the engineering warning in every row; provenance is in the JSON companion.

The JSON keeps the canonical stored specification/hash scheme, resolved nominal values, actual reported expressions/values, report SHA256, Fusion version, document name and counts where available. Scalar divergence, different panel sets, failed validation or incompatible spec identities prevent historical consistency PASS. Missing data stays UNKNOWN. A historical consistency PASS is neither new CAD verification nor proof that a currently open document still matches. Unknown saved identity/version/dirty and cut ownership are not inferred from report geometry.

`tools/check_panel_preview_evidence.py` generates four examples and `TRACEABILITY.json` from accepted artifacts without contacting Fusion. The sidecar links reviewed source/wheel identity, verified installed-source hashes, original report hashes, acceptance links and preview hashes. For G4 it also preserves the exact recorded redacted cloud identity/version/dirty state, ownership audit and measured bounds comparison. Historical producer package identities are separate from the new preview package identity. G3 reports lacking saved-state fields stay UNKNOWN in those examples; their separate accepted lifecycle evidence is linked above.

## Packaging and installation boundary

Use the existing `pip wheel --no-deps`, fresh virtual environment, `tools/check_installed.py` and `tools/deploy_fusion.py NEW_DIRECTORY`. Set a fixed `SOURCE_DATE_EPOCH` for two wheel builds, compare wheel SHA256 and every generated deployment manifest/file hash. No dependency or schema/generator version change. CI runs installed-wheel checks and regressions on Python3.10/3.12. Historical G4 CAD observations used Fusion2705.1.30/Python3.14; G5 itself is offline and is not a live Fusion qualification.

Generating bundles is not installing them. Any future live installation needs separate owner authorization: record exact current installation/configuration/file set, backup original bytes and active paths, use the established native stop/start procedure, and verify loaded source hashes. Roll back exact original files/configuration and verify the restored file set and active source; retain all journals/evidence. No such operation is authorized or performed here.
