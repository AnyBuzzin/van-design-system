# First campervan interior demonstration

Branch `feature/first-interior-demo`, based on verified G4 `ce09a533`.
Uses the existing G3 cabinet generator and Fusion adapter unchanged.
All lengths are millimetres; X across, Y front to rear, Z up.

Fixture: 1800 x 4000 x 2000 rectangular envelope, open roof/front and low
side sills for visibility. Rear bed platform 1764 x 1900 at Z=700 with two
supports. Existing 1200 x 850 x 550 base cabinet is the simplified kitchen/storage
unit, offset to X=50, Y=100, Z=18. The 550 mm depth is the cabinet body;
including the front doors its occupied depth is 568 mm. No appliances, utilities or fixings.

## Run in Fusion

1. Check Data Panel > Editable Documents has spare capacity (user confirmed 3/10).
2. Leave all existing tabs untouched. File > New Design creates a new tab.
3. In that new empty tab, Utilities > Scripts and Add-Ins > Scripts > + / Add
   existing script, select this repository's `demos/FirstInteriorDemo` folder.
4. Select FirstInteriorDemo and click Run. Do not run on an existing design.
5. The script builds only in a completely empty, unsaved, unmodified parametric
   design. It never creates, saves, closes or switches documents.

The script measures BRep bounds and volumes for every panel, stable-ID counts
and body interference; then changes Bed_Length to 1800 and restores it,
changes Cab_Width to 1100 and restores it, measuring actual solids each time.
Reports are written to `demos/evidence/interior_<timestamp>.json` even on failure.
A failure can leave partial geometry in the dedicated demo document; never
rerun in that non-empty document. No automatic cleanup touches existing designs.

## Runner verification

After the build, leave the dedicated demo active. Use the existing runner's
read-only `ping` and `inspect_design` to capture document/version/counts.
The runner's cabinet-only `measure` is not an interior validator: this demo
does not store a cabinet spec as though it described the whole interior.
Do not submit parameter mutation jobs against any existing design.

## Status and limits

Fusion 2705.1.30: first build, BRep bed/cabinet edit-and-restore tests and
interference checks PASS for this fixture (95 checks across five stages).
The live runner independently confirmed restored parameters and object counts.
See `evidence/STATUS.md` for evidence, placement and remaining UNKNOWN checks.
The original report stores dimension-check verdicts rather than raw BRep corners.
Save/reopen persistence remains UNKNOWN. Offline layout tests are not geometry evidence.
This fixture is not measured van-fit, structural, road-legal or manufacturing approval.
