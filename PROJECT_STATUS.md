# VanDesign current status

**18 October 2026.** Issue #43 live composition accepted; approved Runner upgrade installed. `main` is unchanged. Rules: [AGENTS.md](AGENTS.md). Next work: [ROADMAP.md](docs/ROADMAP.md).

## Works today

| Capability | Where it was proven |
| --- | --- |
| Base, tall and overhead cabinets; width and shelf-count edits; shelves sit in side-panel grooves | Live Fusion: [G3](https://github.com/AnyBuzzin/van-design-system/issues/4), [G4](https://github.com/AnyBuzzin/van-design-system/pull/22), [G5](https://github.com/AnyBuzzin/van-design-system/pull/25) |
| Three-panel bed, resizable in width, length and height | Live Fusion: [PR #30](https://github.com/AnyBuzzin/van-design-system/pull/30) |
| Bed + cabinet: 11 solids, exact two-side dado ownership, zero interference; both widths edit/restore; test closes unsaved with original document baseline preserved | Live Fusion: 95/95 checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/43#issuecomment-6255609683), [independent acceptance](https://github.com/AnyBuzzin/van-design-system/pull/45#pullrequestreview-5565186671) |
| Nominal cut lists (CSV/JSON) | Offline; not CNC toolpaths |

## Now

Next: bounded cabinet-position edits and collision refusal ([#46](https://github.com/AnyBuzzin/van-design-system/issues/46)). Accepted baseline: bed at (0,0,0), cabinet at (1500,0,0) mm, 100 mm gap.

## Owner to-do

- Turn on branch protection for `develop` requiring `unit-tests (3.10)` and `unit-tests (3.12)` ([#16](https://github.com/AnyBuzzin/van-design-system/issues/16)).
- Decide whether the repository should be private.
- Check which Fusion licence is needed for commercial use.

## Not yet proven

Combined position edits, combined save/reopen, measured vehicle fit, loads and anchoring, CNC output. The exact V4 source file ([#1](https://github.com/AnyBuzzin/van-design-system/issues/1)) is unknown and blocks nothing.
