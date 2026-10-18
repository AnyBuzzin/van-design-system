# VanDesign current status

**18 October 2026.** `develop` includes V6.3 and the simplified workflow. `main` is unchanged. Rules: [AGENTS.md](AGENTS.md). Next work: [ROADMAP.md](docs/ROADMAP.md).

## Works today

| Capability | Where it was proven |
| --- | --- |
| Base, tall and overhead cabinets; width and shelf-count edits; shelves sit in side-panel grooves | Live Fusion: [G3](https://github.com/AnyBuzzin/van-design-system/issues/4), [G4](https://github.com/AnyBuzzin/van-design-system/pull/22), [G5](https://github.com/AnyBuzzin/van-design-system/pull/25) |
| Three-panel bed, resizable in width, length and height | Live Fusion: [PR #30](https://github.com/AnyBuzzin/van-design-system/pull/30) |
| Bed and cabinet placed together as one 11-panel assembly | Offline only: [PR #32](https://github.com/AnyBuzzin/van-design-system/pull/32), [PR #35](https://github.com/AnyBuzzin/van-design-system/pull/35) |
| Nominal cut lists (CSV/JSON) | Offline; not CNC toolpaths |

## Now

Build the bed and cabinet together in Fusion: bed at (0,0,0), cabinet at (1500,0,0) mm, resizable in Fusion, no overlap.

## Owner to-do

- Turn on branch protection for `develop` requiring `unit-tests (3.10)` and `unit-tests (3.12)` ([#16](https://github.com/AnyBuzzin/van-design-system/issues/16)).
- In Fusion, save or discard the old open test documents and restart Fusion.
- Decide whether the repository should be private.
- Check which Fusion licence is needed for commercial use.

## Not yet proven

Combined model in live Fusion, save/reopen, measured vehicle fit, loads and anchoring, CNC output. The exact V4 source file ([#1](https://github.com/AnyBuzzin/van-design-system/issues/1)) is unknown and blocks nothing.
