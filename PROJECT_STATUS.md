# VanDesign current status

**26 October 2026.** E1.1 rounded-panel live qualification passed; reviewed Runner f24df89 installed. Adopted strategy: design to a plywood-lined interior ([ADR-0002](docs/decisions/ADR-0002-lined-interior-envelope.md)); reference van is the published VW Crafter CR35 LWB maxi, high roof, until the target van is acquired. `main` is unchanged. Rules: [AGENTS.md](AGENTS.md). Next work: [ROADMAP.md](docs/ROADMAP.md) M1 platform consolidation (PRs #76, #77).

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
| Flat lined-interior envelope; width edit/restore and unsafe storage move refused; both pre-existing documents preserved | Live Fusion: 480/480 checks, [B1 results](https://github.com/AnyBuzzin/van-design-system/issues/61#issuecomment-6405273183); finished nominal 1748 × 3008 × 1989 mm, 405 mm deck/arch and 598 mm right strip |
| One 600 × 800 × 18 mm panel with an upper-right rounded corner; radius 50 → 75 → 50 and invalid-radius preview refusal | Live Fusion: 72/72 checks, [E1.1 results](https://github.com/AnyBuzzin/van-design-system/issues/70#issuecomment-6405976728); actual bounds/volume, material probes, stable identity and exact state restoration; own fixture closed unsaved, full final inspection identical to baseline |
| Nominal cut lists (CSV/JSON) | Offline; not CNC toolpaths |

## Now

E1.1 passed the bounded nominal 18 mm rounded-panel test; Jack independently confirmed the raw results and full final baseline. Width/length edits remain offline-tested only, NOT RUN live; no saved persistence, joinery or CNC qualification. The [original B1 FAIL](https://github.com/AnyBuzzin/van-design-system/issues/61#issuecomment-6405161330), dirty failed fixture and clean owner blank remain preserved; capacity 2/10. B1 stepped ceilings and door keep-outs remain offline-only. Raw manual edits are not automatically guarded; configured participant-list persistence is UNKNOWN. Runner remains running; no further live work assigned. Vehicle fit, loads, anchoring and manufacturing remain unqualified.

## Owner to-do

- Mark **VanDesign-PhaseA-Combined-Persistence-20261019-R2** read-only in **VanDesign-V5-Demonstration-20261017-01**; leave the earlier failed fixture untouched.
- When the target van is acquired and lined, measure its finished interior (ROADMAP M6).
- Decide whether the repository should be private.
- Check which Fusion licence is needed for commercial use.

## Not yet proven

Configured participant-list persistence after reopen, general signed-coordinate/zero-crossing placement, measured vehicle fit, loads and anchoring, CNC output. The exact V4 source file ([#1](https://github.com/AnyBuzzin/van-design-system/issues/1)) is unknown and blocks nothing.
