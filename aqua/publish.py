"""Netlify build step: copy the site into dist/, leaving out everything that is not a page.

The repo keeps payloads, raw pulls and facts files next to each report so a run can be audited
and re-rendered, but none of them is served. Only what a browser needs is published.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SKIP_DIRS = {".git", ".github", "_tools", "aqua", "dist", "netlify", "node_modules", "tests", "claude", "__pycache__"}
SKIP_SUFFIX = {".py", ".pyc", ".md", ".toml", ".txt", ".sql"}
KEEP_ROOT: set[str] = set()


def keep(rel: Path) -> bool:
    if any(p in SKIP_DIRS or p.startswith(".") for p in rel.parts[:-1]):
        return False
    name = rel.name
    if name.startswith("_") or name.startswith("."):  # _raw*.json, _*_payload.json, _facts.json, _sources
        return False
    if str(rel) in KEEP_ROOT:
        return True
    if rel.suffix == ".json":  # pages never fetch JSON files; they read functions or inline data
        return False
    if rel.suffix in SKIP_SUFFIX:
        return False
    if any(p.startswith("_") for p in rel.parts[:-1]):
        return False
    return True


def main() -> int:
    if DIST.exists():
        shutil.rmtree(DIST)
    n = 0
    for f in ROOT.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(ROOT)
        if rel.parts[0] in SKIP_DIRS or not keep(rel):
            continue
        dst = DIST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)
        n += 1
    print(f"published {n} files to dist/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
