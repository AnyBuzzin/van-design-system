PR #13's installed package could not import the V5 cabinet modules. This child change makes src/vandesign the sole maintained/distributable runtime, retaining the prototype as unchanged historical source.

- Copy all 27 V5 Python files unchanged; preserve schema/generator constants, formulas, parameter names, IDs and adapter behaviour.
- Preserve DadoShelf's frozen public API/validation and five existing tests, delegating derived values to canonical V5 expressions.
- Derive wheel metadata version from the existing 0.5.0 runtime; do not change generator or schema identity.
- Generate new Fusion bundles from the installed wheel, with per-file SHA-256 manifests and refusal to overwrite. Preserve cabinet launcher; update interior launcher to use canonical source or its generated bundle.
- Run regression suites against the installed wheel, removing prototype runtime path injection. CI builds a wheel and tests a clean environment on 3.10/3.12.

Local clean-wheel verification: 8 compatibility/deployment + 119 V5 + 69 runner tests PASS (196 total), isolated site-packages imports and compilation PASS. Every migrated V5 file matches the retained source. Both generated launchers and existing runner loaders tested offline with mocked adsk; no-design refusal and stale-module reload pass.

**Live Fusion deployment smoke NOT RUN.** Existing installations, runner config/queue and protected designs are untouched. A targeted new disposable-design BRep/cut/edit-restore smoke remains required before deployment acceptance. G0 provenance, deferred G3 F0/F3, broader G4 and G5 qualifications stay open.

See [migration/deployment review](docs/integration/ONE_PACKAGE_MIGRATION.md) and [raw evidence](docs/integration/package-migration-evidence). Child of the integration-preparation branch; draft for Jill's review, no merges or delivery-route changes requested.
