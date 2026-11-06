"""Meta Ads through GoMarble.

Bookings are `schedule_total` (returned under `conversions`), except where a venue sets
meta_event (Aqua Kyoto Paris: offsite_conversion.fb_pixel_custom, under `actions`).
time_increment=7 from a Monday start lands exactly on Monday to Sunday weeks, so one call per
account per contiguous range covers every week.
"""
from __future__ import annotations

import json
from collections import defaultdict

from ..dates import Week
from .gomarble import GoMarble

TOOL = "facebook_get_adaccount_insights"


def _action(row: dict, event: str) -> float:
    for key in ("conversions", "actions"):
        for a in row.get(key) or []:
            if a.get("action_type") == event:
                return float(a["value"])
    return 0.0


def _fields(event: str, extra: list[str] = ()) -> list[str]:
    f = ["spend", "impressions", "clicks", "conversions", *extra]
    if event != "schedule_total":
        f.append("actions")
    return f


def _pages(gm: GoMarble, args: dict) -> list[dict]:
    res = gm.call(TOOL, args)
    rows = list(res.get("data") or [])
    dq = res.get("_gomarble_meta_insights_data_quality") or {}
    if dq.get("paging_next_present"):
        raise RuntimeError(f"Meta insights for {args['act_id']} came back incomplete; refusing to sum a partial page.")
    return rows


def weekly(gm: GoMarble, venue: dict, weeks: list[Week], default_event: str) -> dict[str, dict | None]:
    """spend, bookings, impr, clicks per week folder, summed across the venue's accounts.
    A venue restricted to some campaigns is pulled at campaign level and filtered."""
    event = venue.get("meta_event", default_event)
    start, end = weeks[0].monday, weeks[-1].sunday
    camp = venue.get("meta_campaigns")
    book_camp = venue.get("meta_book_campaigns")
    objective = venue.get("meta_objective")
    level = "campaign" if (camp or objective) else "account"
    acc: dict[str, dict] = defaultdict(lambda: {"spend": 0.0, "bookings": 0.0, "impr": 0.0, "clicks": 0.0, "cpb_spend": 0.0})
    seen = set()
    for act in venue["meta"]:
        args = {"act_id": act, "fields": _fields(event, ["campaign_id", "objective"] if level == "campaign" else []),
                "level": level, "time_increment": 7,
                "time_range": json.dumps({"since": start.isoformat(), "until": end.isoformat()}), "limit": 500}
        for r in _pages(gm, args):
            if camp and r.get("campaign_id") not in camp:
                continue
            k = r["date_start"]
            seen.add(k)
            a = acc[k]
            a["spend"] += float(r.get("spend") or 0)
            a["impr"] += float(r.get("impressions") or 0)
            a["clicks"] += float(r.get("clicks") or 0)
            counts = True
            if book_camp is not None:
                counts = r.get("campaign_id") in book_camp
            if objective is not None:
                counts = counts and r.get("objective") == objective
            if counts:  # spend on campaigns that can book is the CPA denominator
                a["bookings"] += _action(r, event)
                a["cpb_spend"] += float(r.get("spend") or 0)
    out = {}
    for w in weeks:
        k = w.monday.isoformat()
        # An account with no delivery returns no row: that is a real zero, not a failed pull.
        out[w.folder] = dict(acc[k]) if k in seen else {"spend": 0.0, "bookings": 0.0, "impr": 0.0, "clicks": 0.0, "cpb_spend": 0.0}
    return out


def campaigns(gm: GoMarble, venue: dict, week: Week, default_event: str) -> list[dict]:
    """Campaign rows for one week: name, spend, bookings."""
    event = venue.get("meta_event", default_event)
    camp = venue.get("meta_campaigns")
    rows = []
    for act in venue["meta"]:
        args = {"act_id": act, "fields": _fields(event, ["campaign_id", "campaign_name"]), "level": "campaign",
                "time_range": json.dumps({"since": week.monday.isoformat(), "until": week.sunday.isoformat()}),
                "sort": "spend_descending", "limit": 200}
        for r in _pages(gm, args):
            if camp and r.get("campaign_id") not in camp:
                continue
            rows.append({"id": r.get("campaign_id"), "name": r.get("campaign_name", ""), "platform": "Meta",
                         "spend": float(r.get("spend") or 0), "bookings": _action(r, event)})
    return rows
