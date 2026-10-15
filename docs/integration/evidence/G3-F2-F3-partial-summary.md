# VanDesign G3 - F2 tall / F3 overhead partial Fusion evidence

Source commit `4d4345b6cde6084b1731c5298fa50d70759ef061`. Generator installed at
`Documents/VanDesign-G3/4d4345b/VanCabinetJoineryV5`, audit at `Documents/VanDesign-G3/4d4345b/VanDesignCutAuditG3`.
Fusion 2705.1.30. Testing was **stopped by the project owner** part-way through F3.
This is NOT full G3 verification and NOT manufacturing approval. Issue #4 stays open; PR #5 stays draft.

Every report was checked by `verify_g3.py` / `verify_audit.py` (included): each live `Cab_*` value recomputed
independently, named-check counts and statuses, managed entities, design counts vs the build report,
design-spec hash, and stored spec before == after.

## Test matrix

| Stage | Test | Report | Checks PASS/total | FAIL ids | Result |
|---|---|---|---|---|---|
| F2 | F2 build tall@1 | `report_20261014_221815_930645_build` | 112/112 | - | PASS |
| F2 | F2 repeat 1 | `report_20261014_221933_071066_measure` | 112/112 | - | PASS |
| F2 | F2 repeat 2 | `report_20261014_222038_612655_measure` | 112/112 | - | PASS |
| F2 | F2 dado 10 | `report_20261014_222154_436467_measure` | 112/112 | - | PASS |
| F2 | F2 dado restore 6 | `report_20261014_222304_056643_measure` | 112/112 | - | PASS |
| F2 | F2 ply 15 | `report_20261014_222413_469808_measure` | 112/112 | - | PASS |
| F2 | F2 ply restore 18 | `report_20261014_222522_362757_measure` | 112/112 | - | PASS |
| F2 | F2 width 700 | `report_20261014_222631_349926_measure` | 112/112 | - | PASS |
| F2 | F2 width restore 600 | `report_20261014_222740_318419_measure` | 112/112 | - | PASS |
| F2 | F2 depth 600 | `report_20261014_222849_483273_measure` | 112/112 | - | PASS |
| F2 | F2 depth restore 550 | `report_20261014_222958_385993_measure` | 112/112 | - | PASS |
| F2 | F2 height 2000 | `report_20261014_223108_562171_measure` | 112/112 | - | PASS |
| F2 | F2 height restore 1900 | `report_20261014_223217_991345_measure` | 112/112 | - | PASS |
| F2 | F2 NEGATIVE height 2300 | `report_20261014_223326_336585_measure` | 111/112 | profile.tall.height_range | PASS (expected negative FAIL) |
| F2 | F2 post-negative restore 1900 | `report_20261014_223443_080543_measure` | 112/112 | - | PASS |
| F2 | F2 save/close/reopen measure | `report_20261014_223623_948717_measure` | 112/112 | - | PASS |
| F2 | F2 cut audit | `cut_audit_g3_20261014_223720_971180` | 6/6 | - | PASS |
| F3 | F3 build overhead@1 | `report_20261014_223912_665809_build` | 62/62 | - | PASS |
| F3 | F3 repeat 1 | `report_20261014_224020_512260_measure` | 62/62 | - | PASS |
| F3 | F3 repeat 2 | `report_20261014_224104_440286_measure` | 62/62 | - | PASS |
| F3 | F3 dado 10 | `report_20261014_224212_027389_measure` | 62/62 | - | PASS |
| F3 | F3 dado restore 6 | `report_20261014_224315_715550_measure` | 62/62 | - | PASS |
| F3 | F3 ply 15 | `report_20261014_224419_692122_measure` | 62/62 | - | PASS |
| F3 | F3 ply restore 18 | `report_20261014_224523_727191_measure` | 62/62 | - | PASS |
| F3 | F3 width 1100 | `report_20261014_224627_423936_measure` | 62/62 | - | PASS |
| F3 | F3 width restore 1000 | `report_20261014_224731_497110_measure` | 62/62 | - | PASS |
| F3 | depth 350 -> 400 and restore | - | - | - | **DEFERRED** |
| F3 | height 400 -> 500 and restore | - | - | - | **DEFERRED** |
| F3 | negative height 800 (`profile.overhead.height_range`) and restore | - | - | - | **DEFERRED** |
| F3 | save / close / reopen / measure | - | - | - | **DEFERRED** |
| F3 | independent cut audit (2/2) | - | - | - | **DEFERRED** |
| F0 | legacy A-E regression under G3 (incl. 15 mm ply / 8 mm dado -> 1185.4 mm) | - | - | - | **DEFERRED** |

## Summary

- **Completed and passed:** F2 tall: build (112/112), 2 repeats, all 5 scalar edit/restore pairs (dado 10, ply 15, width 700, depth 600, height 2000 giving `Cab_Compartment` 477.5), negative test, post-negative restore, save/close/reopen measure, cut audit 6/6. F3 overhead: build (62/62, shelf 975.4, compartment 173), 2 repeats, and the dado 10, ply 15 and width 1100 edit/restore pairs.
- **Expected negative failure:** F2 `Cab_Height` = 2300 gave exactly one FAIL, `profile.tall.height_range` (observed 2300, limits 1400-2200), 0 UNKNOWN, all 111 other checks PASS. The parameter stayed 2300 (not auto-corrected). Restored to 1900: 112/112 PASS.
- **Unexpected failures:** none.
- **Counts stable:** tall 20 params / 9 root occurrences / 10 components / 39 timeline items in every report; overhead 16 / 8 / 9 / 28. `entities.managed_ids` 9/9 (tall) and 8/8 (overhead) on every run; stored spec unchanged in every measurement.
- **Hashes:** tall `4026125d3a279b956198cb9620ca30397bc88d6be4de9aef756687530a638eb0`, overhead `6c15b5e34fdedbff55f796d416f4c3dc89a3109b58b71d264df668a4d322c2b2`; both match the offline G3 loader; schema 0.2, not migrated.
- **Saved state:** `v5-g3-tall` was saved at its restored baseline (22:35:26), closed, reopened and measured 112/112. After the audit its open tab shows `*` only because the audit moved and restored the timeline marker; it was not saved, so the saved version is the verified baseline. `v5-g3-overhead` was saved at its verified baseline after the width restore (all five base values read back in Change Parameters; the last measurement, 22:47:31, matched the build expressions exactly). Its save/reopen *test* is DEFERRED.
- **Cut audits:** F2 PASS 6/6 (each `dado.shelfN.left/right` cuts exactly one body, `panel.left.001` / `panel.right.001`, never a shelf; timeline marker 39/39 restored; counts before == after). F3 audit DEFERRED.
- **Spec file left installed:** `cabinet_spec.json` beside the generator is currently the committed `specs/overhead.json` (blob `88718d5`). It only affects a *new* build. Earlier copies are in `spec-backups/`.
- **Limitations:** fixture sizes only; width/depth/height edit values were chosen inside each profile's provisional range (the protocol does not fix them); F0 A-E under G3 not run; no manual UI inspection.

## Files

- `reports/report_20261014_221815_930645_build.txt` sha256 `7b03b746c47146e51a9411efccd8cf172aa6577bb10b9968bd424fecbf65449b`
- `reports/report_20261014_221815_930645_build.json` sha256 `48ae55693eb3ff480e04bd6351c90ffe30036b6584d5be55ab583f2603ca3727`
- `reports/report_20261014_221933_071066_measure.txt` sha256 `8ae8dd897dcb9b5d5cbec5ca5e585da1e7de55f674cf7d6a4107e33410724cb6`
- `reports/report_20261014_221933_071066_measure.json` sha256 `36530466cb6f5d22283fa3b24ba7539dbec17e5d83247ce4f9a6452ed20e2cf8`
- `reports/report_20261014_222038_612655_measure.txt` sha256 `8ae8dd897dcb9b5d5cbec5ca5e585da1e7de55f674cf7d6a4107e33410724cb6`
- `reports/report_20261014_222038_612655_measure.json` sha256 `035139cc12b9d3191751eae631856335e848e3eef428788c4d8ff335a9cdc940`
- `reports/report_20261014_222154_436467_measure.txt` sha256 `a77c1eae98e4acebd10285e62397e3d789e560415fad81afba73fcf2f4f160f0`
- `reports/report_20261014_222154_436467_measure.json` sha256 `2733a122107fa5fb3822c5f0529b114ee81a0ab772144e380bc4a1839b5e387a`
- `reports/report_20261014_222304_056643_measure.txt` sha256 `8ae8dd897dcb9b5d5cbec5ca5e585da1e7de55f674cf7d6a4107e33410724cb6`
- `reports/report_20261014_222304_056643_measure.json` sha256 `75026cf56c07b5af572a0a55bab8fbfd23575acaf13d1fe400de5f437f0fb65a`
- `reports/report_20261014_222413_469808_measure.txt` sha256 `0c001bc6b3fc34e993a994cb3e46759fb6a8d6f368583c2a582800a47c19f040`
- `reports/report_20261014_222413_469808_measure.json` sha256 `97d1e616ddc85107b9b16d4b4458381be2a7b6b4f90693f0036721eecf70a2b0`
- `reports/report_20261014_222522_362757_measure.txt` sha256 `8ae8dd897dcb9b5d5cbec5ca5e585da1e7de55f674cf7d6a4107e33410724cb6`
- `reports/report_20261014_222522_362757_measure.json` sha256 `345fcc4ec4b6d447024e148e3f65149792f15a7249d5cb1e29868a2adc42680a`
- `reports/report_20261014_222631_349926_measure.txt` sha256 `2c75c2611a99cc724435831ed4f00b5501964b5c7e05f20e809df41db15b3ccd`
- `reports/report_20261014_222631_349926_measure.json` sha256 `7cb67017f2649f66cb89f8079f3403362f112973d965762c4b521624e2c506b7`
- `reports/report_20261014_222740_318419_measure.txt` sha256 `8ae8dd897dcb9b5d5cbec5ca5e585da1e7de55f674cf7d6a4107e33410724cb6`
- `reports/report_20261014_222740_318419_measure.json` sha256 `c95b14abef47cfb87cb04b3afbd58033d90b51773216a964d462c483e3fc5090`
- `reports/report_20261014_222849_483273_measure.txt` sha256 `8dc6ac9b7adef6263f4ed9b9916a9ec8f1c6d0e4fb7cb13fa97f31adc5c2d878`
- `reports/report_20261014_222849_483273_measure.json` sha256 `80f12dec657ca52d057f733dba965b5dc800c9d3da19aaf9f306a38cf0dd9a19`
- `reports/report_20261014_222958_385993_measure.txt` sha256 `8ae8dd897dcb9b5d5cbec5ca5e585da1e7de55f674cf7d6a4107e33410724cb6`
- `reports/report_20261014_222958_385993_measure.json` sha256 `d4541a5443fc1ab31312439d2630c967c980e270accd433d2fac46c88a4fe2ed`
- `reports/report_20261014_223108_562171_measure.txt` sha256 `5c35f9e78da1647033e50ab326ce06a05ba0f45465f0aef5e382244113764626`
- `reports/report_20261014_223108_562171_measure.json` sha256 `5708792a8e3bfa27327ea99ce160512aa3f1598493faa1e47816bbddedc3a4b3`
- `reports/report_20261014_223217_991345_measure.txt` sha256 `8ae8dd897dcb9b5d5cbec5ca5e585da1e7de55f674cf7d6a4107e33410724cb6`
- `reports/report_20261014_223217_991345_measure.json` sha256 `f76502d4aabbb655040d729468f1782750fe81b7c3426e6e35c0077728ba04a1`
- `reports/report_20261014_223326_336585_measure.txt` sha256 `b751863b47aea578e8ff432b3c9d7027e5594a0900b7e779f93727d0e67915af`
- `reports/report_20261014_223326_336585_measure.json` sha256 `1999ee25c3acfc1e9946d6813ead3931bf24eb9b9655bbd079a5bcdd5db44bcd`
- `reports/report_20261014_223443_080543_measure.txt` sha256 `8ae8dd897dcb9b5d5cbec5ca5e585da1e7de55f674cf7d6a4107e33410724cb6`
- `reports/report_20261014_223443_080543_measure.json` sha256 `3d78de9bd83310822b157a8b210ee0c26cfead278383249137b811a68173ede1`
- `reports/report_20261014_223623_948717_measure.txt` sha256 `8ae8dd897dcb9b5d5cbec5ca5e585da1e7de55f674cf7d6a4107e33410724cb6`
- `reports/report_20261014_223623_948717_measure.json` sha256 `804a13426eabf4ecc98680eeb75841e41009fa92a8592c8a42ecfa83ee2a29de`
- `reports/cut_audit_g3_20261014_223720_971180.txt` sha256 `c0cef87bb3e86b57cea1edb551049c81dad249f84034eb3c872dc1d8c2fe50ab`
- `reports/cut_audit_g3_20261014_223720_971180.json` sha256 `2514f9105991b02ba113c926f415a446e29d67009247d0e372092bfe1d15b434`
- `reports/report_20261014_223912_665809_build.txt` sha256 `626560e195d55dc5ef4ef44170d040918437aee813e8c6075df169f782fc4c1e`
- `reports/report_20261014_223912_665809_build.json` sha256 `799c23c2e3ab4aee2f599eed0bba8f286131262dfd91ebc35738d3b08e28cecc`
- `reports/report_20261014_224020_512260_measure.txt` sha256 `9a52c788090b2277b50729a0c86f60302a829d88038085afdcc9df9f808932b8`
- `reports/report_20261014_224020_512260_measure.json` sha256 `871a6ea39a8d9dca90ffa28fe188e7dc008cb18f61a0584495e4302180d66772`
- `reports/report_20261014_224104_440286_measure.txt` sha256 `9a52c788090b2277b50729a0c86f60302a829d88038085afdcc9df9f808932b8`
- `reports/report_20261014_224104_440286_measure.json` sha256 `c9f6be55fdacd06dc94c8f3ffeb9a4d4a2a9e1d07a2e95631a7e0704ab8004b1`
- `reports/report_20261014_224212_027389_measure.txt` sha256 `3bf0cfcc93178cefdcac4fd5a60fcef43c673a05fcba62081b5f1bfd94c59d48`
- `reports/report_20261014_224212_027389_measure.json` sha256 `2a7c761ecabd7ae421cc4fb23b0bedb6656a7085e5be3eca294cb736e0959a88`
- `reports/report_20261014_224315_715550_measure.txt` sha256 `9a52c788090b2277b50729a0c86f60302a829d88038085afdcc9df9f808932b8`
- `reports/report_20261014_224315_715550_measure.json` sha256 `e07a415be4ed6af4503504aa86473fadce99c6ef233124fab3852a22edbf88c6`
- `reports/report_20261014_224419_692122_measure.txt` sha256 `10f934d4675dd9e12384cf5f99681f26ff691f8607e6ff2bdb62d813d292ef32`
- `reports/report_20261014_224419_692122_measure.json` sha256 `67044cd60855cb60b8872495814a6979af27eb1eda81312e9b8f4da3f0531d5b`
- `reports/report_20261014_224523_727191_measure.txt` sha256 `9a52c788090b2277b50729a0c86f60302a829d88038085afdcc9df9f808932b8`
- `reports/report_20261014_224523_727191_measure.json` sha256 `c56a7f0c18dd6cb6ad2f8a81f0d675642d238eeb694699b9e652b75b9c9dbaec`
- `reports/report_20261014_224627_423936_measure.txt` sha256 `25c052fec2a14d83218ceaff7c7dea8b22a56c5ff75570289a45a99f98319bd8`
- `reports/report_20261014_224627_423936_measure.json` sha256 `8eadb4e7f86423f4e434f82e9ac35f3fff1f8e0730008fbd9a62e2b44f9c8e2b`
- `reports/report_20261014_224731_497110_measure.txt` sha256 `9a52c788090b2277b50729a0c86f60302a829d88038085afdcc9df9f808932b8`
- `reports/report_20261014_224731_497110_measure.json` sha256 `abfdf3e9863bf2c3317cf1486d5acc879f0db7a267c47da8de291d44214b5c4b`
- `verification/verify_g3.py` sha256 `c66382a492ed28c24834287f5ac5409f1aec0d86d1057c9e578802fd81074423`
- `verification/verify_audit.py` sha256 `d007e744d9feb9a4e2b20ffd2aea4ec80999dcf3ea7802043dbf32532d3754f8`
- `verification/vt.sh` sha256 `0dbc8aa7bd6d995099241d0a7caf3c0506b16520411275d8577b711fdaea47fb`
- `verification/results.jsonl` sha256 `aa7ba816fc5b3a277ad9f35cfd2b232775f90c8a20c0b0f4cc415b17abb73ff2`
- `verification/package_f2f3.py` sha256 `959d932ce056bfd693327329b9569b218eed873ac9ad093ea86fbd8ebecbf9b5`
- `spec-backups/cabinet_spec.before-F2.base.json` sha256 `eb71b4d506316b58cba59ea436012420ffc57c8e2dbd55a45484d75eee4db44f`
- `spec-backups/cabinet_spec.before-F3.tall.json` sha256 `d528c32327e53e87ad43ac2fe3c98271779d79cdd31558c7e77437be119c6c42`
