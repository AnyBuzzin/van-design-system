# PR14 real-Fusion compatibility checkpoint — PASS

Executed in Autodesk Fusion 2705.1.30 on 2026-10-15 in the user's dedicated unsaved Untitled cabinet. Independently reviewed checkpoint_20261015_224352_099918.json and all three referenced raw JSON/text measurement reports. Earlier BLOCKED/UNKNOWN notes in STATUS.md are chronological records superseded by this result.

| Check | Actual result |
| --- | --- |
| Baseline BRep validation | PASS: 59 PASS, 0 FAIL, 0 UNKNOWN |
| Width edit BRep validation | PASS: 1200 → 1210 mm; 59 PASS, 0 FAIL, 0 UNKNOWN |
| Restored BRep validation | PASS: exact expression `1200 mm`; 59 PASS, 0 FAIL, 0 UNKNOWN |
| Cut participants | PASS at all three stages: left dado targets only panel.left.001; right only panel.right.001; each is a Cut with exactly one correct participant |
| Dado geometry | PASS: 5.7 mm shelf penetration, 0.3 mm end gap, 0.25 mm clearance above/below; groove/material probes and unmodified mating shelf volumes pass |
| Restoration | PASS: all eight body bounds and volumes equal baseline; maximum recorded corner delta 0 mm and volume delta 0 mm3 |
| Package identity | VERIFIED: 24 loaded VanDesign modules before/after originate in reviewed generated bundle; source SHA-256 values match |
| Deployment integrity | PASS: 31 manifest files verified; fixed manifest SHA-256 9dca986105401b2b3c506b151d5d21684057a8f8cc2eece85752705ce66bcb2a |
| Document safety | Test document unsaved before/after; stored spec unchanged; cut audits restore timeline and preserve counts |

Measured shelf length: 1175.4 → 1185.4 → 1175.4 mm. Measured shelf volume: 11509516.8 → 11607436.8 → 11509516.8 mm3. These changes demonstrate actual BRep response, not only changed parameter arithmetic. The checkpoint script source hash was independently checked against the executed script hash. Independent review results are in independent-review.json; original full evidence and reports are preserved unchanged.

No runner installation/configuration changes, save/close operations or merges were performed. Only the dedicated test cabinet's width and temporarily its audit history marker were changed and restored. The authoritative src/vandesign and historical source remain unchanged.

## Integration recommendation for Jill

The targeted cabinet deployment checkpoint is complete. PR13 head 9a949471 remains the exact ancestor/base of PR14 head 800b34e. Available GitHub Python 3.10/3.12 checks passed on both heads (github-integration-checks.json). Both remain draft and unmerged. No technical blocker was found in this targeted checkpoint; review approval and final required CI/branch-rule checks remain prerequisites to integration.

Use one aggregate route: after Jill's approval, integrate PR13 into develop with ancestry preserved; retarget PR14 to develop; inspect the resulting package-only diff and rerun required CI before integrating PR14. Do not also integrate the original sequential stack. Evidence/test work is separately pushed on feature/pr14-compatibility-checkpoint, so Jill must decide which evidence/test commits to retain; it is not silently included in PR14's unchanged head. No merge is authorized by this report.

Scope: base@1 cabinet deployment, one scalar width edit/restore, explicit two-cut participant audit. This does not qualify every variant, interior demo, runner deployment or full G3/G4 campaign. Historical G0/deferred G3/G4 and G5 acceptance remain open, and no manufacturing approval is implied.
