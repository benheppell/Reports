"""Morning job: the ads monitor's figures, one payload per market, into public.ads_monitor.

Per venue, the 13 most recent completed ISO weeks and the same ISO weeks last year (Monday
minus 364 days):
  meta    booking campaigns (Leads, Sales, Conversions objectives):
          [spend, impressions, reach, frequency, link clicks, bookings]
  other   every other Meta campaign: [spend, impressions, link clicks]
  google  this year: [spend, impressions, clicks, bookings, brand spend, brand clicks,
          search impression share, share lost to budget, share lost to rank]
          last year: [spend, impressions, clicks] (2025 booking conversions are not comparable)
  sr      SevenRooms website and Google Reserve bookings created that week: [web, google reserve]

Rules come from aqua/config: shared ad accounts make one row (Shiro HK), campaign-restricted
accounts count only their own campaigns (The Canton Library), an excluded Google account keeps
its spend but reports no bookings, Dubai's Google cost is converted once, and Paris counts
its custom pixel event. A market whose pull fails keeps yesterday's payload.

    python -m aqua.jobs.ads_monitor                   # all markets, print a summary
    python -m aqua.jobs.ads_monitor --write           # and upsert public.ads_monitor
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from ..dates import Week, last_completed_monday
from ..sources.gomarble import GoMarble
from ..sources.google_ads import is_booking_action
from ..sources.sevenrooms import SevenRooms
from .booking_pipeline import sevenrooms

CFG = Path(__file__).resolve().parent.parent / "config"
N_WEEKS = 13
BOOKING_OBJECTIVES = ["OUTCOME_LEADS", "OUTCOME_SALES", "CONVERSIONS", "LEAD_GENERATION"]
META_TOOL = "facebook_get_adaccount_insights"


# ------------------------------------------------------------------ Meta
def _meta_rows(gm, act, weeks, flt, fields):
    args = {"act_id": act, "fields": fields, "level": "account", "time_increment": 7,
            "time_range": json.dumps({"since": weeks[0].monday.isoformat(), "until": weeks[-1].sunday.isoformat()}),
            "filtering": flt}
    res = gm.call(META_TOOL, args)
    if (res.get("_gomarble_meta_insights_data_quality") or {}).get("paging_next_present"):
        raise RuntimeError(f"Meta {act}: incomplete response")
    if "data" not in res:
        raise RuntimeError(f"Meta {act}: {str(res)[:200]}")
    return {r["date_start"]: r for r in res["data"]}


def _event(row, event):
    for key in ("conversions", "actions"):
        for a in row.get(key) or []:
            if a.get("action_type") == event:
                return float(a["value"])
    return 0.0


def meta_series(gm, venue, weeks):
    """(booking rows, other rows) aligned to weeks; a week with no delivery is a real zero."""
    event = venue.get("meta_event", "schedule_total")
    fields = ["spend", "impressions", "reach", "frequency", "inline_link_clicks", "conversions"]
    if event != "schedule_total":
        fields.append("actions")
    book_ids = venue.get("meta_book_campaigns")
    all_ids = venue.get("meta_campaigns")
    if all_ids:  # campaign-restricted account: booking = its booking campaigns, other = the rest of its own
        bflt = [{"field": "campaign.id", "operator": "IN", "value": book_ids or all_ids}]
        rest = [c for c in all_ids if c not in (book_ids or all_ids)]
        oflt = [{"field": "campaign.id", "operator": "IN", "value": rest}] if rest else None
    else:
        bflt = [{"field": "campaign.objective", "operator": "IN", "value": BOOKING_OBJECTIVES}]
        oflt = [{"field": "campaign.objective", "operator": "NOT_IN", "value": BOOKING_OBJECTIVES}]
    book = [[0.0, 0, 0, 0.0, 0, 0.0] for _ in weeks]
    other = [[0.0, 0, 0] for _ in weeks]
    for act in venue["meta"]:
        rows = _meta_rows(gm, act, weeks, bflt, fields)
        orows = _meta_rows(gm, act, weeks, oflt, ["spend", "impressions", "inline_link_clicks"]) if oflt else {}
        for i, w in enumerate(weeks):
            r = rows.get(w.monday.isoformat())
            if r:
                b = book[i]
                b[0] += float(r.get("spend") or 0)
                b[1] += int(r.get("impressions") or 0)
                b[2] += int(r.get("reach") or 0)  # separate accounts reach separate audiences
                b[4] += int(r.get("inline_link_clicks") or 0)
                b[5] += _event(r, event)
            o = orows.get(w.monday.isoformat())
            if o:
                other[i][0] += float(o.get("spend") or 0)
                other[i][1] += int(o.get("impressions") or 0)
                other[i][2] += int(o.get("inline_link_clicks") or 0)
    for b in book:
        b[0] = round(b[0], 2)
        b[3] = round(b[1] / b[2], 2) if b[2] else 0.0
    for o in other:
        o[0] = round(o[0], 2)
    return book, other


# ------------------------------------------------------------------ Google
def _gaql(gm, venue, q):
    args = {"customer_id": venue["google"], "query": q}
    if venue.get("google_mgr"):
        args["manager_id"] = venue["google_mgr"]
    res = gm.call("google_ads_run_gaql", args)
    if res.get("response_complete") is False or "results" not in res:
        raise RuntimeError(f"Google Ads {venue['google']}: {str(res)[:200]}")
    return res["results"]


def _cost(m):
    return float(m["cost"]) if "cost" in m else float(m.get("costMicros", 0) or 0) / 1e6


def google_series(gm, venue, weeks, this_year: bool):
    start, end = weeks[0].monday, weeks[-1].sunday
    fx = venue.get("google_fx", 1.0)
    idx = {w.monday.isoformat(): i for i, w in enumerate(weeks)}
    if not this_year:
        out = [[0.0, 0, 0] for _ in weeks]
        for r in _gaql(gm, venue, "SELECT segments.week, metrics.cost_micros, metrics.impressions, metrics.clicks "
                                  f"FROM customer WHERE segments.date BETWEEN '{start}' AND '{end}'"):
            i = idx.get(r["segments"]["week"])
            if i is not None:
                m = r["metrics"]
                out[i] = [round(_cost(m) * fx, 2), int(m.get("impressions", 0)), int(m.get("clicks", 0))]
        return out
    out = [[0.0, 0, 0, 0.0, 0.0, 0, None, None, None] for _ in weeks]
    for r in _gaql(gm, venue, "SELECT segments.week, campaign.name, metrics.cost_micros, metrics.impressions, metrics.clicks "
                              f"FROM campaign WHERE segments.date BETWEEN '{start}' AND '{end}' AND metrics.impressions > 0"):
        i = idx.get(r["segments"]["week"])
        if i is None:
            continue
        m, o = r["metrics"], out[i]
        cost = _cost(m) * fx
        o[0] += cost
        o[1] += int(m.get("impressions", 0))
        o[2] += int(m.get("clicks", 0))
        if "brand" in r["campaign"].get("name", "").lower():
            o[4] += cost
            o[5] += int(m.get("clicks", 0))
    rule = venue.get("google_actions")
    for r in _gaql(gm, venue, "SELECT segments.week, segments.conversion_action_name, metrics.conversions "
                              f"FROM customer WHERE segments.date BETWEEN '{start}' AND '{end}'"):
        i = idx.get(r["segments"]["week"])
        if i is not None and is_booking_action(r["segments"]["conversionActionName"], rule):
            out[i][3] += float(r["metrics"].get("conversions", 0) or 0)
    elig = defaultdict(float); shown = defaultdict(float); lb = defaultdict(float); lr = defaultdict(float)
    for r in _gaql(gm, venue, "SELECT segments.week, campaign.id, metrics.impressions, metrics.search_impression_share, "
                              "metrics.search_budget_lost_impression_share, metrics.search_rank_lost_impression_share "
                              f"FROM campaign WHERE segments.date BETWEEN '{start}' AND '{end}' "
                              "AND campaign.advertising_channel_type = 'SEARCH' AND metrics.impressions > 0"):
        i = idx.get(r["segments"]["week"])
        m = r["metrics"]
        share = m.get("searchImpressionShare")
        if i is None or not share:
            continue
        im = int(m.get("impressions", 0))
        e = im / share
        elig[i] += e; shown[i] += im
        lb[i] += e * float(m.get("searchBudgetLostImpressionShare") or 0)
        lr[i] += e * float(m.get("searchRankLostImpressionShare") or 0)
    for i, o in enumerate(out):
        o[0], o[3], o[4] = round(o[0], 2), round(o[3], 1), round(o[4], 2)
        if elig[i]:
            o[6], o[7], o[8] = round(shown[i] / elig[i], 3), round(lb[i] / elig[i], 3), round(lr[i] / elig[i], 3)
        if venue.get("google_excluded"):
            o[3] = None  # not a verified booking action: spend shown, bookings and CPA n/a
    return out


# ------------------------------------------------------------------ assemble
def rows_for_market(market, pcfg):
    """Report rows: one per venue, except venues that share ad accounts, which make one row."""
    groups = {g["members"][0]: g for g in market.get("group", [])}
    skip = {m for g in market.get("group", []) for m in g["members"][1:]}
    out = []
    for v in market["venue"]:
        if v["name"] in skip:
            continue
        g = groups.get(v["name"])
        members = [x for x in market["venue"] if g and x["name"] in g["members"]] or [v]
        p = pcfg.get(v["name"], {})
        no_ly = all(x.get("no_ly") or pcfg.get(x["name"], {}).get("ly_null") or pcfg.get(x["name"], {}).get("ly_null_from")
                    for x in members)
        out.append({"name": g["name"] if g else v["name"], "acct": v, "members": members, "no_ly": no_ly,
                    "order": p.get("order", 99)})
    return sorted(out, key=lambda r: r["order"])


def build_market(gm, sr, market, pcfg, weeks):
    ly = [w.yoy for w in weeks]
    sr_ty, sr_ly = sevenrooms(sr, market, weeks), sevenrooms(sr, market, ly)

    def srs(members, data, ws):
        out = []
        for w in ws:
            web = gr = 0
            for m in members:
                cells = data.get(m["name"], {}).get(w.monday, {})
                web += sum(cells.get("web", {}).get(k, (0, 0))[0] for k in (1, 2, 3))
                gr += sum(cells.get("gr", {}).get(k, (0, 0))[0] for k in (1, 2, 3))
            out.append([web, gr])
        return out

    venues = []
    for r in rows_for_market(market, pcfg):
        v = r["acct"]
        meta_ty, other_ty = meta_series(gm, v, weeks)
        meta_ly, other_ly = (None, None) if r["no_ly"] else meta_series(gm, v, ly)
        venues.append({
            "name": r["name"],
            "meta": {"ty": meta_ty, "ly": meta_ly},
            "other": {"ty": other_ty, "ly": other_ly},
            "google": {"ty": google_series(gm, v, weeks, True),
                       "ly": None if r["no_ly"] else google_series(gm, v, ly, False)},
            "sr": {"ty": srs(r["members"], sr_ty, weeks), "ly": None if r["no_ly"] else srs(r["members"], sr_ly, ly)},
        })
    return {"market": market["name"], "slug": market["slug"], "sym": market["sym"].strip(), "ccy": market["ccy"],
            "weeks": [w.monday.isoformat() for w in weeks],
            "generated": datetime.now(timezone.utc).isoformat(timespec="minutes"), "venues": venues}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--markets", default="london,hk,usa,dubai,paris")
    a = ap.parse_args(argv)
    markets = {m["slug"]: m for m in tomllib.loads((CFG / "markets.toml").read_text())["market"]}
    pcfg = tomllib.loads((CFG / "pipeline.toml").read_text())
    weeks = Week(last_completed_monday(datetime.now(timezone.utc).date())).back(N_WEEKS)
    gm, sr = GoMarble(), SevenRooms()
    summary, status = [], 0
    for slug in a.markets.split(","):
        try:
            payload = build_market(gm, sr, markets[slug], pcfg.get(slug, {}), weeks)
        except Exception as e:  # keep yesterday's payload rather than write a partial one
            summary.append(f"{slug}: FAILED, left as it was: {str(e)[:300]}")
            status = 1
            continue
        last = {v["name"]: (v["meta"]["ty"][-1][5], v["google"]["ty"][-1][3], sum(v["sr"]["ty"][-1])) for v in payload["venues"]}
        summary.append(f"{slug}: {len(payload['venues'])} venues, W{weeks[-1].monday.isocalendar()[1]} "
                       f"meta/google/sevenrooms bookings {last}")
        if a.write:
            with sr.conn.cursor() as cur:
                cur.execute("insert into ads_monitor (market, payload, updated_at) values (%s, %s, now()) "
                            "on conflict (market) do update set payload = excluded.payload, updated_at = now()",
                            (slug, json.dumps(payload)))
    report = "### Ads monitor\n```\n" + "\n".join(summary) + "\n```\n"
    print(report)
    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as fh:
        fh.write(report)
    return status


if __name__ == "__main__":
    sys.exit(main())
