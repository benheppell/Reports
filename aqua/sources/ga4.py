"""GA4 pulls through GoMarble, at week grain.

Users are not additive across days, so every metric is requested with the isoYearIsoWeek
dimension (ISO weeks run Monday to Sunday, matching the reporting week) over a contiguous range.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import date

from ..dates import Week
from .gomarble import GoMarble

TOOL = "google_analytics_run_report"


def _iso_key(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}{w:02d}"


def _path_filter(path: str | None, path_not: str | None) -> list[dict]:
    ex = []
    if path:
        ex.append({"filter": {"fieldName": "pagePath", "stringFilter": {"matchType": "PARTIAL_REGEXP", "value": path}}})
    if path_not:
        ex.append({"notExpression": {"filter": {"fieldName": "pagePath",
                                                "stringFilter": {"matchType": "PARTIAL_REGEXP", "value": path_not}}}})
    return ex


def _and(exprs: list[dict]) -> dict | None:
    if not exprs:
        return None
    return exprs[0] if len(exprs) == 1 else {"andGroup": {"expressions": exprs}}


def _run(gm: GoMarble, prop: str, start: date, end: date, metrics: list[str], dims: list[str],
         flt: dict | None = None, limit: int | None = None) -> list[dict]:
    args = {"property_id": prop, "start_date": start.isoformat(), "end_date": end.isoformat(),
            "metrics": metrics, "dimensions": dims}
    if flt:
        args["dimension_filter"] = flt
    if limit:
        args["limit"] = limit
    for attempt in range(3):
        res = gm.call(TOOL, args, fresh=attempt > 0)
        # A real report always carries its headers and metadata, even with zero rows. Anything
        # else is an error or a rate limit dressed as a result: never read it as zero.
        meta = res.get("metadata") or {}
        ok = "metricHeaders" in res and "metadata" in res and not res.get("error")
        if ok and meta.get("total_rows", 0) > meta.get("rows_returned", len(res.get("rows") or [])):
            raise RuntimeError(f"GA4 {prop}: {meta['rows_returned']} of {meta['total_rows']} rows returned")
        if ok:
            break
        time.sleep(10 * (attempt + 1))
    else:
        raise RuntimeError(f"GA4 {prop} {start}..{end}: no report in response: {json.dumps(res)[:200]}")
    out = []
    for r in res.get("rows", []) or []:
        row = {h["name"]: v["value"] for h, v in zip(res["dimensionHeaders"], r["dimensionValues"])} if dims else {}
        for h, v in zip(res["metricHeaders"], r["metricValues"]):
            row[h["name"]] = float(v["value"])
        out.append(row)
    return out


def bookings_by_week(gm: GoMarble, venue: dict, weeks: list[Week], event: str, exclude_paths: str) -> dict[str, float | None]:
    """Create-path GA4 bookings per week folder, summed across the venue's properties."""
    start, end = weeks[0].monday, weeks[-1].sunday
    flt = _and([{"filter": {"fieldName": "eventName", "stringFilter": {"matchType": "EXACT", "value": event}}},
                {"notExpression": {"filter": {"fieldName": "pagePath",
                                              "stringFilter": {"matchType": "PARTIAL_REGEXP", "value": exclude_paths}}}},
                *_path_filter(venue.get("ga4_path"), venue.get("ga4_path_not"))])
    tot: dict[str, float] = defaultdict(float)
    for prop in venue["ga4"]:
        for r in _run(gm, prop, start, end, ["eventCount"], ["isoYearIsoWeek"], flt):
            tot[r["isoYearIsoWeek"]] += r["eventCount"]
    return {w.folder: tot.get(_iso_key(w.monday), 0.0) for w in weeks}


WEB_METRICS = ["totalUsers", "sessions", "averageSessionDuration", "bounceRate", "engagementRate",
               "screenPageViews", "newUsers"]


def web_by_week(gm: GoMarble, venue: dict, weeks: list[Week]) -> dict[str, dict]:
    """Users, sessions and session-weighted rates per week. Rates combine across properties
    weighted by sessions, as the Regent St pair always has been."""
    start, end = weeks[0].monday, weeks[-1].sunday
    flt = _and(_path_filter(venue.get("ga4_path"), venue.get("ga4_path_not")))
    acc: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for prop in venue["ga4"]:
        for r in _run(gm, prop, start, end, WEB_METRICS, ["isoYearIsoWeek"], flt):
            a, s = acc[r["isoYearIsoWeek"]], r["sessions"]
            a["users"] += r["totalUsers"]
            a["sessions"] += s
            a["spv"] += r["screenPageViews"]
            a["new"] += r["newUsers"]
            a["asd_w"] += r["averageSessionDuration"] * s
            a["bounce_w"] += r["bounceRate"] * s
            a["eng_w"] += r["engagementRate"] * s
    out = {}
    for w in weeks:
        a = acc.get(_iso_key(w.monday))
        if not a or not a["sessions"]:
            out[w.folder] = None
            continue
        s = a["sessions"]
        out[w.folder] = {"users": int(a["users"]), "sessions": int(s), "spv": int(a["spv"]), "new": int(a["new"]),
                         "asd": a["asd_w"] / s, "bounce": a["bounce_w"] / s, "eng": a["eng_w"] / s}
    return out


def breakdown(gm: GoMarble, venue: dict, week: Week, dim: str, event: str, exclude_paths: str,
              limit: int | None = None) -> dict[str, dict]:
    """Sessions and create-path bookings for one week split by a dimension
    (sessionDefaultChannelGroup, deviceCategory or landingPage)."""
    path = _path_filter(venue.get("ga4_path"), venue.get("ga4_path_not"))
    bflt = _and([{"filter": {"fieldName": "eventName", "stringFilter": {"matchType": "EXACT", "value": event}}},
                 {"notExpression": {"filter": {"fieldName": "pagePath",
                                               "stringFilter": {"matchType": "PARTIAL_REGEXP", "value": exclude_paths}}}},
                 *path])
    out: dict[str, dict] = defaultdict(lambda: {"s": 0.0, "b": 0.0})
    for prop in venue["ga4"]:
        for r in _run(gm, prop, week.monday, week.sunday, ["sessions"], [dim], _and(path), limit):
            out[r[dim]]["s"] += r["sessions"]
        for r in _run(gm, prop, week.monday, week.sunday, ["eventCount"], [dim], bflt, limit):
            out[r[dim]]["b"] += r["eventCount"]
    return dict(out)


def bookings_range(gm: GoMarble, venue: dict, start: date, end: date, event: str, exclude_paths: str) -> float:
    """Create-path GA4 bookings over any date range (used for months)."""
    flt = _and([{"filter": {"fieldName": "eventName", "stringFilter": {"matchType": "EXACT", "value": event}}},
                {"notExpression": {"filter": {"fieldName": "pagePath",
                                              "stringFilter": {"matchType": "PARTIAL_REGEXP", "value": exclude_paths}}}},
                *_path_filter(venue.get("ga4_path"), venue.get("ga4_path_not"))])
    return sum(r["eventCount"] for prop in venue["ga4"] for r in _run(gm, prop, start, end, ["eventCount"], [], flt))
