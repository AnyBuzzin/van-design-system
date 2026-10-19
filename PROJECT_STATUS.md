# VanDesign current status

**19 October 2026.** Issue #60 Phase A accepted under the owner-revised persistence scope; reviewed Runner 4081cb3 installed. `main` is unchanged. Rules: [AGENTS.md](AGENTS.md). Next work: [ROADMAP.md](docs/ROADMAP.md).

## Works today

| Capability | Where it was proven |
| --- | --- |
| Base, tall and overhead cabinets; width and shelf-count edits; shelves sit in side-panel grooves | Live Fusion: [G3](https://github.com/AnyBuzzin/van-design-system/issues/4), [G4](https://github.com/AnyBuzzin/van-design-system/pull/22), [G5](https://github.com/AnyBuzzin/van-design-system/pull/25) |
| Three-panel bed, resizable in width, length and height | Live Fusion: [PR #30](https://github.com/AnyBuzzin/van-design-system/pull/30) |
| Bed + cabinet: 11 solids, exact two-side dado ownership, zero interference; both widths edit/restore; test closes unsaved with original document baseline preserved | Live Fusion: 95/95 checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/43#issuecomment-6255609683), [independent acceptance](https://github.com/AnyBuzzin/van-design-system/pull/45#pullrequestreview-5565186671) |
| Cabinet placement (1500,0) to (1600,100) and back: doors follow, cuts/volumes/interference verified; overlapping (100,100) refused without mutation; both existing documents preserved | Live Fusion: 140/140 stage checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/46#issuecomment-6256189001), [independent acceptance](https://github.com/AnyBuzzin/van-design-system/pull/49) |
| Bed + cabinet in an UNMEASURED Transit test envelope with assumed wheel arches; 382 mm deck/arch clearance, 634 mm nominal right strip; unsafe move refused unchanged | Live Fusion: 176/176 checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/51#issuecomment-6257218503); four existing documents preserved |
| Five-panel under-bed storage box; width 600 -> 700 -> 600 mm, eight butt contacts, safe restoration and collision refusal | Live Fusion: 452/452 checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/56#issuecomment-6257745990); both existing documents and owner panel moves preserved |
| Full-scale dimensioned cutaway with readable plan labels; reference-only walls/roof and explicit assumptions | Live Fusion: 226/226 checks and independent image review, [results](https://github.com/AnyBuzzin/van-design-system/issues/60#issuecomment-6258304297) |
| Base width 1200 -> 1210 -> 1200 restored; combined scene saved/reopened clean at version 1 with unchanged geometry and affected-body ownership | Live Fusion: base 3 x 63 checks ([results](https://github.com/AnyBuzzin/van-design-system/issues/60#issuecomment-6258570019)); revised persistence 226/226 ([R2 results](https://github.com/AnyBuzzin/van-design-system/issues/60#issuecomment-6265892095)); configured participant-list persistence UNKNOWN |
| Nominal cut lists (CSV/JSON) | Offline; not CNC toolpaths |

## Now

Jack independently accepted and closed #60 under the revised owner-approved criterion: exact pre-save participants, clean reopen, unchanged measured geometry/state and exact affected-body ownership. Configured participant-list persistence remains UNKNOWN. The [original dirty-state failure](https://github.com/AnyBuzzin/van-design-system/issues/60#issuecomment-6258570019), failed fixture and historical evidence remain preserved. R2 is open, saved and clean; capacity was 4/10, owner read-only action pending. #61 stays queued pending owner progression; no further live work is assigned. Preserve all earlier fixtures and owner edits. Vehicle fit, access, loads and manufacturing remain unqualified.

## Owner to-do

- Mark **VanDesign-PhaseA-Combined-Persistence-20261019-R2** read-only in **VanDesign-V5-Demonstration-20261017-01**; leave the earlier failed fixture untouched.
- Turn on branch protection for `develop` requiring `unit-tests (3.10)` and `unit-tests (3.12)` ([#16](https://github.com/AnyBuzzin/van-design-system/issues/16)).
- Decide whether the repository should be private.
- Check which Fusion licence is needed for commercial use.

## Not yet proven

Configured participant-list persistence after reopen, general signed-coordinate/zero-crossing placement, measured vehicle fit, loads and anchoring, CNC output. The exact V4 source file ([#1](https://github.com/AnyBuzzin/van-design-system/issues/1)) is unknown and blocks nothing.
