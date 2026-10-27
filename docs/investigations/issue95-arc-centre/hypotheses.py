"""Issue #95 arc-centre failures: which modelled behaviours fit the evidence?

Standalone and offline (no adsk, no repository imports): python hypotheses.py

Revised after the owner-approved read-only diagnostic (report
issue95_arc_centre_20261027T005918Z_5d67c05a.json, SHA-256 9068ba62...,
status PARTIAL). The earlier version assumed every run failed on the first
arc's first centre dimension; the snapshot contradicts that for run 1, so
that premise and every conclusion drawn from it are withdrawn.

This models only runs 2 and 3 (8b98209, 6d4e87a), which both log arc index 2
of k.panel.left.001 (the loop's first arc). Run 1 is NOT modelled: its
failing segment and axis were not logged, and its surviving sketch has a fully
driven first arc and a second arc with one centre dimension. Why a dimension
there over-constrained remains UNKNOWN.

It checks 3 x 2 x 3 = 18 SELECTED combinations of three behaviours that the
documentation leaves open (not every behaviour the API or solver could
have) against two kinds of evidence:
  live results  R2: arc centre != the driven point after creation;
                R3: merge() returned True, centre still != driven point.
  snapshot      S2 (run 2 fixture): driven point and arc centre are distinct, at one
                   position, with no constraint or dimension on the arc centre;
                S3 (run 3 fixture): still distinct, now joined by a CoincidentConstraint;
                   arc centre fully constrained; two repeat reads of the centre compare
                   equal (all four arcs).
The snapshot is post-failure state: it cannot show creation-time state or replay
merge(). Survivors are consistent with the model and the evidence, not proven,
and say nothing about why run 1 conflicted. Root cause remains UNKNOWN.
"""
from itertools import product

AXES = {
    # SketchArcs.addByCenterStartSweep given an existing SketchPoint centre
    "centre_input": ("reuse", "copy_coincident", "copy_unlinked"),
    # Python == on two reads of one sketch point
    "equality": ("entity", "wrapper"),
    # driven.merge(arc centre): documented redirect, no effect, or a coincident link
    "merge": ("documented", "keeps_arc_point", "adds_coincident"),
}


class Sketch:
    def __init__(self, b):
        self.b, self.points, self.coincident, self.reads = b, 0, set(), 0

    def point(self):
        self.points += 1
        return self.points

    def read(self, pid):
        """A property read: a wrapper that compares by entity, or by read under 'wrapper'."""
        self.reads += 1
        return (pid,) if self.b["equality"] == "entity" else (pid, self.reads)

    def arc(self, centre):
        if self.b["centre_input"] == "reuse":
            return {"centre": centre}
        own = self.point()
        if self.b["centre_input"] == "copy_coincident":
            self.coincident.add(frozenset((own, centre)))
        return {"centre": own}

    def merge(self, keep, other, arc):
        if keep == other:
            return True
        if self.b["merge"] == "documented":
            arc["centre"] = keep
        elif self.b["merge"] == "adds_coincident":
            self.coincident.add(frozenset((keep, other)))
        return True


def run_2(s):
    driven = s.point()
    arc = s.arc(driven)
    live = "differs" if s.read(arc["centre"]) != s.read(driven) else "same"
    distinct = arc["centre"] != driven
    linked = frozenset((arc["centre"], driven)) in s.coincident
    return live, distinct, linked


def run_3(s):
    driven = s.point()
    arc = s.arc(driven)
    live = "same"
    if s.read(arc["centre"]) != s.read(driven):
        s.merge(driven, arc["centre"], arc)
        live = "differs_after_merge" if s.read(arc["centre"]) != s.read(driven) else "same"
    distinct = arc["centre"] != driven
    linked = frozenset((arc["centre"], driven)) in s.coincident
    repeat_equal = s.read(arc["centre"]) == s.read(arc["centre"])
    return live, distinct, linked, repeat_equal


# (live result, distinct now, coincident link now[, repeat reads equal])
OBSERVED_2 = ("differs", True, False)                       # R2 + S2
OBSERVED_3 = ("differs_after_merge", True, True, True)      # R3 + S3


def consistent():
    out = []
    for values in product(*AXES.values()):
        b = dict(zip(AXES, values))
        if run_2(Sketch(b)) == OBSERVED_2 and run_3(Sketch(b)) == OBSERVED_3:
            out.append(b)
    return out


if __name__ == "__main__":
    survivors = consistent()
    total = len(list(product(*AXES.values())))
    print("%d of %d selected model combinations fit runs 2-3 and the post-failure snapshot "
          "(consistency only; run 1 not modelled):" % (len(survivors), total))
    for b in survivors:
        print("  " + ", ".join("%s=%s" % kv for kv in b.items()))
