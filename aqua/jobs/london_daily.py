"""Morning job: GA4 bookings and users per property per day for the London daily page.

Writes public.london_daily_ga4 (property_id, d, bookings, users), the last 35 days, upserted.
The properties come from public.london_daily_rows, so a venue change is made there, not here.

Basis, matching what the page has always read: bookings are every sevenrooms_booking_complete
event (all page paths, amendments included), users are GA4 daily total users.

    python -m aqua.jobs.london_daily            # check only: compare with the table, write nothing
    python -m aqua.jobs.london_daily --write    # upsert
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

from ..sources.ga4 import _run
from ..sources.gomarble import GoMarble
from ..sources.sevenrooms import SevenRooms

EVENT = "sevenrooms_booking_complete"
DAYS = 35


def pull(gm: GoMarble, prop: str, start: date, end: date) -> dict[date, dict]:
    users = _run(gm, prop, start, end, ["totalUsers"], ["date"])
    flt = {"filter": {"fieldName": "eventName", "stringFilter": {"matchType": "EXACT", "value": EVENT}}}
    books = _run(gm, prop, start, end, ["eventCount"], ["date"], flt)
    out: dict[date, dict] = {}
    for r in users:
        d = datetime.strptime(r["date"], "%Y%m%d").date()
        out[d] = {"users": int(r["totalUsers"]), "bookings": 0}
    for r in books:
        d = datetime.strptime(r["date"], "%Y%m%d").date()
        out.setdefault(d, {"users": 0, "bookings": 0})["bookings"] = int(r["eventCount"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--end", help="last day to pull, YYYY-MM-DD (default yesterday, London)")
    a = ap.parse_args(argv)
    end = date.fromisoformat(a.end) if a.end else (datetime.now(timezone.utc) + timedelta(hours=1)).date() - timedelta(days=1)
    start = end - timedelta(days=DAYS - 1)
    sr = SevenRooms()
    props = sorted({p for (ps,) in sr.query("select ga4_props from london_daily_rows", None) for p in ps})
    gm = GoMarble()
    rows, failed = [], []
    for p in props:
        try:
            for d, v in sorted(pull(gm, p, start, end).items()):
                rows.append((p, d, v["bookings"], v["users"]))
        except Exception as e:  # never write a zero for a failed pull: leave that property's rows alone
            failed.append(f"{p}: {e}")
    existing = {(p, d): (b, u) for p, d, b, u in sr.query(
        "select property_id, d, bookings, users from london_daily_ga4 where d between %s and %s", (start, end))}
    changed = [(p, d, existing.get((p, d)), (b, u)) for p, d, b, u in rows if existing.get((p, d)) != (b, u)]
    print(f"{len(rows)} rows for {len(props)} properties, {start}..{end}; {len(changed)} differ from the table")
    for p, d, old, new in changed[:40]:
        print(f"  {p} {d}: table {old} -> pulled {new}")
    if a.write and rows:
        with sr.conn.cursor() as cur:
            cur.executemany(
                "insert into london_daily_ga4 (property_id, d, bookings, users, updated_at) values (%s, %s, %s, %s, now()) "
                "on conflict (property_id, d) do update set bookings = excluded.bookings, users = excluded.users, "
                "updated_at = now()", rows)
        print(f"wrote {len(rows)} rows")
    summary = {"job": "london_daily", "days": f"{start}..{end}", "rows": len(rows), "differ": len(changed),
               "written": bool(a.write and rows), "failed": failed}
    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as fh:
        fh.write("### London daily GA4\n```\n" + json.dumps(summary, indent=1) + "\n```\n")
    for f in failed:
        print("FAILED", f)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
