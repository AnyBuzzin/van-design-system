# Issue #95 arc-centre failures: independent investigation (Claude, 27 October 2026)

Revised after the owner-approved read-only diagnostic (#95, comment 6431077873).

**The root cause remains UNKNOWN.** This document separates live results, post-failure observations, model consistency and hypotheses. The original live reports, the diagnostic report and its read errors are preserved unchanged:
- live results: `a29cc7` `8ee635a0…`, `564aff` `0ba2eba2…`, `d520bb` `f7ea8343…`;
- diagnostic: `issue95_arc_centre_20261027T005918Z_5d67c05a.json` `9068ba62…`, script source `6f7b4896…`.

**Correction.** An earlier version of this document said that all three runs failed on the first arc's first centre dimension. That was **wrong for run 1**. The diagnostic snapshot shows run 1's sketch with a fully driven first arc and a second arc. The run-1 trace never recorded which arc or axis failed. That premise, and every conclusion that depended on it, is withdrawn, including the model result that "every survivor needs the arc centre constrained at creation".

## Live results (traces)
| Run | Construction | Logged failure |
|---|---|---|
| `89b7a5a` | Arcs from a Point3D centre; coordinate dimensions on each `arc.centerSketchPoint` | `VCS_SKETCH_OVER_CONSTRAINTS` from an `addDistanceDimension` call. **Segment and axis not logged.** |
| `8b98209` (#104) | Explicit SketchPoint takes both coordinate dimensions, then is passed as the arc centre | `k.panel.left.001: arc 2 centre identity differs` |
| `6d4e87a` (#107) | As #104, then `driven.merge(arc centre)` returned True | `arc 2 … identity differs after merge` |

For runs 2 and 3, "arc 2" is segment index 2. In the bound loop's segment order, derived offline from the job's request, that is the loop's first arc: a 3 mm dog-bone relief and an exact semicircle.

## Post-failure observations (diagnostic, status PARTIAL)
- Fusion 2705.1.30. Eight documents were open, and all three expected sketches were found.
- **Eight `connectedEntities` reads failed**: the property returned None, then `.count` raised. Those connectivity values are **UNKNOWN**, not evidence of no connection.

| Fixture | Current state |
|---|---|
| Run 1 (open index 5) | **Two arcs.** The first arc and its centre are **fully constrained**: two driving coordinate dimensions, a 3 mm radial dimension and two parallel direction constraints. The second arc (centre −456.021, 20.579) is not fully constrained; its centre has **one** driving coordinate dimension. |
| Run 2 (index 6) | The arc centre (point 3) is **a different point** from the driven point (point 2), at the same position. The arc centre has no constraints or dimensions and is not fully constrained. The driven point has two driving dimensions. |
| Run 3 (index 7) | The two points are **still distinct**, now joined by a **CoincidentConstraint**. The arc centre is fully constrained; the arc is not. The driven point has two driving dimensions. |

- In all four arcs, two separate reads of `centerSketchPoint` compare equal, so no simple wrapper-inequality was observed in these reads.
- None of the three sketches is fully constrained.

**This is state after the failures.** It cannot show the order of creation, the state at arc creation, or what `merge()` did step by step.

## What the official documentation says, compared with what was observed
- **`SketchArcs.addByCenterStartSweep`.** The docs accept "an existing SketchPoint or a Point3D" as the centre, and do not say whether that point becomes the arc's centre.
  - *Observed (run 2):* the arc's centre is now a separate point with no link to the driven one.
- **`SketchPoint.merge`.** The docs say the input point is deleted and its references re-pointed.
  - *Observed (run 3):* both points still exist, joined by a coincident constraint. That is not what the documented outcome would leave behind. How it arose is not observable.
- **Equality.** Autodesk's help says `==` tests "the same Fusion object".
  - *Observed:* consistent for repeated reads of a centre. No universal claim follows.
- **Dimensioning an arc's own `centerSketchPoint`.**
  - *Observed (run 1):* this succeeded for at least the first arc, which is now fully driven. A later dimension in that sketch conflicted for a reason that is still UNKNOWN.

## Model (`hypotheses.py`): consistency only
The model covers **18 selected combinations** of three documented-open behaviours, tested against runs 2 and 3 and their snapshots. Run 1 is not modelled.
- **One fits:** the arc gets its own **unlinked** centre point, `==` compares entities, and `merge` **left both points, adding a coincident link** rather than redirecting.
- That is consistent with the evidence, not proven, and it does not explain run 1.

## Hypotheses (not established)
- **H1, supported by the snapshot.** Passing an existing SketchPoint as the arc centre did not make it the arc's centre in these sketches. Builds whose correctness rests on that identity (#104, #107) therefore rest on a premise the snapshot contradicts.
- **H2.** Run 1's conflict comes from how the second relief arc's constraints interact with earlier geometry in the same sketch. That geometry includes the first arc's fixed direction references, whose points all start at the datum location. **Not observed directly; UNKNOWN.**

Whether run 3's coincident link would make the geometry follow width edits is **not established**. No sketch was fully constrained, and no width edit was run.

## Direction accepted by Jack (#95): Option B
- The #95 Fusion sketches carry **no dog-bone reliefs**: lines and coordinate dimensions only.
- Fusion volumes, material probes, interference, full constraint and the native 1100 → 1000 → 1100 restoration are checked against a separately identified **relief-free core oracle**.
- **Every relief stays in the default manufacturing core and DXF.** These are checked offline:
  - analytic material and area differences against the relieved oracle;
  - DXF re-read.
- Absent Fusion relief probes are *offline-only / NOT RUN in Fusion*, never a live PASS.
- Stable IDs, exact cut ownership, refusal gates, restoration checks, default relieved outputs and hashes are preserved.
- Native width stays affine and dimension-driven, with no claim of general arc support.
- The lines-only path is unqualified until its own approved live test.
- **Not yet observed live:** lines joined at shared SketchPoints on this path.

Handoff after Jack confirms:
- Claude: the smallest relief-free producer and bindings change.
- Astra: the lines-only adapter and verification.

No further arc experiment, Fusion build, Runner change or fixture operation without separate owner approval.

## Files
- `inspect_failed_sketches.py`: the read-only diagnostic exactly as reviewed and run (source `6f7b4896…`). It is **unchanged**; its PARTIAL result is final and is not rerun.
- `hypotheses.py`: the revised consistency model described above.
