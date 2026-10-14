"""Capture the C0 golden fixtures from the PRE-G3 pinned source.

Usage (run once, at the pinned commit, with a clean tree):
    python tools/capture_g2_golden.py <pinned-git-sha>

Writes tests/fixtures/g2_golden.json and tests/fixtures/protected_sources.json.
Never re-run this after G3 code changes to "fix" a failing golden test.
"""

import json
import os
import platform
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.join(os.path.dirname(HERE), "tests")
sys.path.insert(0, TESTS)

import g2_snapshot  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sha = sys.argv[1]
    out = os.path.join(TESTS, "fixtures")
    os.makedirs(out, exist_ok=True)
    header = {"captured_from_git_sha": sha, "python": platform.python_version(),
              "note": "Frozen from pre-G3 source. Do not regenerate to make a test pass."}
    golden = {"header": header, "combos": g2_snapshot.all_combo_snapshots()}
    protected = {"header": header, **g2_snapshot.protected_manifest()}
    for name, data in (("g2_golden.json", golden), ("protected_sources.json", protected)):
        with open(os.path.join(out, name), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("wrote", os.path.join(out, name))


if __name__ == "__main__":
    main()
