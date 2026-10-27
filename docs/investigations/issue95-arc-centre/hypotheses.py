"""Issue #95 arc-centre failures: which Fusion behaviours explain all three live runs?

Standalone and offline (no adsk, no repository imports): python hypotheses.py

A tiny sketch model is run through the control flow of the three live
attempts under 24 SELECTED combinations of four behaviours the documentation
leaves open (not every behaviour the API or solver could have), and each is
checked against what the runs observed. It models API contracts, not Fusion's
solver; a surviving combination is "consistent with the model and the three
results", not "true". In this model attempt 1 can only fail through the
already_constrained premise, so every survivor carries it by construction:
that is not independent evidence of the root cause, which remains UNKNOWN.

Live observations (raw results preserved in the Runner queue):
  O1 89b7a5a vd-20261026T230116-a29cc7: arc made from Point3D centre; the first
     coordinate dimension on arc.centerSketchPoint -> VCS_SKETCH_OVER_CONSTRAINTS.
  O2 8b98209 vd-20261026T231835-564aff: explicit SketchPoint takes both coordinate
     dimensions; arc made with it as centre; arc.centerSketchPoint != it.
  O3 6d4e87a vd-20261026T235800-d520bb: as O2, the arc's centre is valid, unfixed and
     at the expected XYZ; driven.merge(arc centre) returns True; still !=.
All three fail on the first arc of k.panel.left.001: a 3 mm dog-bone relief, an
exact semicircle (sweep -pi), the only geometry in the sketch besides the fixed datum.
"""
from itertools import product

AXES = {
    # SketchArcs.addByCenterStartSweep given an existing SketchPoint centre ("can be an existing SketchPoint")
    "centre_input": ("reuse", "copy_coincident", "copy_unlinked"),
    # Python == on two wrappers of one sketch point (Autodesk help: == tests "the same Fusion object")
    "equality": ("entity", "wrapper"),
    # driven.merge(arc centre): documented = input deleted, the arc now references `driven`
    "merge": ("documented", "keeps_arc_point"),
    # adding a coordinate dimension to a free arc's own centre (Point3D-made arc)
    "own_centre": ("free", "already_constrained"),
}


class OverConstrained(Exception):
    pass


class Model:
    def __init__(self, b):
        self.b, self.next_id, self.dims, self.coincident = b, 0, {}, set()

    def point(self):
        self.next_id += 1
        self.dims[self.next_id] = 0
        return self.next_id

    def wrap(self, pid):
        # Under "wrapper" equality every property read is a new object that compares unequal.
        return ("w", pid, self.next_wrapper()) if self.b["equality"] == "wrapper" else ("w", pid)

    _n = 0

    def next_wrapper(self):
        Model._n += 1
        return Model._n

    def dimension(self, pid, owned_by_arc=False):
        if owned_by_arc and self.b["own_centre"] == "already_constrained":
            raise OverConstrained
        self.dims[pid] += 1

    def arc(self, centre_pid=None):
        if centre_pid is None or self.b["centre_input"] != "reuse":
            own = self.point()
            if centre_pid is not None and self.b["centre_input"] == "copy_coincident":
                self.coincident.add((own, centre_pid))
            return {"centre": own}
        return {"centre": centre_pid}

    def merge(self, keep, other, arc):
        if keep == other:
            return True                       # merging a point with itself: assume a True no-op
        if self.b["merge"] == "documented":
            arc["centre"] = keep
        return True


def attempt_1(m):
    arc = m.arc(None)
    try:
        m.dimension(arc["centre"], owned_by_arc=True)
        m.dimension(arc["centre"], owned_by_arc=True)
    except OverConstrained:
        return "over_constrained"
    return "ok"


def attempt_2(m):
    driven = m.point()
    m.dimension(driven); m.dimension(driven)
    arc = m.arc(driven)
    return "identity_differs" if m.wrap(arc["centre"]) != m.wrap(driven) else "ok"


def attempt_3(m):
    driven = m.point()
    m.dimension(driven); m.dimension(driven)
    arc = m.arc(driven)
    if m.wrap(arc["centre"]) != m.wrap(driven):
        if m.merge(driven, arc["centre"], arc) is not True:
            return "merge_failed"
        if m.wrap(arc["centre"]) != m.wrap(driven):
            return "identity_differs_after_merge"
    return "ok"


OBSERVED = ("over_constrained", "identity_differs", "identity_differs_after_merge")


def consistent():
    out = []
    for values in product(*AXES.values()):
        b = dict(zip(AXES, values))
        got = (attempt_1(Model(b)), attempt_2(Model(b)), attempt_3(Model(b)))
        if got == OBSERVED:
            out.append(b)
    return out


if __name__ == "__main__":
    survivors = consistent()
    print("%d of %d selected model combinations reproduce all three live outcomes (consistency only):"
          % (len(survivors), len(list(product(*AXES.values())))))
    for b in survivors:
        print("  " + ", ".join("%s=%s" % kv for kv in b.items()))
