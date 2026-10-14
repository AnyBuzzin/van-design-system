"""A simulated CAD backend used to test validation without Fusion.

``SimGeometry`` plays the role of Fusion after the user edits parameters: it
takes base-parameter overrides, derives the 'actual' solids itself, and can be
told to misbehave (including reproducing the original V4 bug where groove cuts
trimmed the shelf).
"""

from core_path import *  # noqa: F401,F403  (sets sys.path)

from vandesign.core.geometry import Box
from vandesign.verification.geometry_source import MeasuredBody


class SimGeometry:
    def __init__(self, assembly, overrides=None, bug_cut_all=False, skip_cuts=False,
                 shelf_dz=0.0, unreadable_params=(), unmeasurable=(), interference="compute",
                 no_containment=False):
        self.assembly = assembly
        self.overrides = dict(overrides or {})
        self.env = assembly.parameters.resolve(self.overrides)
        self.diagnostics = []
        self.bug_cut_all = bug_cut_all
        self.skip_cuts = skip_cuts
        self.shelf_dz = shelf_dz
        self.unreadable = set(unreadable_params)
        self.unmeasurable = set(unmeasurable)
        self.interference = interference
        self.no_containment = no_containment
        self.blank = {p.stable_id: p.box.resolve(self.env) for p in assembly.panels}
        self.cuts = [(o, o.cut.resolve(self.env)) for o in assembly.operations]

    def _cuts_for(self, pid):
        if self.skip_cuts:
            return []
        out = []
        for o, c in self.cuts:
            if o.target_panel_id == pid or (self.bug_cut_all and self.blank[pid].intersection(c)):
                out.append(c)
        return out

    def _effective(self, pid):
        """(bbox, volume) after the applied cuts."""
        box = self.blank[pid]
        cuts = self._cuts_for(pid)
        vol = box.volume - sum(box.overlap_volume(c) for c in cuts)
        lo, hi = list(box.lo), list(box.hi)
        for c in cuts:
            i = box.intersection(c)
            if i and abs(i.size[1] - box.size[1]) < 1e-9 and abs(i.size[2] - box.size[2]) < 1e-9:
                if abs(i.lo[0] - box.lo[0]) < 1e-9:
                    lo[0] = i.hi[0]
                elif abs(i.hi[0] - box.hi[0]) < 1e-9:
                    hi[0] = i.lo[0]
        return Box(tuple(lo), tuple(hi)), vol

    def parameter_value(self, name):
        if name in self.unreadable:
            return None
        return self.env.get(name)

    def body(self, pid):
        if pid in self.unmeasurable:
            return None
        box, vol = self._effective(pid)
        if pid.startswith("panel.shelf") and self.shelf_dz:
            box = Box((box.lo[0], box.lo[1], box.lo[2] + self.shelf_dz), (box.hi[0], box.hi[1], box.hi[2] + self.shelf_dz))
        return MeasuredBody(box, vol)

    def point_in_material(self, pid, p):
        if self.no_containment:
            return None
        if not self.blank[pid].contains_point(p):
            return False
        return not any(c.contains_point(p) for c in self._cuts_for(pid))

    def interference_count(self, pids):
        if self.interference != "compute":
            return self.interference
        n = 0
        for i, a in enumerate(pids):
            for b in pids[i + 1:]:
                o = self.blank[a].intersection(self.blank[b])
                if not o:
                    continue
                free = o.volume - sum(o.overlap_volume(c) for c in self._cuts_for(a) + self._cuts_for(b))
                if free > 1e-6:
                    n += 1
        return n
