# VanDesign current status

**19 October 2026.** Issue #56 under-bed storage qualification passed; approved Runner correction installed. Adopted strategy: design to a measured plywood-lined interior ([ADR-0002](docs/decisions/ADR-0002-lined-interior-envelope.md)). `main` is unchanged. Rules: [AGENTS.md](AGENTS.md). Next work: [ROADMAP.md](docs/ROADMAP.md) Phase A.

## Works today

| Capability | Where it was proven |
| --- | --- |
| Base, tall and overhead cabinets; width and shelf-count edits; shelves sit in side-panel grooves | Live Fusion: [G3](https://github.com/AnyBuzzin/van-design-system/issues/4), [G4](https://github.com/AnyBuzzin/van-design-system/pull/22), [G5](https://github.com/AnyBuzzin/van-design-system/pull/25) |
| Three-panel bed, resizable in width, length and height | Live Fusion: [PR #30](https://github.com/AnyBuzzin/van-design-system/pull/30) |
| Bed + cabinet: 11 solids, exact two-side dado ownership, zero interference; both widths edit/restore; test closes unsaved with original document baseline preserved | Live Fusion: 95/95 checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/43#issuecomment-6255609683), [independent acceptance](https://github.com/AnyBuzzin/van-design-system/pull/45#pullrequestreview-5565186671) |
| Cabinet placement (1500,0) to (1600,100) and back: doors follow, cuts/volumes/interference verified; overlapping (100,100) refused without mutation; both existing documents preserved | Live Fusion: 140/140 stage checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/46#issuecomment-6256189001), [independent acceptance](https://github.com/AnyBuzzin/van-design-system/pull/49) |
| Bed + cabinet in an UNMEASURED Transit test envelope with assumed wheel arches; 382 mm deck/arch clearance, 634 mm nominal right strip; unsafe move refused unchanged | Live Fusion: 176/176 checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/51#issuecomment-6257218503); four existing documents preserved |
| Five-panel under-bed storage box; width 600 -> 700 -> 600 mm, eight butt contacts, safe restoration and collision refusal | Live Fusion: 452/452 checks, [results](https://github.com/AnyBuzzin/van-design-system/issues/56#issuecomment-6257745990); both existing documents and owner panel moves preserved |
| Nominal cut lists (CSV/JSON) | Offline; not CNC toolpaths |

## Now

Issue #56 bounded storage qualification is complete; Jack independently verified the measurements and exact final baseline. The first live run FAILED exact restoration on 2.65e-8 mm³ volume readback noise; the fix ([PR #58](https://github.com/AnyBuzzin/van-design-system/pull/58)) was rerun to 452/452. The box uses nominal 18 mm panels within an unmeasured test envelope; withdrawal/access, loads and real vehicle fit remain unqualified. Preserve the failed storage fixture, owner edits and original failure evidence.

Phase A close-out, Issue [#60](https://github.com/AnyBuzzin/van-design-system/issues/60): offline adapter regression and guarded persistence merged ([PR #63](https://github.com/AnyBuzzin/van-design-system/pull/63)). Live base checkpoint PASS 189/189 after the PR #49 adapter change. Combined save/reopen FAILED safely (geometry 113/113 identical, but the reopened document was flagged modified by the verification's timeline roll); fix merged ([PR #65](https://github.com/AnyBuzzin/van-design-system/pull/65)), live rerun UNKNOWN pending owner approval. The saved fixture `VanDesign-PhaseA-Combined-Persistence-20261019` (v1, unsaved changes) stays untouched. Phase B ([#61](https://github.com/AnyBuzzin/van-design-system/issues/61)) stays queued.

## Owner to-do

- For #60: approve the PR #65 Runner redeploy and live rerun; decide whether to keep or close (without saving) the open persistence fixture.
- When the target van is acquired and lined, measure its finished interior (ROADMAP Phase C). Until then, work uses the published Ford Transit L2H3 reference van.
- Decide whether the repository should be private.
- Check which Fusion licence is needed for commercial use.

## Not yet proven

General signed-coordinate/zero-crossing placement, combined save/reopen, measured vehicle fit, loads and anchoring, CNC output. The exact V4 source file ([#1](https://github.com/AnyBuzzin/van-design-system/issues/1)) is unknown and blocks nothing.
