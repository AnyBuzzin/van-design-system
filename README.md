# VanDesign

Python and Fusion tools for editable van furniture and, eventually, individual CNC panel exports.

[Current capability and next task](PROJECT_STATUS.md) · [Agent workflow](AGENTS.md) · [Product direction](docs/ROADMAP.md) · [Owner work plan](https://github.com/AnyBuzzin/van-design-system/issues/36)

## Architecture

src/vandesign is the maintained runtime: millimetre specifications and parametric panels/joints feed the Fusion adapter. Actual solid-body measurements qualify supported CAD behaviour. The existing Runner executes authorised jobs; historical prototypes remain evidence.

Nominal CSV/JSON panel previews are not CNC toolpaths. Structural strength, vehicle mounting, measured fit and manufacturing need separate qualification. Current evidence and limits belong in the status page linked above.

Develop is the integration branch; main is reserved for a separate release decision. See AGENTS.md for tests, review, permissions and reporting.

No redistribution licence is currently offered. Resolve Fusion licence eligibility before commercial use.
