"""Package original job evidence into a ZIP with a SHA-256 manifest.

Files are copied byte-for-byte; the archive is verified against the sources
after writing.  Nothing in the result folders is modified.
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from typing import Dict, Iterable, List, Optional

from .queue import JobQueue, utc_now


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def package(queue: JobQueue, job_ids: Iterable[str], out_zip: str, extra_files: Optional[Dict[str, str]] = None) -> Dict:
    if os.path.exists(out_zip):
        raise FileExistsError("refusing to overwrite %s" % out_zip)
    entries: List[tuple] = []
    for jid in job_ids:
        rdir = queue.result_dir(jid)
        if not os.path.isdir(rdir):
            raise FileNotFoundError("no results for job %s" % jid)
        for base, _dirs, files in os.walk(rdir):
            for f in sorted(files):
                src = os.path.join(base, f)
                entries.append((src, "jobs/%s/%s" % (jid, os.path.relpath(src, rdir).replace(os.sep, "/"))))
        st = queue.p("state", jid + ".json")
        if os.path.exists(st):
            entries.append((st, "jobs/%s/state.json" % jid))
    for arc, src in (extra_files or {}).items():
        entries.append((src, arc))
    manifest = {"created_utc": utc_now(), "files": [{"path": arc, "sha256": sha256_file(src), "bytes": os.path.getsize(src)}
                                                    for src, arc in entries]}
    os.makedirs(os.path.dirname(os.path.abspath(out_zip)), exist_ok=True)
    with zipfile.ZipFile(out_zip, "x", zipfile.ZIP_DEFLATED) as z:
        for src, arc in entries:
            z.write(src, arc)
        z.writestr("MANIFEST.sha256.json", json.dumps(manifest, indent=2))
    with zipfile.ZipFile(out_zip) as z:
        for src, arc in entries:
            if z.read(arc) != open(src, "rb").read():
                raise RuntimeError("archive verification failed for %s" % arc)
    return {"zip": out_zip, "files": len(entries), "sha256": sha256_file(out_zip)}
