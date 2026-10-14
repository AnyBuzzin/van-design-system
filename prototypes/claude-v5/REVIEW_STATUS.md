# Claude V5 source import review

> **LATEST UPDATE — 2026-10-14, after real-Fusion tests:** G2 fixture verification COMPLETE: A–E passed 58/58 checks each in Fusion v2705.1.30; a direct read-only cut audit verified exact one-body ownership for each left/right dado operation. [Evidence](FUSION_TEST_PROTOCOL.md), [cut audit](docs/test-results/cut_audit_20261014_174320_047406.txt). Issue #2 closed. G3 three variants is now open as issue #4, on `feature/v5-g3-cabinet-variants`. The lines below are **historical pre-Fusion notes**, not the current status. G0 source provenance and `src/vandesign` integration are still unresolved. PR #3 remains draft.\n\n**2026-10-14** — Full 35-file source imported from the uploaded `vandesign_v5.zip` on `feature/v5-fusion-adapter`.

- Offline Python tests: **30/30 passed** in the analysis environment using `python -m unittest discover -s tests -v` from this prototype folder.
- Baseline `sha256sum -c SHA256SUMS.txt`: **2/2 matched**, when run within `baseline/`.
- Fusion adapter: **NOT YET RUN IN FUSION**.
- V4 archive within this prototype: hash-verified relative to the supplied archive, not independently proven identical to the original Fusion-tested file.
- `participantBodies` is explicitly assigned in V5 cut operations; still requires a real Fusion cut-target smoke test.
- The V5 prototype has a bundled standalone `vandesign` package. This is experimental and **not integrated** into the foundation package at `src/vandesign` yet. Avoid duplicate module drift: reconcile only after testing.
- Before merge, run the real Fusion fixture tests A-D and the save/reopen check, resolve all FAIL/UNKNOWN results and document the exact tested revision.

Issue: https://github.com/AnyBuzzin/van-design-system/issues/2


## Upstream pre-Fusion patch reconciliation — 2026-10-14

The user supplied Claude's original `v5-pre-fusion-corrections.patch` and `FUSION_TEST_PROTOCOL.md` after earlier reporting improvements had already been committed. The patch's hunks **cannot be applied verbatim** to the modified `runner.py`; the changes were compared and reconciled manually, without altering the CAD geometry.

- Live `Cab_*` parameter values, Fusion version and document name are captured in JSON and the readable text report.
- JSON contains both `parameters_read_from_fusion` (values plus expressions) and a simpler `parameters_mm` mapping compatible with Claude's patch.
- A missing stored specification on a managed assembly tells the user to discard a possible partial build.
- Failed build operations show a direct dialog with traceback; the user must close the unsaved partial design.
- Filename includes `_build` or `_measure`; both `.json` and `.txt` are written.
- The supplied Fusion test protocol's A–E fixture values are preserved in `FUSION_TEST_PROTOCOL.md` (expanded to reflect the repo and new reporting structure).
- A mocked-adsk report serialization test was added: **31/31 tests passed locally** in Python 3.13 after reconciliation. This is not a Fusion runtime result.
- Feature-branch GitHub Actions now executes the V5 prototype suite in addition to the main foundation tests. GitHub CI outcome should be checked separately.

**Fusion 360 verification: UNKNOWN.** No V5 build, parameter-edit or save/reopen test has been performed or reported inside Fusion. Do not merge until issue #2 and Draft PR #3 acceptance criteria pass.
