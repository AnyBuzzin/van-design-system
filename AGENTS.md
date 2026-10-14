# Rules for AI coding assistants

Read README.md, PROJECT_STATUS.md and docs/standards/precision-and-ownership.md before modifying code.

- Preserve the exact proven V4 version; do not overwrite an archive.
- Keep CAD-neutral math in core; isolate all `adsk` imports to the Fusion adapter.
- All design units must be explicit; canonical units are millimetres.
- Require body ownership on every boolean cut. Fail closed when a target cannot be resolved.
- Do not mutate existing Fusion designs unless explicitly requested by the design workflow.
- Give components stable IDs independent of display labels.
- Treat validation failures and unavailable evidence as FAIL or UNKNOWN, never PASS.
- Test parameter edits plus actual BRep geometry; arithmetic tests are insufficient.
- Maintain backwards-compatible parameter names or document migrations.
- Do not claim tests were run without logs/evidence.
- No CAM, structural, electrical, road-legal or CNC approval without relevant engineering checks.
- Use a feature branch, tests and review for modifications to the core or adapter.
