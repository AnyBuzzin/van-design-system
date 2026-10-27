# Issue #95 arc-centre failures: independent investigation (Claude, 27 October 2026)

Offline only: no Fusion, Runner or document operations. Raw live results were read, never modified (SHA-256 values match #95):
- `a29cc7`: `8ee635a0…`
- `564aff`: `0ba2eba2…`
- `d520bb`: `f7ea8343…`

**The root cause remains UNKNOWN.** This document separates what was observed from what is inferred or hypothesised.

## Observed (live results)
All three runs stop on the **first arc of the first native sketch**, `k.panel.left.001` segment 2. That arc is a 3 mm dog-bone relief and an **exact semicircle** (sweep −π, centre −571.979, 20.579 mm in sketch space). The only other geometry is the fixed datum point at (−750, −750). No earlier arc, line or constraint exists.

| Run | Construction | Result |
|---|---|---|
| `89b7a5a` | Arc from a Point3D centre, then a coordinate dimension on `arc.centerSketchPoint` | `VCS_SKETCH_OVER_CONSTRAINTS` from an `addDistanceDimension` call (axis not recorded) |
| `8b98209` (#104) | Explicit SketchPoint gets both coordinate dimensions (completed), then is passed as the arc centre | `arc.centerSketchPoint != point` |
| `6d4e87a` (#107) | As #104. The arc's centre read back valid, unfixed and at the expected XYZ; `driven.merge(centre)` returned True | still `!=` |

Run 1 *is* the "use the arc's own returned centre" construction, so that alternative has already failed once, for a reason not yet known.

## What the official documentation confirms (and does not)
- **Confirmed:** `SketchArcs.addByCenterStartSweep` accepts "an existing SketchPoint or a Point3D" as the centre. Negative sweeps are normalised to counter-clockwise.
  - **Not documented:** whether the arc's `centerSketchPoint` is the passed point, or whether a coincident constraint is created.
- **Confirmed:** Autodesk's help says Python `==` tests whether two variables reference "the same Fusion object". In the installed API, `Base.__eq__` compares the API object pointers after a type check.
  - **Not documented:** that sketch-point wrappers are unique per entity.
- **Confirmed:** `SketchPoint.merge` merges the input into this point, "deletes the other sketch point", and re-points its references.
  - **Not documented:** how this applies to a point an arc owns as its centre.
- **Confirmed (community practice, not a guarantee):** scripts commonly dimension a circle's `centerSketchPoint` after creation, so run 1 is not obviously ordinary behaviour.

## Model (hypotheses.py): consistency only
`hypotheses.py` models **24 selected combinations** of four behaviours the documentation leaves open. They do not exhaust what Fusion's API or solver might do. It runs the three attempts' control flow and keeps the combinations that reproduce all three outcomes; 8 survive.

All 8 include the `already_constrained` premise. That follows from the model's construction: in this model run 1 can *only* fail through that premise. So the result is **not independent evidence** that the arc centre was constrained at creation. It shows which modelled explanations stay consistent with the three results; it does not establish a cause.

## Leading hypothesis (not established)
The semicircular relief arc's centre is not a free, independently drivable point as constructed. Each attempt then tried to drive that same centre:
- directly, in run 1;
- by substitution, in run 2;
- by merge, in run 3.

Unknowns behind this hypothesis:
- whether the centre was constrained at creation, and if so why (an exact-semicircle special case is one candidate);
- whether Fusion copied the centre and linked it by coincidence;
- what `merge` actually did.

The previous fixes changed how the point was attached. Their offline fakes encoded the assumed contract and captured nothing of what Fusion built, so they could not distinguish these possibilities.

## What the proposed read-only inspection can and cannot show
`inspect_failed_sketches.py` would be run once, with owner approval. It reads the three failed sketches still open in their unsaved fixtures and writes **one new uniquely named report**, created exclusively so it never overwrites anything. The report contains:
- source hash and Fusion version;
- expected and observed sketch counts;
- complete, partial or error status;
- an explicit error record for every failed read, with UNKNOWN for any comparison that could not be evaluated.

**It can observe the current post-failure state:**
- points and their connectivity;
- the constraints and dimensions now on the arc centre;
- whether the arc centre is now the driven point, a separate point with a coincident constraint, or an unlinked copy;
- whether `==` holds between two reads of one property.

**It cannot prove** the state at arc creation, or replay what `merge` did. Any such conclusion drawn from the snapshot is an inference and will be labelled as one.

It edits, activates, saves and closes nothing. A later, separately approved step in a fresh scratch document could test creation-time behaviour, such as a non-semicircle arc. **No further cabinet build or arc variant until then.**

## Direction accepted by Jack (#95): Option B
- The #95 Fusion sketches carry **no dog-bone reliefs**: lines and coordinate dimensions only.
- Fusion volumes, material probes, interference, full constraint and the native 1100 → 1000 → 1100 restoration are checked against a separately identified **relief-free core oracle**.
- **Every relief stays in the default manufacturing core and DXF.** These are checked offline:
  - analytic material and area differences against the relieved oracle;
  - DXF re-read.
- Absent Fusion relief probes are reported as *offline-only / NOT RUN in Fusion*, never as a live PASS.
- Stable IDs, exact cut ownership, refusal gates, default outputs and hashes are preserved.
- Native width stays affine and dimension-driven, with no claim of general arc support.
- The lines-only path is unqualified until its own approved live test.
- **Not yet confirmed live:** lines joined at shared SketchPoints have not run on this path. Coordinate dimensions on a free SketchPoint did complete in runs 2 and 3.

Work on Option B starts only after the diagnostic decision boundary:
- Claude: the relief-free producer and bindings.
- Astra: the adapter and verification consumer.
