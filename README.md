> Current consolidation status (2026-10-15): see [integration review](docs/integration/CONSOLIDATION_2026-10-15.md). G3 has partial Fusion evidence; G4 width-only is evidenced; package reconciliation/G0 remain open. Nothing has merged to develop.

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
- The V5 Fusion adapter **was user-tested in real Fusion 360** (v2705.1.30): smoke tests A–E all passed 58/58, with separate API verification of exact left/right cut participants. This is a verified limited fixture, **not** manufacturing qualification or a guarantee for other configurations. See [test evidence](prototypes/claude-v5/FUSION_TEST_PROTOCOL.md).
- Never equate passing arithmetic/unit tests with physical fitment or CNC readiness.

## Run foundation tests
```bash
python -m unittest discover -s tests -v
```

## Branch policy
`main`: stable project structure and independently exercised Python utilities.
`develop`: integration preparation.
`feature/v5-fusion-adapter`: G2 real-Fusion smoke-test and audit passed; **draft PR #3 remains unmerged pending integration review**.
`feature/v5-g3-cabinet-variants`: successor G3 branch for three variants, [Claude handover](docs/ai/CLAUDE_V5_G3_HANDOVER_2026-10-14.md).

Private project. No redistribution licence granted.
