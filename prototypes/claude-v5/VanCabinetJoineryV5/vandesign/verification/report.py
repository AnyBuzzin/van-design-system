"""Check / ValidationReport.  Unavailable evidence is UNKNOWN, never PASS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"


@dataclass(frozen=True)
class Check:
    check_id: str
    status: str
    observed: Optional[float] = None
    expected: Optional[float] = None
    tolerance: Optional[float] = None
    unit: str = ""
    object_ids: Tuple[str, ...] = ()
    note: str = ""
    limit_min: Optional[float] = None   # optional range metadata (G3 profile checks)
    limit_max: Optional[float] = None

    def line(self) -> str:
        parts = ["  %-7s %s" % (self.status, self.check_id)]
        if self.observed is not None:
            parts.append(": %.4f%s" % (self.observed, " " + self.unit if self.unit else ""))
            if self.expected is not None:
                parts.append(" (expected %.4f)" % self.expected)
        if self.note:
            parts.append("  [%s]" % self.note)
        return "".join(parts)

    def to_dict(self) -> Dict:
        d = {
            "check_id": self.check_id, "status": self.status, "observed": self.observed,
            "expected": self.expected, "tolerance": self.tolerance, "unit": self.unit,
            "object_ids": list(self.object_ids), "note": self.note,
        }
        # Emitted only when set so the original check layout is unchanged.
        if self.limit_min is not None:
            d["limit_min"] = self.limit_min
        if self.limit_max is not None:
            d["limit_max"] = self.limit_max
        return d


@dataclass
class ValidationReport:
    checks: List[Check] = field(default_factory=list)
    diagnostics: List[str] = field(default_factory=list)

    def add(self, check: Check) -> None:
        self.checks.append(check)

    def counts(self) -> Dict[str, int]:
        c = {PASS: 0, FAIL: 0, UNKNOWN: 0}
        for ch in self.checks:
            c[ch.status] += 1
        return c

    @property
    def verdict(self) -> str:
        c = self.counts()
        if c[FAIL]:
            return FAIL
        if c[UNKNOWN] or not self.checks:
            return UNKNOWN
        return PASS

    def headline(self) -> str:
        c = self.counts()
        if self.verdict == PASS:
            return "RESULT: PASS - all %d checks passed" % c[PASS]
        if self.verdict == FAIL:
            return "RESULT: FAIL - %d failed, %d unknown, %d passed" % (c[FAIL], c[UNKNOWN], c[PASS])
        return "RESULT: UNKNOWN - %d check(s) could not be evaluated (NOT releasable)" % c[UNKNOWN]

    def text(self, only_problems: bool = False) -> str:
        lines = []
        for ch in self.checks:
            if only_problems and ch.status == PASS:
                continue
            lines.append(ch.line())
        lines.append("")
        lines.append(self.headline())
        for d in self.diagnostics:
            lines.append("diagnostic: " + d)
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        return {"verdict": self.verdict, "counts": self.counts(),
                "checks": [c.to_dict() for c in self.checks], "diagnostics": list(self.diagnostics)}
