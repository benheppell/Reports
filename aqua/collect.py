"""Pull every source figure a market's weekly reports need, into one facts file.

The facts file (_facts.json, never published) is the single input to every payload builder,
so a run can be re-rendered, diffed or audited without touching a source again.

Weeks pulled per venue: the 8 weeks ending with the reporting week, and the same 8 weeks last
year (minus 364 days). Prior and year-ago weeks are always re-pulled, never carried forward,
because Google conversions settle upward for two to three weeks and GA4 rates restate.
"""
from __future__ import annotations

import concurrent.futures as cf
import traceback
from datetime import date, timedelta

from .dates import Week, fy_start
from .sources import ga4, meta
from .sources.gomarble import GoMarble
from .sources.google_ads import GoogleAds

N_WEEKS = 8


def _ly(weeks: list[Week]) -> list[Week]:
    return [w.yoy for w in weeks]


def collect_venue(gm: GoMarble, gads: GoogleAds, market: dict, defaults: dict, v: dict, week: Week) -> dict:
    ty, ly = week.back(N_WEEKS), _ly(week.back(N_WEEKS))
    ev, ex = defaults["ga4_event"], defaults["ga4_exclude_paths"]
    f: dict = {"errors": []}

    def guard(key, fn, *a):
        try:
            f[key] = fn(*a)
        except Exception as e:  # never fabricate: a failed pull is null and named
            f[key] = None
            f["errors"].append(f"{key}: {e}")
            traceback.print_exc()

    def both(fn, *a):
        a_ty, a_ly = fn(*a, ty), fn(*a, ly)
        return {**a_ly, **a_ty}

    guard("ga4_book", lambda: both(lambda vv, ws: ga4.bookings_by_week(gm, vv, ws, ev, ex), v))
    guard("web", lambda: both(lambda vv, ws: ga4.web_by_week(gm, vv, ws), v))
    fys = fy_start(week.monday, market["fy_start_month"])
    guard("ytd_book", lambda: sum(ga4.bookings_by_week(gm, v, _weeks_between(fys, week), ev, ex).values()))
    for k, dim in (("channels", "sessionDefaultChannelGroup"),):
        guard(k, lambda: {lab: ga4.breakdown(gm, v, w, dim, ev, ex)
                          for lab, w in (("cur", week), ("prior", week.prior), ("yoy", week.yoy))})
    guard("devices", lambda: ga4.breakdown(gm, v, week, "deviceCategory", ev, ex))
    guard("landing", lambda: ga4.breakdown(gm, v, week, "landingPage", ev, ex, limit=50))
    if v.get("meta"):
        guard("meta", lambda: both(lambda vv, ws: meta.weekly(gm, vv, ws, defaults["meta_event"]), v))
        guard("meta_campaigns", lambda: {"cur": meta.campaigns(gm, v, week, defaults["meta_event"]),
                                         "prior": meta.campaigns(gm, v, week.prior, defaults["meta_event"])})
    if v.get("google"):
        guard("google", lambda: both(lambda vv, ws: gads.weekly(vv, ws), v))
        guard("google_campaigns", lambda: {"cur": gads.campaigns(v, week), "prior": gads.campaigns(v, week.prior)})
    return f


def _weeks_between(start: date, week: Week) -> list[Week]:
    """Whole weeks from the FY's W1 to the reporting week. The stub days before W1 are added
    by the caller if a market counts them (none does today)."""
    w1 = start + timedelta(days=(7 - start.weekday()) % 7)
    n = (week.monday - w1).days // 7 + 1
    return week.back(n)


def collect_market(market: dict, defaults: dict, week: Week, gm: GoMarble, sr=None,
                   gads: GoogleAds | None = None, workers: int = 6) -> dict:
    gads = gads or GoogleAds(gm)
    facts = {"market": market["slug"], "week": week.monday.isoformat(), "venues": {}, "covers": None,
             "web_rows": None, "errors": []}
    seen_shared: dict[str, str] = {}
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(collect_venue, gm, gads, market, defaults, v, week): v["name"] for v in market["venue"]}
        for fut in cf.as_completed(futs):
            facts["venues"][futs[fut]] = fut.result()
    for v in market["venue"]:  # shared ad accounts are pulled for each row but shown once
        if v.get("shared_ads"):
            seen_shared.setdefault(v["shared_ads"], v["name"])
    facts["shared_owner"] = seen_shared
    if sr is not None and market.get("covers_rules"):
        ty = week.back(N_WEEKS)
        try:
            facts["covers"] = {"ty": sr.covers_by_week(market, ty), "ly": sr.covers_by_week(market, [week.yoy])}
        except Exception as e:
            facts["errors"].append(f"covers: {e}")
        try:
            facts["web_rows"] = sr.gross_web_rows(market, [week.prior, week])
        except Exception as e:
            facts["errors"].append(f"web_rows: {e}")
    for name, vf in facts["venues"].items():
        facts["errors"] += [f"{name} {e}" for e in vf["errors"]]
    return facts
