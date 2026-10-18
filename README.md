# VanDesign — AI-assisted parametric van engineering

**Current state (18 October 2026):** V5 cabinet family and standalone bed have bounded real-Fusion evidence; V6.2 placement and V6.3 **combined bed + cabinet composition are accepted OFFLINE**, not yet qualified in a single live Fusion design. The project is **not manufacturing- or CNC-ready**.

[Current project status](PROJECT_STATUS.md) · [Next product capabilities](docs/ROADMAP.md) · [Owner-approved work plan](https://github.com/AnyBuzzin/van-design-system/issues/36) · [Engineering instructions](AGENTS.md)

## What VanDesign does today

- Generates base, tall and overhead **parametric cabinet panels** using named Fusion parameters and explicit owned dado cuts.
- Generates a standalone three-panel nominal 18 mm bed, with tested size edits in Fusion.
- Uses **V6.2 CAD-neutral layout checks** to place one bed and one cabinet, refuse collisions and preserve independent panel identities.
- Uses **V6.3 offline symbolic composition** to prepare an 11-panel, two-cabinet-dado combined assembly without duplicating source formulas. **This exact composition has not yet passed live Fusion BRep qualification.**
- Produces deterministic nominal CSV/JSON panel previews; these are not CNC toolpaths or physically qualified cutting instructions.

## Architecture

The maintained Python runtime is **src/vandesign**: typed millimetre specs → CAD-neutral expressions/panels/joints → Fusion adapter → measured BRep verification for supported live tests. The existing Fusion Runner can execute specifically authorised bounded jobs. Historical V4/V5 prototypes remain as evidence, **not a second maintained runtime**. No additional orchestration platform is required.

## Engineering and business boundaries

Start from integrated **develop**; leave **main** for a separate release decision. Make focused PRs with actual PASS/FAIL/UNKNOWN results, preserve existing Fusion designs and evidence, and follow [precision/cut ownership rules](docs/standards/precision-and-ownership.md). Branch protection and live-Fusion activation remain to be verified; see [Issue #16](https://github.com/AnyBuzzin/van-design-system/issues/16) and [Issue #36](https://github.com/AnyBuzzin/van-design-system/issues/36).

Current software output is **not validated** for structural load, vehicle mounting, measured fit, CNC tooling or commercial manufacturing. The exact original executed V4 source is still [unresolved](https://github.com/AnyBuzzin/van-design-system/issues/1). A separate licence decision is needed before commercial Fusion use.

**No redistribution licence is currently offered.** The repository's public visibility does not mean its content is approved for unrestricted reuse.
