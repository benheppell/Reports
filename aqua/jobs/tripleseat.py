"""Tripleseat feed: leads and events into public.tripleseat_leads and public.tripleseat_events.

    python -m aqua.jobs.tripleseat --check            # structure + the discovery cross-checks, no writes
    python -m aqua.jobs.tripleseat --daily --write    # leads and events created in the last 14 days,
                                                      # plus events updated in the last 3 days
    python -m aqua.jobs.tripleseat --weekly --write   # every event created in the trailing 400 days

Needs TRIPLESEAT_CLIENT_ID, TRIPLESEAT_CLIENT_SECRET and (with --write) SUPABASE_DB_URL.
A run that fails part-way writes nothing: rows are collected first and upserted at the end.
"""
from __future__ import annotations

import argparse
import os
import sys
import tomllib
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from ..sources.tripleseat import Tripleseat, event_row, lead_row

CFG = Path(__file__).resolve().parents[1] / "config" / "tripleseat.toml"

LEAD_COLS = ["lead_id", "location_id", "venue", "created_at", "converted_on", "turned_down_at", "event_id",
             "requested_event_date", "guest_count", "lead_source_id", "lead_source", "referral_source_id",
             "lead_form_id", "utm_source", "utm_medium", "utm_campaign", "has_gclid", "deleted_at"]
EVENT_COLS = ["event_id", "booking_id", "lead_id", "location_id", "venue", "room_ids", "room_class", "event_type",
              "market_segment", "status", "created_at", "updated_at", "deleted_at", "event_date",
              "first_tentative_at", "first_definite_at", "lost_at", "closed_at", "booking_definite_date",
              "booking_lost_date", "guest_count", "food_and_beverage_min", "grand_total", "actual_amount",
              "deposit_amount", "value", "value_basis", "lost_reason", "lost_reason_id"]


def load():
    cfg = tomllib.loads(CFG.read_text())
    venues = {int(k): v["venue"] for k, v in cfg["locations"].items()}
    return cfg["settings"], venues


def upsert(conn, table: str, key: str, cols: list[str], rows: list[dict]) -> None:
    if not rows:
        return
    ph = ", ".join(["%s"] * len(cols))
    upd = ", ".join(f"{c} = excluded.{c}" for c in cols if c != key) + ", pulled_at = now()"
    sql = (f"insert into public.{table} ({', '.join(cols)}, pulled_at) values ({ph}, now()) "
           f"on conflict ({key}) do update set {upd}")
    with conn.cursor() as cur:
        cur.executemany(sql, [[r[c] for c in cols] for r in rows])


def shape(obj, depth=0) -> str:
    """Field names and types only, never values, for --check."""
    if isinstance(obj, dict):
        if depth > 1:
            return "{...}"
        return "{" + ", ".join(f"{k}: {shape(v, depth + 1)}" for k, v in sorted(obj.items())) + "}"
    if isinstance(obj, list):
        return f"[{shape(obj[0], depth + 1)}] x{len(obj)}" if obj else "[]"
    return type(obj).__name__


def check(ts: Tripleseat, venues: dict[int, str]) -> int:
    """Re-run the discovery cross-checks. Prints counts and IDs only."""
    ok = True
    locs = ts.locations()
    ids = sorted(int(l.get("id")) for l in locs if isinstance(l, dict) and l.get("id"))
    print("locations:", ids, "| expected:", sorted(venues))
    ok &= set(ids) >= set(venues)

    raw = list(ts.leads_created(date(2026, 11, 9), date(2026, 11, 16)))
    if raw:
        print("lead fields:", shape(raw[0]))
    hut = sorted(r["lead_id"] for r in (lead_row(x, venues) for x in raw) if r and r["venue"] == "Hutong")
    print(f"Hutong leads 9-15 Nov 2026: {len(hut)} (expected 86), first {hut[:1]} last {hut[-1:]} "
          "(expected 58029346 / 58268334)")
    ok &= len(hut) == 86 and hut[:1] == [58029346] and hut[-1:] == [58268334]

    evs = list(ts.events_created(date(2026, 10, 1), date(2026, 10, 2), [17674]))
    if evs:
        print("event fields:", shape(evs[0]))
    rows = {r["event_id"]: r for r in (event_row(e, venues) for e in evs) if r}
    for eid, want in ((63114934, 4115.0), (63603980, 1926.83)):
        r = rows.get(eid)
        print(f"event {eid}: " + (f"actual {r['actual_amount']} grand {r['grand_total']} basis {r['value_basis']} "
                                   f"status {r['status']} definite {r['first_definite_at']}" if r else "not in this pull")
              + f" (expected actual {want})")
        ok &= bool(r) and r["actual_amount"] == want
    if rows:
        print("statuses:", dict(Counter(r["status"] for r in rows.values())))
    print("CHECK", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--daily", action="store_true")
    mode.add_argument("--weekly", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)

    st, venues = load()
    ts = Tripleseat(st["api"], st["requests_per_second"])
    if a.check:
        return check(ts, venues)

    today = date.today()
    tomorrow = today + timedelta(days=1)
    locs = sorted(venues)
    leads, events = [], {}
    if a.daily:
        start = today - timedelta(days=st["daily_created_days"])
        leads = [r for r in (lead_row(x, venues) for x in ts.leads_created(start, tomorrow)) if r]
        for e in ts.events_created(start, tomorrow, locs):
            r = event_row(e, venues, st["min_event_year"])
            if r:
                events[r["event_id"]] = r
        for e in ts.events_updated(today - timedelta(days=st["daily_updated_days"]), locs):
            r = event_row(e, venues, st["min_event_year"])
            if r:
                events[r["event_id"]] = r
    else:
        start = today - timedelta(days=st["weekly_created_days"])
        # Month-sized slices keep each search short and a failure easy to place.
        s = start
        while s < tomorrow:
            e_ = min(s + timedelta(days=31), tomorrow)
            for e in ts.events_created(s, e_, locs):
                r = event_row(e, venues, st["min_event_year"])
                if r:
                    events[r["event_id"]] = r
            leads += [r for r in (lead_row(x, venues) for x in ts.leads_created(s, e_)) if r]
            s = e_
    by_status = Counter(r["status"] for r in events.values())
    by_venue = Counter(r["venue"] for r in leads)
    report = (f"### Tripleseat {'daily' if a.daily else 'weekly'}\n```\n"
              f"leads: {len(leads)} {dict(by_venue)}\nevents: {len(events)} {dict(by_status)}\n"
              f"value basis: {dict(Counter(r['value_basis'] for r in events.values()))}\n```\n")
    print(report)
    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as fh:
        fh.write(report)
    if a.write:
        from ..sources.sevenrooms import SevenRooms
        conn = SevenRooms().conn
        upsert(conn, "tripleseat_leads", "lead_id", LEAD_COLS, leads)
        upsert(conn, "tripleseat_events", "event_id", EVENT_COLS, list(events.values()))
        print("written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
