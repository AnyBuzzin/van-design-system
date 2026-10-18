# V6.2 bounded offline layout contract

Approved [Issue31 contract and Jill clarifications](https://github.com/AnyBuzzin/van-design-system/issues/31#issuecomment-6244308296). Base revision: `7de3349242cfe59b7af533b82abdb79d28ae2c4d`.

One new CAD-neutral `vandesign.layout_preview.make_layout(placements)` function returns a versioned JSON-compatible snapshot for exactly the default accepted bed and default base@1 cabinet. Input: two records with fixed unique `instance_id` (`bed.001`, `cabinet.001`) and `translation_mm` (XYZ numeric triple). No caller-supplied furniture specifications, rotations or generic assembly composition.

Reuse existing builders, shared preflight, resolved Box geometry and standalone previews. Preserve canonical specifications, their named hash schemes, parameters, local IDs and cut ownership. Composite identities are instance/local-ID pairs. Translate resolved boxes only; never mutate expressions, generators or standalone previews. Export deterministic JSON using existing `panel_preview.canonical_json`.

Acceptance: separated modules PASS; conservative whole-envelope intersection REFUSED (including empty bed underside); malformed/duplicate/missing instance records and nonnumeric, boolean, nonfinite or numerically invalid derived geometry REFUSED. Contact within existing Box intersection epsilon1e-9mm is nominal non-overlap only. Test independent XYZ translations, contact boundaries, determinism, composite identity and byte-identical standalone previews/specifications. Keep 6mm cabinet back distinct from18mm main/bed panels.

Only nominal arithmetic may PASS. Shared live Fusion geometry, usable access, door motion, fastening, vehicle fit, loads and manufacturing remain UNKNOWN/unqualified. The snapshot is not a compile-ready Fusion assembly. No adapter/Runner changes, Fusion calls, persistence, material/furniture expansion, experimental-demo edits, UI or infrastructure. No protected resources are touched; rollback is abandoning the offline branch, not a CAD operation. One draft PR; independent review and owner approval required before merge.

## Implemented interface and evidence

```python
from vandesign.layout_preview import make_layout
from vandesign.panel_preview import canonical_json

snapshot = make_layout([
    {"instance_id": "bed.001", "translation_mm": [0, 0, 0]},
    {"instance_id": "cabinet.001", "translation_mm": [1500, 0, 0]},
])
text = canonical_json(snapshot)
```

Input list/key order does not affect output. Numeric inputs normalize to floats (including negative zero). Any refused input raises `ValueError` without a partial snapshot or side effects. A translation that loses resolved dimensions by more than1e-9mm at floating-point precision is refused, even if its input coordinates are finite. No floor or vehicle boundary is inferred; negative placements are allowed. Existing Box epsilon is a geometric comparison convention, not usable access clearance.

`instances` remains separate: unchanged canonical specs and named hashes, assembly hashes, parameter values/derived expressions, local/world panel boxes, operation target/mating identities and local/world cut boxes. Each includes its unchanged specification-only standalone preview. This preserves nominal dimensions/quantities and CSV/JSON parity without duplicating panel formulas. Whole envelopes intentionally overestimate occupied space, including voids and gaps. The experimental interior is unchanged.

| Evidence | Result |
| --- | --- |
| [Installed-wheel core tests](v6-2-offline-evidence/core-tests.txt), including9 focused layout tests | PASS47/47 |
| [Historical prototype regression](v6-2-offline-evidence/prototype-tests.txt) | PASS119/119 |
| [Offline Runner regression](v6-2-offline-evidence/runner-offline-tests.txt), no Runner connection | PASS79/79 |
| [Wheel/source/spec/preview preservation](v6-2-offline-evidence/verification.json) | PASS;33 existing runtime Python files unchanged after line-ending normalization; standalone spec/CSV/JSON bytes identical to accepted wheel |
| [Separated example](v6-2-offline-evidence/separated-layout.json) | PASS nominal envelope arithmetic;11 composite panel identities |
| Overlap/bed-void, invalid input, derived invalid geometry and contact-boundary tests | Expected refusal/PASS assertions verified; no live model |
| Python3.10/3.12 CI | See draft PR checks; local evidence records pre-CI state |
| Live multi-module Fusion, access/door clearance, physical suitability | UNKNOWN/NOT RUN |

[Evidence hashes](v6-2-offline-evidence/MANIFEST.json) preserve raw offline logs. Initial build without isolation failed because the test-only environment lacked the build backend; the standard isolated wheel build succeeded and was installed only into a fresh offline test environment. No production deployment or installation changed. No Fusion calls, protected-design actions or additional V6.1 tests occurred. Earlier tab/capacity history, G0 and public-ID history remain unresolved. Independent review and owner integration approval are pending.
