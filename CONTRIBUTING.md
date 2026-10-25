# Development process

1. Branch from develop for features and fixes. Do not commit experimental Fusion code directly to main.
2. Keep one issue per bug/feature with expected geometry, reproduction steps, dimensions and test evidence.
3. Record tests actually run in PR descriptions. Use UNKNOWN when Fusion is unavailable.
4. Run `python -m unittest discover -s tests -v` before pushing.
5. Preserve a stable ID and parametric dependency for every geometric component.
6. Include unit/fixture tests and a repeatable Fusion check for changes in CAD code.
7. Use PR reviews for changes; merge into main only after agreed acceptance gates.
8. Do not commit customer data, private vehicle scans, secrets, CNC toolpaths or commercial assets.

## Release policy
Version labels distinguish experimental, Fusion-verified, and manufacturing-approved. No version is automatically manufacturing-approved by passing software tests.
