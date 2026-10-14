# Explicitly NOT implemented (per the V5 brief)

> **Current status 2026-10-14:** This list describes functionality not yet implemented. The section below called “Known risks to check on the first Fusion run” was written **before** the actual G2 smoke tests. Fusion version 2705.1.30 ran all A–E fixture scenarios (58/58 checks passed per run), including real `pointContainment` probes and component attributes; the separate cut audit also passed. Those historical API compatibility concerns are resolved **for the tested configuration only**. New G3 variants have **not** yet been run in Fusion.\n\n- AI generation / schema-constrained AI intake
- Vehicle envelopes, datums, module placement, rotations (identity placement only)
- Nesting, CAM, G-code, DXF/CSV export, cut-list output
- Change engine: structural edits (shelf/door count) require a fresh build; no diffing of manual Fusion edits (G4)
- Measured vs nominal plywood thickness, tolerance classes, material records beyond `material_ref`
- Three cabinet variants from one core (G3): implemented as data-only profiles and offline-tested, but NOT yet run in Fusion (see FUSION_TEST_PROTOCOL_G3.md). Fixture sizes are not engineering limits; no plinth, hanging rail, hinges or rabbet.
- Save/reopen automation and a Fusion-hosted automated test run (manual smoke test in README)

# Known risks to check on the first Fusion run
- `Component.attributes` / `Attributes.add` and `BRepBody.pointContainment` are used per Autodesk's published docs (`PointContainment` lives in `adsk.fusion`) but have not run in Fusion here. Failures surface as UNKNOWN/diagnostics or an error dialog, not as PASS.
- Point probes use a 0.1 mm offset; if Fusion reports boundary results the probes become UNKNOWN rather than FAIL.
- The 0.01 mm check is a software-consistency epsilon, not a shop tolerance.
