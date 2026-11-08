"""Morning job: rewrite public.booking_pipeline for the five most recently completed weeks.

Method: claude/booking-pipeline-runbook.md. Per venue and ISO week, bookings and covers created,
split by the week they are for (this week, next week, beyond), against the matched week last year
(Monday minus 364 days); plus digital spend, sessions, website conversion and brand searches.

    python -m aqua.jobs.booking_pipeline                 # check only: compare with the table
    python -m aqua.jobs.booking_pipeline --write         # upsert
    python -m aqua.jobs.booking_pipeline --markets london,hk

Guardrails (runbook): never write a zero for a failed pull, write null; a market whose pull
fails is left untouched; in a settled week, a venue whose total bookings created (all three
service windows, this year) moves more than 5% is written but named, and fails the run so
GitHub emails. Moves in single windows or covers are ordinary cancellations: listed only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..dates import Week, last_completed_monday
from ..sources import meta as meta_src
from ..sources.ga4 import _and, _path_filter, _run
from ..sources.gomarble import GoMarble
from ..sources.google_ads import GoogleAds
from ..sources.sevenrooms import SevenRooms

CFG = Path(__file__).resolve().parent.parent / "config"
N_WEEKS = 5
GSC_DELAY_DAYS = 3

# Channel classification on COALESCE(booking_source,''), runbook "Channels counted in the total".
CH_CASE = """CASE
  WHEN src = 'Booking Widget' OR src ILIKE '%%landing page%%' OR src IN ('Nav CTA','Hero CTA','Menu Page','Website',
       'Popup','EDM','What''s On') OR src ILIKE 'PPC%%' THEN 'web'
  WHEN src = 'Google Reserve Integration' THEN 'gr'
  WHEN {ot} THEN 'ot'
  WHEN src ILIKE 'resy%%' THEN 'rs'
  ELSE 'x' END"""
OT_DEFAULT = ("src ILIKE '%%open table%%' OR src ILIKE '%%opentable%%' OR src = 'OT Guestcenter' OR src = 'OT' "
              "OR src ILIKE '%%otgc%%'")
OT_HK = "src ILIKE '%%openrice%%'"  # HK's third party; no HK venue counts it

SR_SQL = """
WITH c AS (
  SELECT v.name AS sr_venue, res.covers AS cov, res.service_date AS sd, COALESCE(res.booking_source,'') AS src,
         date_trunc('week', (((res.sr_created_at AT TIME ZONE %(tz)s)::date)::timestamp))::date AS cw
  FROM reservations res JOIN venues v ON v.id = res.venue_id
  WHERE v.name = ANY(%(venues)s)
    AND res.is_deleted = false
    AND COALESCE(res.status_simple,'') <> 'Canceled'
    AND COALESCE(res.raw->>'venue_seating_area_name','') NOT ILIKE '%%bar%%'
    AND res.sr_created_at >= (%(start)s::timestamp AT TIME ZONE %(tz)s)
    AND res.sr_created_at <  (%(end)s::timestamp AT TIME ZONE %(tz)s)),
k AS (
  SELECT sr_venue, cw, cov, {case} AS ch,
         CASE WHEN sd >= cw AND sd <= cw + 6 THEN 1
              WHEN sd >= cw + 7 AND sd <= cw + 13 THEN 2
              WHEN sd >= cw + 14 AND sd <= cw + 3650 THEN 3
              ELSE 0 END AS win
  FROM c)
SELECT sr_venue, cw, ch, win, COUNT(*)::int, COALESCE(SUM(cov),0)::int FROM k WHERE ch <> 'x'
GROUP BY sr_venue, cw, ch, win"""

CHANNELS = {"wg": {"web", "gr"}, "wg+ot": {"web", "gr", "ot"}, "wg+ot+rs": {"web", "gr", "ot", "rs"}}


def load():
    markets = {m["slug"]: m for m in tomllib.loads((CFG / "markets.toml").read_text())["market"]}
    return markets, tomllib.loads((CFG / "pipeline.toml").read_text())


# ------------------------------------------------------------------ SevenRooms
def sevenrooms(sr: SevenRooms, market: dict, weeks: list[Week]) -> dict:
    """{venue: {monday: {ch: {win: (bookings, covers)}}}} for one contiguous range of weeks."""
    names = sorted({n for v in market["venue"] for n in v["sr"]})
    case = CH_CASE.format(ot=OT_HK if market["slug"] == "hk" else OT_DEFAULT)
    rows = sr.query(SR_SQL.format(case=case), {
        "tz": market["tz"], "venues": names, "start": weeks[0].monday.isoformat(),
        "end": (weeks[-1].sunday + timedelta(days=1)).isoformat()})
    out: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for sr_venue, cw, ch, win, n, cov in rows:
        for v in market["venue"]:
            if sr_venue not in v["sr"]:
                continue
            start = date.fromisoformat(v["sr_from"]) if v.get("sr_from") else None
            if start and cw < start - timedelta(days=start.weekday()):  # e.g. Vista before it became Canton
                continue
            b0, c0 = out[v["name"]][cw][ch].get(win, (0, 0))
            out[v["name"]][cw][ch][win] = (b0 + n, c0 + cov)
    return out


def sr_fields(cells: dict, channels: str, suffix: str) -> dict:
    keep = CHANNELS[channels]
    f = {}
    for w in (1, 2, 3):
        f[f"b{w}_{suffix}"] = sum(cells.get(ch, {}).get(w, (0, 0))[0] for ch in keep)
        f[f"c{w}_{suffix}"] = sum(cells.get(ch, {}).get(w, (0, 0))[1] for ch in keep)
    f[f"late_{suffix}"] = sum(cells.get(ch, {}).get(0, (0, 0))[0] for ch in keep)
    f[f"wgb_{suffix}"] = sum(cells.get(ch, {}).get(w, (0, 0))[0] for ch in ("web", "gr") for w in (1, 2, 3))
    f[f"web_{suffix}"] = sum(cells.get("web", {}).get(w, (0, 0))[0] for w in (1, 2, 3))
    return f


# ------------------------------------------------------------------ digital
def sessions(gm: GoMarble, v: dict, weeks: list[Week]) -> dict[date, int]:
    """Sum of daily GA4 sessions per week, as the table has always held."""
    def pull(flt) -> dict[date, int]:
        acc: dict[date, int] = defaultdict(int)
        for prop in v["ga4"]:
            for r in _run(gm, prop, weeks[0].monday, weeks[-1].sunday, ["sessions"], ["date"], flt):
                d = datetime.strptime(r["date"], "%Y%m%d").date()
                acc[d - timedelta(days=d.weekday())] += int(r["sessions"])
        return acc

    if v.get("ga4_path_not"):
        # The remainder site of a split property (Shiro Pacific Place) is the property's total
        # minus the other site's sessions; a "not this path" filter would double count sessions
        # that touch both.
        total, other = pull(None), pull(_and(_path_filter(v["ga4_path_not"], None)))
        return defaultdict(int, {k: total[k] - other.get(k, 0) for k in total})
    return pull(_and(_path_filter(v.get("ga4_path"), None)))


def brand(gm: GoMarble, sites, regex: str, weeks: list[Week]) -> dict[date, int]:
    out: dict[date, int] = defaultdict(int)
    for site in [sites] if isinstance(sites, str) else sites:
        res = gm.call("gsc_get_advanced_search_analytics", {
            "site_url": site, "start_date": weeks[0].monday.isoformat(), "end_date": weeks[-1].sunday.isoformat(),
            "dimensions": ["date"], "row_limit": 1000,
            "dimension_filter_groups": [{"filters": [{"dimension": "query", "operator": "includingRegex",
                                                      "expression": regex}]}]})
        if res.get("error") or "rows" not in res:
            raise RuntimeError(f"Search Console {site}: {str(res.get('error', res))[:200]}")
        for r in res["rows"]:
            d = date.fromisoformat(r["keys"][0] if "keys" in r else r["date"])
            out[d - timedelta(days=d.weekday())] += int(r["impressions"])
    return out


def spend(gm: GoMarble, gads: GoogleAds, v: dict, weeks: list[Week]) -> dict[date, float]:
    out: dict[date, float] = defaultdict(float)
    for f, x in meta_src.weekly(gm, v, weeks, "schedule_total").items():
        out[date.fromisoformat(f[1:])] += x["spend"]
    if not v.get("google_excluded"):
        for f, x in gads.weekly_spend(v, weeks).items():
            out[date.fromisoformat(f[1:])] += x
    return out


# ------------------------------------------------------------------ build
def build_market(market: dict, pcfg: dict, weeks: list[Week], gm, gads, sr, today: date) -> tuple[list[dict], list[str]]:
    ly = [w.yoy for w in weeks]
    errors: list[str] = []
    sr_ty, sr_ly = sevenrooms(sr, market, weeks), sevenrooms(sr, market, ly)
    rows = []
    for v in market["venue"]:
        p = pcfg[v["name"]]

        def get(label, fn, *a):
            try:
                return fn(*a)
            except Exception as e:  # null and named, never zero
                errors.append(f"{v['name']} {label}: {e}")
                return None

        sess = {k: get(f"sessions {k}", sessions, gm, v, ws) for k, ws in (("ty", weeks), ("ly", ly))}
        spd = {k: None if p.get("spend_null") else get(f"spend {k}", spend, gm, gads, v, ws)
               for k, ws in (("ty", weeks), ("ly", ly))}
        brd = {k: get(f"brand {k}", brand, gm, p["brand_site"], p["brand_regex"], ws) if p.get("brand_site") else None
               for k, ws in (("ty", weeks), ("ly", ly))}
        for w in weeks:
            lw = w.yoy
            notes = dict(p.get("notes", {}))
            if (today - w.sunday).days < GSC_DELAY_DAYS + 1 and p.get("brand_site"):
                notes["brand"] = "; ".join(x for x in (notes.get("brand"), "the last days are inside the Search Console "
                                                       "reporting delay, may restate upward") if x)
            r = {"market": market["slug"], "venue": v["name"], "week_key": w.folder, "monday": w.monday,
                 "ly_monday": lw.monday, "channels": p["channels"], "not_comparable": bool(p.get("ly_null") or p.get("ly_null_from") or v.get("not_comparable")),
                 "venue_order": p["order"],
                 **sr_fields(sr_ty.get(v["name"], {}).get(w.monday, {}), p["channels"], "ty"),
                 **sr_fields(sr_ly.get(v["name"], {}).get(lw.monday, {}), p["channels"], "ly"),
                 "spend_ty": None if spd["ty"] is None else round(spd["ty"].get(w.monday, 0.0), 2),
                 "spend_ly": None if spd["ly"] is None or p.get("spend_ly_null") else round(spd["ly"].get(lw.monday, 0.0), 2),
                 "sess_ty": None if sess["ty"] is None else sess["ty"].get(w.monday, 0),
                 "sess_ly": None if sess["ly"] is None else sess["ly"].get(lw.monday, 0),
                 "brand_ty": None if brd["ty"] is None else brd["ty"].get(w.monday, 0),
                 "brand_ly": None if brd["ly"] is None or p.get("brand_ly_null") else brd["ly"].get(lw.monday, 0),
                 "notes": json.dumps(notes)}
            if p.get("ly_null") or (p.get("ly_null_from") and lw.monday >= date.fromisoformat(p["ly_null_from"])):
                for k in list(r):
                    if k.endswith("_ly"):
                        r[k] = None
            rows.append(r)
    return rows, errors


COLS = ["market", "venue", "week_key", "monday", "ly_monday", "channels", "not_comparable", "venue_order",
        "b1_ty", "c1_ty", "b2_ty", "c2_ty", "b3_ty", "c3_ty", "b1_ly", "c1_ly", "b2_ly", "c2_ly", "b3_ly", "c3_ly",
        "wgb_ty", "wgb_ly", "web_ty", "web_ly", "late_ty", "late_ly", "spend_ty", "spend_ly", "sess_ty", "sess_ly",
        "brand_ty", "brand_ly", "notes"]
NUM = [c for c in COLS[8:-1]]


def compare(sr: SevenRooms, rows: list[dict], weeks: list[Week]) -> tuple[list[str], list[str]]:
    """Differences against the table, and venues whose total bookings moved over 5% in a settled
    week (all but the latest)."""
    m = rows[0]["market"]
    cur = sr.query(f"select venue, week_key, {', '.join(NUM)} from booking_pipeline where market = %s "
                   "and week_key = any(%s)", (m, [w.folder for w in weeks]))
    old = {(r[0], r[1]): dict(zip(NUM, r[2:])) for r in cur}
    diffs, moves = [], []
    for r in rows:
        o = old.get((r["venue"], r["week_key"]))
        if not o:
            diffs.append(f"{r['venue']} {r['week_key']}: new row")
            continue
        for c in NUM:
            a, b = o[c], r[c]
            a = float(a) if a is not None else None
            if a != (float(b) if b is not None else None):
                diffs.append(f"{r['venue']} {r['week_key']} {c}: table {a} -> new {b}")
        if r["week_key"] != weeks[-1].folder:
            tb = ("b1_ty", "b2_ty", "b3_ty")
            if all(o[c] is not None and r[c] is not None for c in tb):
                a, b = sum(float(o[c]) for c in tb), sum(float(r[c]) for c in tb)
                if a and abs(b - a) / a > 0.05:
                    moves.append(f"{r['venue']} {r['week_key']} bookings: {a:g} -> {b:g}")
    return diffs, moves


def write(sr: SevenRooms, rows: list[dict]) -> None:
    ph = ", ".join(["%s"] * len(COLS))
    upd = ", ".join(f"{c} = excluded.{c}" for c in COLS[3:])
    sql = (f"insert into booking_pipeline ({', '.join(COLS)}) values ({ph}) "
           f"on conflict (market, venue, week_key) do update set {upd}")
    with sr.conn.cursor() as cur:
        cur.executemany(sql, [[r[c] for c in COLS] for r in rows])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--markets", default="london,hk,usa,dubai,paris")
    ap.add_argument("--latest", help="Monday of the latest completed week (default: computed)")
    a = ap.parse_args(argv)
    today = datetime.now(timezone.utc).date()
    latest = Week(date.fromisoformat(a.latest) if a.latest else last_completed_monday(today))
    weeks = latest.back(N_WEEKS)
    markets, pcfg = load()
    gm, sr = GoMarble(), SevenRooms()
    gads = GoogleAds(gm)
    summary, status = [], 0
    for slug in a.markets.split(","):
        market = markets[slug]
        try:
            rows, errors = build_market(market, pcfg[slug], weeks, gm, gads, sr, today)
        except Exception as e:
            summary.append(f"{slug}: FAILED, left untouched: {e}")
            status = 1
            continue
        diffs, moves = compare(sr, rows, weeks)
        print(f"== {slug}: {len(rows)} rows, {len(diffs)} values differ from the table, {len(moves)} settled moves >5%")
        for d in diffs[:60]:
            print("  ", d)
        for e in errors:
            print("  PULL FAILED", e)
        verdict = "checked"
        if errors:
            verdict, status = "skipped: a pull failed, table left as it was", 1
        elif a.write:
            write(sr, rows)
            verdict = "written"
            if moves:
                verdict, status = "written, but a settled week's bookings moved more than 5%", 1
        summary.append(f"{slug}: {verdict}; {len(diffs)} differences, {len(moves)} settled moves" +
                       "".join(f"\n    {m}" for m in moves[:10]) + "".join(f"\n    {e}" for e in errors[:10]))
    report = f"### Booking pipeline {weeks[0].folder}..{weeks[-1].folder}\n```\n" + "\n".join(summary) + "\n```\n"
    print(report)
    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as fh:
        fh.write(report)
    return status


if __name__ == "__main__":
    sys.exit(main())
