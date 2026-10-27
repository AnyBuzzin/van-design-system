# Issue #95 arc-centre failures: independent investigation (Claude, 27 October 2026)

Offline only: no Fusion, Runner or document operations. Raw live results were read, never modified (SHA-256 values match #95):
- `a29cc7`: `8ee635a0…`
- `564aff`: `0ba2eba2…`
- `d520bb`: `f7ea8343…`

## What failed, exactly
All three live runs stop on the **first arc of the first native sketch**, `k.panel.left.001` segment 2. That arc is a 3 mm dog-bone relief and an **exact semicircle** (sweep −π, centre −571.979, 20.579 mm in sketch space). The only other geometry is the fixed datum point at (−750, −750). No earlier arc, line or constraint exists.

| Run | Construction | Result |
|---|---|---|
| `89b7a5a` | Arc from a Point3D centre, then a coordinate dimension on `arc.centerSketchPoint` | `VCS_SKETCH_OVER_CONSTRAINTS` on the **first** dimension call |
| `8b98209` (#104) | Explicit SketchPoint gets both coordinate dimensions (succeeded), then is passed as the arc centre | `arc.centerSketchPoint != point` |
| `6d4e87a` (#107) | As #104. The arc's centre was valid, unfixed and at the expected XYZ; `driven.merge(centre)` returned True | still `!=` |

The first run *is* the "use the arc's own returned centre as the authoritative reference" approach. It is the most direct documented construction, and it failed first.

## What the official documentation confirms (and does not)
- **Confirmed:** `SketchArcs.addByCenterStartSweep` accepts "an existing SketchPoint or a Point3D" as the centre. Negative sweeps are normalised to counter-clockwise, which swaps the endpoints.
  - **Not documented:** that the arc's `centerSketchPoint` *is* the passed point, or that a coincident constraint is created.
- **Confirmed:** Autodesk's help says Python `==` tests whether two variables reference "the same Fusion object". In the installed API, `Base.__eq__` compares the API object pointers after a type check.
  - **Not documented:** that sketch-point wrappers are unique per entity.
- **Confirmed:** `SketchPoint.merge` merges the input point into this one, "deletes the other sketch point", and re-points its references.
  - **Not documented:** how this applies to a point an arc owns as its centre.
- **Confirmed:** dimensioning a circle's `centerSketchPoint` after creation is common forum practice. So O1 is **not** normal behaviour for an ordinary free centre.

## Independent reproduction
`hypotheses.py` models every combination of the behaviours the documentation leaves open (24 in total). It runs the three attempts' control flow under each and keeps the combinations that reproduce all three live outcomes. **8 survive, and every one of them needs the same fact: the arc's own centre was already constrained when Fusion created it.** That is what run 1 showed directly.
- Runs 2 and 3 only tried ways of attaching *another* point to that centre.
- Under Autodesk's documented `==`, the survivors also need Fusion to have given the arc its own centre point and `merge` not to have redirected it.

The model reflects API contracts, not Fusion's solver. It narrows the explanation; it does not prove it.

## Most likely root cause
**The semicircular dog-bone arc's centre is not a free, independently drivable point in Fusion as constructed** (medium confidence). Every attempt has tried to drive that centre: directly in run 1, by substitution in run 2, by merge in run 3. The identity gates in runs 2 and 3 failed for the same underlying reason; they are not the defect themselves.

Still UNKNOWN:
- why the centre is already constrained. Candidates include an exact-semicircle special case, or Fusion defining the centre from the arc;
- whether it is linked by coincidence to the driven point.

The previous fixes changed how the point was attached but never captured what Fusion actually built. Their offline fakes encoded the assumed contract, so they could only confirm that assumption.

## What would settle it
One **read-only** inspection, `inspect_failed_sketches.py`, run once with owner approval. It reads the three failed sketches still open in their unsaved fixtures and writes JSON:
- points;
- the arc centre's fixed and constraint state;
- the constraints and dimensions on that centre;
- reuse versus copy (point count at the centre and any coincident constraint);
- the merge result;
- whether `==` holds between two reads of the same property.

It edits, activates, saves and closes nothing. A second, separately approved step could test a non-semicircle arc in a fresh scratch document. **No further cabinet build until then.**

## Simplest defensible way forward (decision for Jack and the owner)
**Option B: no arcs in the #95 Fusion sketches.**
- Dog-bone reliefs are manufacturing-only. `PanelProfile` already notes them as "not present in the CAD body", and the DXF/CNC geometry comes from the core.
- Without reliefs, every tab-and-slot cabinet loop is rectilinear: lines plus coordinate dimensions only.
  - Coordinate dimensions on a free SketchPoint succeeded live in runs 2 and 3.
  - Lines joined at shared SketchPoints have **not** yet run live on this path. The existing "one fully constrained profile" gate would catch a failure; it is not relaxed.
- Width editing stays genuinely native: the same affine bindings, produced from the relief-free profile.
- Proof stays exact:
  - Fusion volumes and probes are checked against the relief-free core profile;
  - the core proves offline that relief-free plus relief areas equals the DXF profile;
  - the DXF is re-read against the core;
  - interference with reliefs absent is conservative, because reliefs only remove material.
- **Trade-off:** #95 criterion 2 currently asks for Fusion probes at "every arc and relief". That criterion would move to the core and DXF. Arcs come back later, after the diagnostic, for visible fillets (worktop), where Fusion's documented `SketchArcs.addFillet` builds tangent-constrained arcs.

**Option A:** keep reliefs in Fusion and choose an arc construction only after the diagnostic shows what Fusion does. Any choice before that would be another speculative cycle.

Recommendation: **approve the read-only diagnostic and adopt Option B for #95 now.**
- The producer change is small and offline: relief-free bindings.
- The adapter loses its arc branch for this path (Astra's file).
- The live width test can then proceed on lines only, while the diagnostic informs arcs for later work.
