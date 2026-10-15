# Configurable interior layouts (runner 0.3.0)

Use the existing create/build/save queue workflow. `run_approved_demo` accepts
optional `layout_mm` with finite numeric values for Bed_Width, Bed_Length,
Bed_Height, Kitchen_X and Kitchen_Y. Unknown keys, strings, booleans and nonfinite
values are refused. All lengths and coordinates are millimetres.

The bed is centered across the van and anchored at the rear. Height is the deck
underside Z datum; the 18 mm deck top is height + 18. Kitchen X/Y locate the
front-left of the whole cabinet, including doors; its occupied depth is 568 mm.
Van envelope remains the existing 1800 x 4000 x 2000 demonstration fixture.

Example build args:
```json
{"demo_id":"<create job ID>","entry_point":"FirstInteriorDemo",
 "layout_mm":{"Bed_Width":1500,"Bed_Length":2000,"Bed_Height":650,
              "Kitchen_X":200,"Kitchen_Y":600}}
```

Pure preflight rejects geometry outside the envelope and overlapping occupied
bed/kitchen bounding boxes before the first CAD operation. Occupied bed bounds
include under-bed space; furniture cannot be placed inside that void simply
because a solid-body interference test would miss it. Tangency is allowed but
does not certify usable clearance. Bed length must accommodate both supports.
A refused session is terminal and cannot be saved. CAD failures also block save.

Successful builds retain the original five smoke-test stages, plus kitchen X/Y
edit/restore stages in `layout_edit_stages`. All actual BRep bounds and volumes,
stable IDs, groove center probes and interference must pass; baseline parameters
and object counts must restore. Raw body min/max coordinates are now recorded.
Bed length testing shrinks relative to the requested length, keeping the original
default test 1900 -> 1800 -> 1900. Save remeasures the configured assembly.

Compatibility: omitted layout_mm uses the unchanged 24-parameter default; explicit
layout_mm adds Bed_Width (25 parameters) while retaining all existing Cab_* and
interior parameter names and stable IDs. There is no migration of existing designs.

## Targeted persistence check

`verify_demo_persistence {"design_id":"<explicit saved demo lineage>"}` requires
that ID in local config `demo_persistence_design_ids`, excludes protected IDs,
and requires the exact active saved/unmodified demo and its marker. It measures
before closing, closes only that clean target without saving, reopens the same
cloud file, then compares bounds/volumes/parameters/counts/identity/version.
Other open documents are checked against unchanged name/valid/saved/modified
snapshots. Any missing evidence, failed reopen or mismatch is FAIL/UNKNOWN.
It never saves dirty documents or discards changes; a dirty target is refused.

Evidence: [configurable-layouts/STATUS.md](evidence/configurable-layouts/STATUS.md).
No structural, van-fit, road-legal or manufacturing approval is implied.
