# Claude V5 prototype — pending import and Fusion verification

The user uploaded `vandesign_v5.zip` to ChatGPT. Its 30 CAD-independent tests were executed successfully in the working environment on 2026-10-14.

**The implementation files from that archive have not yet been committed to this branch.** The original ZIP remains available in the conversation, not in GitHub. Do not claim otherwise or mark the adapter as verified.

Expected archive contents:
- `VanCabinetJoineryV5/` with the Fusion script, manifest, and internal `vandesign/` modules
- `baseline/` with V4 rev2, manifest and SHA256 hashes
- `tests/` with core, simulation and validation tests
- `README.md`, `NOT_IMPLEMENTED.md`

## Before merge

1. Commit the actual audited Python files from the uploaded ZIP.
2. Keep the archive’s baseline separate from a confirmed user-verified V4 release until source identity is established.
3. Run the 30 independent tests in CI.
4. Run the Fusion smoke test on an empty design, change dado depth to 10 mm and check actual shelf engagement.
5. Save, reopen, and retest; resolve every FAIL or UNKNOWN.
6. Open a PR against `develop`, then promote to `main` only after acceptance.

No geometry from this branch is approved for CNC production.
