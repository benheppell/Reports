"""The Monday run: pull, build, render, update the manifest and hub. No laptop, no hand edits.

    python -m aqua.run                       # last completed week, every market
    python -m aqua.run --week 2026-10-26     # a specific Monday
    python -m aqua.run --markets london,hk   # some markets
    python -m aqua.run --from-facts          # re-render from saved _facts.json, no source calls
    python -m aqua.run --replay CACHE_DIR    # use recorded GoMarble responses only (tests)

Exit status is non-zero if any market failed; a failed market is left untouched rather than
half-written, and the run log says why.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib
from datetime import date, datetime, timezone
from pathlib import Path

from . import collect as collect_mod
from .builders import monthly, weekly
from .builders.common import Ctx
from .dates import EN_DASH, MONTHS_LONG, Week, fy_week_no, last_completed_monday

ROOT = Path(__file__).resolve().parent.parent
CFG = Path(__file__).resolve().parent / "config"
TOOLS = ROOT / "_tools"

GENERATORS = {  # report -> (payload file, generator, output page)
    "dashboard": ("_dashboard_payload.json", "dashboard_gen.py", "dashboard.html"),
    "deepdive": ("_deepdive_payload.json", "deepdive_gen.py", "deep-dive.html"),
    "ads": ("_ads_payload.json", "snapshot_gen.py", "ads.html"),
    "trends": ("_trends_payload.json", "trends_html.py", "trends.html"),
    "covers": ("_covers_payload.json", "covers_gen.py", "covers.html"),
}
BUILDERS = {"dashboard": weekly.dashboard, "deepdive": weekly.deepdive, "ads": weekly.ads,
            "trends": weekly.trends, "covers": weekly.covers}


def load_config():
    cfg = tomllib.loads((CFG / "markets.toml").read_text())
    targets = tomllib.loads((CFG / "targets.toml").read_text())
    overrides = tomllib.loads((CFG / "overrides.toml").read_text())
    return cfg, targets, overrides


def render(report: str, payload_path: Path, out: Path, market_name: str) -> None:
    _, gen, _ = GENERATORS[report]
    args = [sys.executable, str(TOOLS / gen)]
    args += [market_name, str(payload_path), str(out)] if report == "trends" else [str(payload_path), str(out)]
    subprocess.run(args, check=True, cwd=ROOT)
    if report == "trends":  # house style: the template emits one em dash
        out.write_text(out.read_text().replace("&mdash;", ":").replace("—", ":"))


def run_market(market, defaults, week: Week, targets, overrides, gm, sr, from_facts: bool, today: date) -> dict:
    folder = ROOT / market["slug"] / week.folder
    facts_path = folder / "_facts.json"
    if from_facts:
        facts = json.loads(facts_path.read_text())
    else:
        facts = collect_mod.collect_market(market, defaults, week, gm, sr)
    # Guardrail: a market whose core pulls failed is not written at all.
    core_fail = [e for e in facts["errors"] if e.split(": ")[0].split()[-1] in ("ga4_book", "web")]
    if core_fail:
        return {"market": market["slug"], "status": "skipped", "errors": facts["errors"]}
    folder.mkdir(parents=True, exist_ok=True)
    facts_path.write_text(json.dumps(facts, indent=1, default=str))
    ctx = Ctx(market, defaults, facts, week, targets, overrides, today)
    built, errors = [], list(facts["errors"])
    for report in market["reports"]:
        if report == "monthly":
            continue
        try:
            payload, bad = clean(BUILDERS[report](ctx))
            errors += [f"{report}: not a number at {b}, shown as n/a" for b in bad]
            pf, _, page = GENERATORS[report]
            (folder / pf).write_text(json.dumps(payload, indent=1, ensure_ascii=False, allow_nan=False))
            render(report, folder / pf, folder / page, market["name"])
            built.append(report)
        except Exception as e:
            errors.append(f"{report}: {e}")
    return {"market": market["slug"], "status": "ok" if not errors else "partial", "built": built, "errors": errors}


def clean(obj, path="$"):
    """Replace NaN and infinity with None (shown as n/a) and report where they were."""
    import math
    bad = []
    if isinstance(obj, float) and not math.isfinite(obj):
        return None, [path]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out[k], b = clean(v, f"{path}.{k}")
            bad += b
        return out, bad
    if isinstance(obj, list):
        out = []
        for i, v in enumerate(obj):
            x, b = clean(v, f"{path}[{i}]")
            out.append(x)
            bad += b
        return out, bad
    return obj, bad


def run_monthly(market, defaults, targets, gm, y, m, today) -> dict:
    folder = ROOT / market["slug"] / f"m{y}-{m:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    facts = monthly.collect(gm, market, defaults, y, m)
    (folder / "_facts.json").write_text(json.dumps(facts, indent=1))
    p = monthly.build(market, facts, targets, y, m, today)
    (folder / "_monthly_payload.json").write_text(json.dumps(p, indent=1, ensure_ascii=False))
    subprocess.run([sys.executable, str(TOOLS / "monthly_gen.py"), str(folder / "_monthly_payload.json"),
                    str(folder / "dashboard.html")], check=True, cwd=ROOT)
    return {"market": market["slug"], "monthly": f"m{y}-{m:02d}"}


# ------------------------------------------------------------------ manifest
def update_manifest(cfg, week: Week, results: dict, monthly_done: dict, today: date) -> None:
    path = ROOT / "manifest.json"
    man = json.loads(path.read_text())
    by_slug = {mk["slug"]: mk for mk in man["markets"]}
    for market in cfg["market"]:
        r = results.get(market["slug"])
        if not r or not r.get("built"):
            continue
        mk = by_slug[market["slug"]]
        n = fy_week_no(week.monday, market["fy_start_month"])
        built = set(r["built"])
        entry = {"dates": f"W{n} · {week.label()}", "folder": week.folder}
        if "dashboard" in built:
            entry.update({"deepdive": "deepdive" in built, "ads": "ads" in built, "covers": "covers" in built})
        else:
            entry.update({"ads": "ads" in built, "dash": False})
        mk["weekly"] = [entry] + [w for w in mk.get("weekly", []) if w["folder"] != week.folder]
        if "trends" in built:
            mk["trends"] = [{"dates": week.label(), "folder": week.folder}] + \
                           [t for t in mk.get("trends", []) if t["folder"] != week.folder]
        if market["slug"] in monthly_done:
            f = monthly_done[market["slug"]]
            y, m = int(f[1:5]), int(f[6:8])
            mk["monthly"] = [{"label": f"{MONTHS_LONG[m - 1]} {y}", "folder": f}] + \
                            [x for x in mk.get("monthly", []) if x["folder"] != f]
    man["generated"] = f"{today.day} {MONTHS_LONG[today.month - 1]} {today.year}"
    path.write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n")
    subprocess.run([sys.executable, "build_hub.py"], check=True, cwd=ROOT)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", help="Monday of the reporting week, YYYY-MM-DD (default: last completed)")
    ap.add_argument("--markets", default="all")
    ap.add_argument("--from-facts", action="store_true")
    ap.add_argument("--replay", help="GoMarble response cache to replay from (no network)")
    ap.add_argument("--record", help="GoMarble response cache to record into")
    ap.add_argument("--no-covers", action="store_true", help="skip the SevenRooms database")
    ap.add_argument("--monthly", choices=["auto", "yes", "no"], default="auto")
    ap.add_argument("--no-manifest", action="store_true")
    a = ap.parse_args(argv)

    today = datetime.now(timezone.utc).date()
    week = Week(date.fromisoformat(a.week)) if a.week else Week(last_completed_monday(today))
    cfg, targets, overrides = load_config()
    markets = [m for m in cfg["market"] if a.markets == "all" or m["slug"] in a.markets.split(",")]

    gm = sr = None
    db_error = None
    if not a.from_facts:
        from .sources.gomarble import GoMarble
        gm = GoMarble(cache_dir=a.replay or a.record, replay_only=bool(a.replay))
        if not a.no_covers and any(m.get("covers_rules") for m in markets):
            from .sources.sevenrooms import SevenRooms
            try:
                sr = SevenRooms()
            except Exception as e:  # covers pages fail; everything else still builds
                db_error = f"SevenRooms database: {e} (host {_db_host()})"
                print(db_error, flush=True)

    results = {}
    for market in markets:
        print(f"== {market['name']} {week.folder}", flush=True)
        try:
            results[market["slug"]] = run_market(market, cfg["defaults"], week, targets, overrides, gm, sr,
                                                 a.from_facts, today)
        except Exception as e:
            results[market["slug"]] = {"market": market["slug"], "status": "failed", "errors": [repr(e)]}
        if db_error and market.get("covers_rules"):
            results[market["slug"]].setdefault("errors", []).insert(0, db_error)
            if results[market["slug"]].get("status") == "ok":
                results[market["slug"]]["status"] = "partial"
        print(json.dumps(results[market["slug"]], indent=1), flush=True)

    # Monthly: on the first Monday of a month, build the month just completed.
    run_month = a.monthly == "yes" or (a.monthly == "auto" and today.day <= 7 and today.weekday() == 0)
    monthly_done = {}
    if run_month and gm is not None:
        y, m = monthly.prev_month(today.year, today.month)
        for market in markets:
            if "monthly" in market["reports"]:
                try:
                    monthly_done[market["slug"]] = run_monthly(market, cfg["defaults"], targets, gm, y, m, today)["monthly"]
                except Exception as e:
                    results.setdefault(market["slug"], {}).setdefault("errors", []).append(f"monthly: {e}")

    if not a.no_manifest:
        update_manifest(cfg, week, results, monthly_done, today)

    log = {"week": week.folder, "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "results": results, "monthly": monthly_done}
    (ROOT / "run-log.json").write_text(json.dumps(log, indent=1) + "\n")
    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as fh:
        fh.write(summary_md(log))
    return 0 if all(r.get("status") == "ok" for r in results.values()) else 1


def _db_host() -> str:
    """The host part of SUPABASE_DB_URL, for error messages. Never the password."""
    from urllib.parse import urlsplit
    try:
        return urlsplit(os.environ.get("SUPABASE_DB_URL", "")).hostname or "missing"
    except ValueError:
        return "unparseable (check the password for @ # / ? characters)"


def summary_md(log) -> str:
    lines = [f"## Aqua reports {log['week']}", "", "| Market | Status | Built | Problems |", "|---|---|---|---|"]
    for r in log["results"].values():
        probs = "<br>".join(e.replace("|", "/")[:200] for e in r.get("errors", [])) or "none"
        lines.append(f"| {r['market']} | {r.get('status')} | {', '.join(r.get('built', []))} | {probs} |")
    if log["monthly"]:
        lines.append("\nMonthly built: " + ", ".join(f"{k} {v}" for k, v in log["monthly"].items()))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
