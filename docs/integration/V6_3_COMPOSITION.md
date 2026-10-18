# V6.3 offline symbolic composition contract

Approved [Jill contract/owner approval](https://github.com/AnyBuzzin/van-design-system/issues/34#issuecomment-6244552003). Baseline: `cbec6fe98421d143e0acfa0b2a704eeea4691c20`, after PR33 integration.

One explicit `compose_layout(snapshot)` converts only a fully revalidated V6.2 fixed bed.001/default cabinet.001 snapshot to an immutable result containing a symbolic `AssemblyDefinition` and read-only canonical manifest JSON. Recompute `make_layout` from placements and reject any disagreement in the input snapshot (specifications, hashes, inventory, parameters, ownership, bounds or qualification). No permissive migration, arbitrary module injection or editable manifest.

Reuse accepted builders, ordered ParameterSet and preflight. Prefix composed panel/operation/constraint IDs with instance IDs; preserve local identity mapping. Translate panel/cut origins with `Mm` expressions; retain sizes, parameter names/formulas and both dado references. Require11panels/2cabinet dados, unique ordered parameters/IDs and exact local ownership. Cross-check symbolic resolved world bounds against V6.2. Hash a distinct versioned composition manifest, never reinterpret a standalone spec hash.

Focused offline acceptance: translated bounds/formulas/volumes and targets, deterministic metadata, unchanged sources/previews, collisions/contact policy, invalid/ambiguous snapshots, duplicate parameters/IDs, nonfinite or precision-loss placements and remapping errors. No adapter, schema, persistence, Runner or experimental-demo changes. No Fusion calls, live helper, new fixtures or deployment. Stop if those are necessary. Existing empty-root safeguards remain. The composition is only an offline candidate, not qualified live CAD; never pass its manifest to the cabinet-oriented `store_spec_json` as a cabinet spec.

One focused draft PR, independent Jack review and owner merge approval. Preserve all existing fixtures and UNKNOWN tab/capacity history, G0 and public-ID history. No load/fit/access/manufacturing or persistence claim. Rollback is abandoning this offline change; no CAD rollback exists or is authorized.

## Interface and implementation

```python
from vandesign.layout_preview import make_layout
from vandesign.composition import compose_layout

layout = make_layout([
    {"instance_id": "bed.001", "translation_mm": [0, 0, 0]},
    {"instance_id": "cabinet.001", "translation_mm": [1500, 0, 0]},
])
candidate = compose_layout(layout)  # No CAD or filesystem operation.
assembly = candidate.assembly
provenance_json = candidate.manifest_json
```

The frozen result contains the existing frozen AssemblyDefinition and an immutable manifest string. The caller must supply the complete canonical V6.2 snapshot, not a hand-edited partial plan; regenerate it with `make_layout` after changing placements. Revalidation compares canonical serialized snapshots, including source specifications/hashes, parameters, local/world boxes, previews and qualification. Composition subsequently checks freshly rebuilt sources, exact inventories and local ownership, translated bounds/volumes, ordered combined parameters and shared preflight before returning a candidate. Errors produce no result or side effects.

Panel IDs use `instance.local_id`, e.g. `bed.001.bed.deck.001`. Operations and constraints use the same explicit lineage; both dado references map to `cabinet.001` panels. Origins are source expressions plus `Mm(translation)`; sizes, clearances, source constraint expressions and parameter definitions are preserved. Source parameter dependency order remains bed then cabinet. No formulas are replaced by resolved constants. Expected world bounds come from V6.2, cross-checked within1e-9mm and volume relative1e-12/absolute1e-6mm³. Face contact uses the unchanged V6.2 epsilon, not assembly/access clearance.

`assembly.spec_hash` is SHA-256 of the versioned canonical manifest UTF-8 bytes, distinct from both source spec hashes. Manifest records canonical source specs/named hash schemes, placements, parameter values/expressions, source-to-composed panel/cut/constraint mapping, expected world bounds, symbolic origin/size expressions and the validated layout hash. It is separate offline evidence. Cabinet-oriented adapter generator labels and singular stored-spec attributes remain unchanged and are not per-instance provenance. This increment does not authorize invoking the adapter or persisting that manifest in Fusion.

## Evidence and limits

| Check | Actual result |
| --- | --- |
| [Installed-wheel core tests](v6-3-offline-evidence/core-tests.txt), including7 new composition tests | PASS54/54 |
| [Prototype regression](v6-3-offline-evidence/prototype-tests.txt) | PASS119/119 |
| [Offline Runner tests](v6-3-offline-evidence/runner-offline-tests.txt), no Runner connection | PASS79/79 |
| [Source/wheel/output preservation](v6-3-offline-evidence/verification.json) | PASS;34 prior runtime modules unchanged after CRLF normalization; V6.2 snapshot and standalone spec/CSV/JSON bytes unchanged |
| [Deterministic composition manifest](v6-3-offline-evidence/composition-manifest.json) |11panels/2cabinet dados, distinct composition hash, shared offline preflight PASS |
| Tampered spec/hash/inventory, duplicate IDs/params/constraints, dependency order, cross-instance remap, invalid/colliding/precision-loss placements | Expected refusal assertions PASS |
| Python3.10/3.12 CI | See draft PR checks; local verification records pre-CI state |
| Combined Fusion BRep/boolean cuts, native metadata/persistence, physical fitness | UNKNOWN/NOT RUN |

[Manifest](v6-3-offline-evidence/MANIFEST.json) pins raw logs and example. No prior failure evidence was changed, no cabinet/G4 live campaign repeated, and no Fusion/Runner installation/configuration or protected fixture touched. Offline expressions remain editable mathematically, but later parameter edits can invalidate layout clearances; no ongoing layout reconciliation or edit qualification is claimed. Future live testing requires its own reviewed route and owner approval. Independent review and owner merge approval remain pending.
