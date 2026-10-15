# VanDesign — AI-assisted parametric van engineering

**Current state (2026-10-15): V5 engineering development integrated into `develop`; NOT manufacturing-ready.** [Complete project status](PROJECT_STATUS.md) · [Current roadmap](docs/ROADMAP.md).

VanDesign aims to turn typed van/customer requirements into editable Autodesk Fusion 360 assemblies, with deterministic geometry, measured CAD validation and, at later approved stages, traceable manufacturing information. **AI proposes intent; the engineering core constructs and validates; humans approve fabrication.**

## Start here

- [Current status, completed work and exact gaps](PROJECT_STATUS.md)
- [Authoritative V5 gates G0–G5 and later V6–V10 roadmap](docs/ROADMAP.md)
- [Rules for AI development and milestone scope](AGENTS.md)
- [Geometry precision and cut ownership](docs/standards/precision-and-ownership.md)
- [Contributor guidance](CONTRIBUTING.md)
- [Preserved original V4 provenance](legacy/v4-verified/README.md)
- [Single-runtime migration details](docs/integration/ONE_PACKAGE_MIGRATION.md)
- [Real-Fusion deployed-package checkpoint](docs/integration/pr14-checkpoint-evidence/live-20261015/FINAL_REVIEW.md)

## Architecture and source of truth

```text
typed millimetre specifications
       |
src/vandesign — CAD-neutral expressions, panels and geometry
       |
furniture and simplified vehicle-layout modules
       |
Fusion adapter and generated, hash-verified script bundles
       |
read-only BRep verification + exact boolean cut participants
       |
reviewed, scoped engineering evidence
```

**`src/vandesign` is the sole maintained Python runtime.** The former `prototypes/claude-v5` package is retained as historical source and test evidence, **not** a second runtime. The installed wheel provides legacy `DadoShelf` and the V5 component/model/Fusion-adapter interfaces. No code outside the CAD adapter may depend on `adsk`.

The original V4 final executed source identity is still under investigation; the V5 G2 base fixture and the deployed PR14 `base@1` checkpoint have documented real-Fusion geometry and exclusive cut-ownership PASS results. This does **not** prove arbitrary variants, measured vehicle fit, production structures or CNC safety.

## Development and testing

- Use `develop` as the starting baseline and create **one focused feature branch/PR per milestone**. `main` is reserved for separately authorised stable/release changes.
- Offline tests use the installed Python package and GitHub Actions on Python 3.10 and 3.12. The development-only integration of [PR #14](https://github.com/AnyBuzzin/van-design-system/pull/14) (including the PR #13 stack) passed post-merge CI.
- For changed CAD behaviour, collect focused real-Fusion BRep/owned-cut/edit-restore or persistence evidence; don't restart unrelated historical regression campaigns.
- Existing live Fusion runner installations may still point to historical package folders; **do not silently replace them**. Migrate through a separate approved backup/rollback procedure.
- Treat any actual product release, manufacturing/CAM/CNC operation and physical van installation as **unqualified** until formal future acceptance.

VanDesign source is not offered under a redistribution licence.
