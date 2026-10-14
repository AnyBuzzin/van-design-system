"""Persistent restore journal for temporary parameter edits.

One JSON file per design under ``<queue>/journal/``.  An entry is written
*before* a parameter is changed (state ``pending``), updated after the change
is confirmed (``applied``) and removed only after the restored value has been
read back and the restore measurement passed.  A ``pending`` or
``restore_unverified`` entry left behind after a crash is an uncertain state
that blocks further edits to that parameter until a human resolves it.
"""

from __future__ import annotations

import os
import re
from typing import Dict, Optional

from .queue import atomic_write_json, read_json, utc_now


class JournalError(RuntimeError):
    pass


def _fname(design_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", design_id)[:150] + ".json"


class RestoreJournal:
    def __init__(self, folder: str, design_id: str):
        self.path = os.path.join(folder, _fname(design_id))
        self.design_id = design_id

    def load(self) -> Dict:
        if os.path.exists(self.path):
            return read_json(self.path)
        return {"design_id": self.design_id, "entries": {}}

    def _save(self, data: Dict) -> None:
        atomic_write_json(self.path, data)

    def entry(self, name: str) -> Optional[Dict]:
        return self.load()["entries"].get(name)

    def begin_edit(self, name: str, original_expression: str, original_value_mm: float, new_expression: str, job_id: str) -> Dict:
        data = self.load()
        if name in data["entries"]:
            e = data["entries"][name]
            raise JournalError("%s already has an unrestored edit (state %s, original %r, job %s); restore it first"
                               % (name, e.get("state"), e.get("original_expression"), e.get("job_id")))
        data["entries"][name] = {"state": "pending", "original_expression": original_expression,
                                 "original_value_mm": original_value_mm, "new_expression": new_expression,
                                 "job_id": job_id, "utc": utc_now()}
        self._save(data)
        return data["entries"][name]

    def mark(self, name: str, state: str, **info) -> None:
        data = self.load()
        if name not in data["entries"]:
            raise JournalError("no journal entry for %s" % name)
        data["entries"][name].update(info, state=state, utc=utc_now())
        self._save(data)

    def clear(self, name: str) -> None:
        data = self.load()
        data["entries"].pop(name, None)
        self._save(data)

    def uncertain(self) -> Dict:
        return {k: v for k, v in self.load()["entries"].items() if v.get("state") != "applied"}
