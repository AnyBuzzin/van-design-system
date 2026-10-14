# VanDesign — AI-powered van engineering

**Status:** V5 architecture + CAD-neutral framework foundation. **Not manufacturing-ready.**

VanDesign aims to turn configurable vehicle and customer requirements into editable Fusion 360 assemblies and validated manufacturing data.

AI proposes design specifications; deterministic engineering rules calculate geometry; validation measures the resulting solids; a human approves fabrication.

## Start here
- [Current status](PROJECT_STATUS.md)
- [Roadmap](docs/ROADMAP.md)
- [Engineering constraints](docs/standards/precision-and-ownership.md)
- [AI assistant rules](AGENTS.md)
- [Contributing](CONTRIBUTING.md)
- [V4 baseline provenance](legacy/v4-verified/README.md)

## Architecture
```
core + component model (no adsk imports)
         |
furniture/vehicle design modules
         |
CAD adapter: Autodesk Fusion 360
         |
independent solid-body validation
         |
reviewed manufacturing outputs
```

The CAD-specific adapter must explicitly specify cut participants; never allow a dado cut to modify a neighbouring shelf. Every component gets a stable identifier.

## Source-status policy
- V4 shelf fit has been verified by the user in Fusion. Archive the **exact** verified file before labelling any source release verified.
- Claude's V5 implementation passed 30 CAD-independent Python tests, but its Fusion adapter has **not** been run in Fusion.
- Never equate passing arithmetic/unit tests with physical fitment or CNC readiness.

## Run foundation tests
```bash
python -m unittest discover -s tests -v
```

## Branch policy
`main`: stable project structure and independently exercised Python utilities.
`develop`: integration preparation.
`feature/v5-fusion-adapter`: V5 Fusion prototype; do not merge without a smoke test.

Private project. No redistribution licence granted.
