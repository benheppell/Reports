"""Monthly dashboard: the weekly dashboard cut down to bookings, target, MoM and YoY.
Built on the first Monday of each month for the month just completed."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from ..dates import MONTHS_LONG, long_date
from ..sources import ga4
from .common import fmt_int, no_dashes, pct, words


def month_bounds(y: int, m: int) -> tuple[date, date]:
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


def prev_month(y: int, m: int) -> tuple[int, int]:
    return (y - 1, 12) if m == 1 else (y, m - 1)


def collect(gm, market: dict, defaults: dict, y: int, m: int) -> dict:
    ev, ex = defaults["ga4_event"], defaults["ga4_exclude_paths"]
    py, pm = prev_month(y, m)
    out = {}
    for v in market["venue"]:
        if v.get("outside"):
            continue
        f = {}
        for key, (yy, mm) in (("act", (y, m)), ("mom", (py, pm)), ("yoy", (y - 1, m))):
            try:
                f[key] = ga4.bookings_range(gm, v, *month_bounds(yy, mm), ev, ex)
            except Exception as e:  # a failed pull is null and named, never zero
                f[key] = None
                f.setdefault("errors", []).append(f"{key}: {e}")
        out[v["name"]] = f
    return out


def build(market: dict, facts: dict, targets: dict, y: int, m: int, generated: date) -> dict:
    key = f"{y}-{m:02d}"
    tg = targets.get(market["slug"], {})
    no_target = bool(market.get("no_target"))
    venues = []
    for v in market["venue"]:
        if v.get("outside"):
            continue
        f = facts[v["name"]]
        r = {"name": v["name"], "act": round(f["act"]) if f["act"] is not None else None,
             "mom": round(f["mom"]) if f["mom"] is not None else None,
             "yoy": round(f["yoy"]) if f["yoy"] is not None else None,
             "nc": bool(v.get("not_comparable") or v.get("no_ly"))}
        if not no_target:
            r["tgt"] = (tg.get(v["name"]) or {}).get(key)
        venues.append(r)
    act = sum(r["act"] or 0 for r in venues)
    mom = sum(r["mom"] or 0 for r in venues)
    yoy = sum(r["yoy"] or 0 for r in venues if not r["nc"])
    act_c = sum(r["act"] or 0 for r in venues if not r["nc"])
    label = f"{MONTHS_LONG[m - 1]} {y}"
    note = (f"{label} closed at <b>{fmt_int(act)}</b> create-path GA4 bookings, <b>{words(pct(act, mom))}</b> on "
            f"the month before and <b>{words(pct(act_c, yoy))}</b> year on year on comparable venues.")
    return {"market": f"Aqua {market['name']}", "sym": market["sym"], "ccy": market["ccy"], "month_label": label,
            "generated": long_date(generated), "venues": venues, "note": no_dashes(note), "no_target": no_target}
