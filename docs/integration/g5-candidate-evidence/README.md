# G5 candidate verification — independent acceptance pending

Source/package commit `1c0aa68` (full identity in [source proof](source-proof.json)); built offline on Windows/Python3.12.14. No Fusion connection, document operation, Runner installation or configuration change. G4 fixture and unsaved changes remain untouched.

| Check | Result / evidence |
| --- | --- |
| Installed wheel and unchanged legacy identity | PASS — [isolated import check](installed.txt), [31 source files compared to commit and wheel](source-proof.json) |
| Focused and existing regressions | PASS — [30 root tests](root-tests.txt), [119 historical regression tests against installed runtime](prototype-tests.txt), [79 Runner tests](runner-tests.txt):228 total. Includes8 new preview tests; original goldens unchanged. |
| Compile | PASS — [empty successful output](compile.txt) |
| Reproducible wheels / bundles | PASS — [record](reproducibility.json). Two wheel SHA256 values `4f1845d076d0c9f70c4240d6d954a1685894b85664ee53efb4644df923c43313`; fixed SOURCE_DATE_EPOCH1792195200, setuptools84.0.0, no runtime dependencies. Both generated bundle manifests and every covered file matched. This proves repeatability in the recorded environment, not cross-platform/cross-builder wheel equality. |
| Accepted measurements reused | PASS — [traceability sidecar](TRACEABILITY.json): default tall/overhead reports, base two-shelf and restored one-shelf reports. G4 blank dimensions/thickness independently compared with recorded actual BRep bounds at0.01mm; exact groove target maps compared. No CAD tests repeated. |
| Stale/missing evidence handling | PASS — tests cover changed parameter with matching stored hash, wrong identity, failed/unknown/omitted/duplicate checks, orphan panel and missing measurements. Nominal-only output is UNKNOWN. Original overhead scalar edit produces expected evidence-consistency FAIL, not a claim that the accepted edited CAD was defective. |
| Python3.10/3.12 CI | Pending PR workflow; CI result will be linked on the PR. |
| G5 live Fusion / structural persistence | NOT RUN / UNKNOWN and excluded. Historical G4 observations used Fusion2705.1.30/Python3.14. No new live qualification or permanent deployment. |

Examples: [base one shelf CSV](base-to-one.csv) / [JSON](base-to-one.json), [two shelves CSV](base-to-two.csv) / [JSON](base-to-two.json), [overhead CSV](overhead-default.csv) / [JSON](overhead-default.json), [tall CSV](tall-default.csv) / [JSON](tall-default.json). All are **ENGINEERING PREVIEW, NOT CERTIFIED CNC OUTPUT**. G3 saved-state/ownership fields absent from individual geometry reports remain UNKNOWN there; separately accepted evidence is linked in the [scope contract](../G5_ENGINEERING_CANDIDATE.md).

[MANIFEST.json](MANIFEST.json) hashes the published output bytes. Original accepted reports remain at their pinned historical paths, linked and hashed by TRACEABILITY.json. No private configuration or cloud IDs were newly read or published; existing redacted fixture IDs remain redacted. Local test logs contain only developer environment paths and test outcomes.

During development, one new negative-case assertion initially expected UNKNOWN after changing a check status but retaining stale PASS counts. The stricter count consistency check correctly returned FAIL; the test now explicitly requires FAIL for inconsistent totals, with a separate missing-check test requiring UNKNOWN even when totals are internally consistent. No historical tests, failures or goldens were changed.

Jack: independently review the bounded support matrix, preview semantics, traceability limits and CI. Owner acceptance and any merge/release remain separate decisions; Issue24 stays open. No additional owner approval is needed for this completed offline work.
