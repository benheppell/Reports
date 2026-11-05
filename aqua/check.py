"""Render every page the run just built in headless Chromium and fail on a broken one.

Two pages in this estate have gone live blank (one from an unclosed script tag), so nothing is
committed until each new page loads with no console or page errors and has visible content.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["dashboard.html", "deep-dive.html", "ads.html", "trends.html", "covers.html"]


def pages_from_log() -> list[Path]:
    log = json.loads((ROOT / "run-log.json").read_text())
    out = [ROOT / "index.html"]
    for r in log["results"].values():
        folder = ROOT / r["market"] / log["week"]
        out += [folder / p for p in PAGES if (folder / p).exists()]
        out.append(ROOT / r["market"] / "index.html")
    for slug, m in log.get("monthly", {}).items():
        out.append(ROOT / slug / m / "dashboard.html")
    return out


def check(pages: list[Path]) -> list[str]:
    from playwright.sync_api import sync_playwright
    problems = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for path in pages:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errs = []
            page.on("pageerror", lambda e: errs.append(f"page error: {e}"))
            page.on("console", lambda m: errs.append(f"console: {m.text}") if m.type == "error" else None)
            # Fonts and Chart.js come from CDNs; a blocked CDN is not a page fault.
            page.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") and
                       "cdnjs" not in r.request.url else r.continue_())
            page.goto(path.as_uri())
            page.wait_for_timeout(400)
            text = page.inner_text("body").strip()
            if len(text) < 200:
                errs.append("page is nearly empty")
            for sel in ("text=undefined", "text=NaN"):
                if page.locator(sel).count():
                    errs.append(f"shows '{sel[5:]}'")
            errs = [e for e in errs if "net::ERR_FAILED" not in e and "Failed to load resource" not in e]
            if errs:
                problems.append(f"{path.relative_to(ROOT)}: " + "; ".join(errs[:5]))
            page.close()
        browser.close()
    return problems


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    pages = [Path(a).resolve() for a in argv] if argv else pages_from_log()
    probs = check(pages)
    for p in probs:
        print("FAIL", p)
    print(f"checked {len(pages)} pages, {len(probs)} failed")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
