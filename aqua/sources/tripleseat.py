"""Tripleseat API v1 (London events and private dining).

Auth: OAuth 2.0 client_credentials. A fresh token is minted at the start of every run and never
stored (tokens last 2 hours, no refresh token, minting another does not revoke the first).
Needs env TRIPLESEAT_CLIENT_ID and TRIPLESEAT_CLIENT_SECRET.

Behaviour found in discovery (17 Nov 2026) that this module relies on:
- created_before (leads) and event_created_end_date / event_end_date (events) are exclusive upper
  bounds, so callers pass the day after the last day wanted.
- Lead and event timestamps are US-format London local strings ("9/21/2026 8:10 AM"); booking
  dates are ISO with an offset; event_date_iso8601 is the clean event date.
- status_changes is unsorted: sort by created_at before use.
- Names (lost reasons, event types, segments) carry stray spaces: trim them.

Only IDs, dates, counts and source fields leave this module. Names, emails, phones, company,
notes and descriptions are never read into a row.
"""
from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

LONDON = ZoneInfo("Europe/London")


class TripleseatError(RuntimeError):
    pass


# ------------------------------------------------------------------ parsing helpers (pure)

def clean(s) -> str | None:
    if s is None:
        return None
    s = str(s).strip()
    return s or None


def num(v) -> float | None:
    """Money and counts arrive as numbers or strings ("4115.0", "£4,115.00")."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("£", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def to_int(v) -> int | None:
    n = num(v)
    return int(n) if n is not None else None


def parse_ts(v) -> datetime | None:
    """US-format London local ("9/21/2026 8:10 AM"), or ISO 8601 with or without an offset."""
    v = clean(v)
    if not v:
        return None
    for fmt in ("%m/%d/%Y %I:%M %p", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y"):
        try:
            return datetime.strptime(v, fmt).replace(tzinfo=LONDON)
        except ValueError:
            pass
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=LONDON)


def parse_date(v) -> date | None:
    v = clean(v)
    if not v:
        return None
    try:
        return date.fromisoformat(v[:10])
    except ValueError:
        t = parse_ts(v)
        return t.date() if t else None


def obj_id(v) -> int | None:
    """A field that is either an id or an object with an id."""
    if isinstance(v, dict):
        return to_int(v.get("id"))
    return to_int(v)


def obj_name(v) -> str | None:
    if isinstance(v, dict):
        return clean(v.get("name"))
    return clean(v)


def timeline(status_changes) -> dict:
    """First time each status was reached, from the unsorted status_changes list."""
    rows = []
    for c in status_changes or []:
        t = parse_ts(c.get("created_at"))
        if t:
            rows.append((t, clean(c.get("status")) or ""))
    rows.sort()
    first = {}
    for t, s in rows:
        first.setdefault(s.upper(), t)
    return {"first_tentative_at": first.get("TENTATIVE"), "first_definite_at": first.get("DEFINITE"),
            "lost_at": first.get("LOST"), "closed_at": first.get("CLOSED")}


def value_rule(actual, grand, fbmin) -> tuple[float | None, str]:
    """actual_amount, else grand_total, else food_and_beverage_min; say which was used."""
    for v, basis in ((actual, "actual"), (grand, "grand"), (fbmin, "fbmin")):
        if v is not None and v > 0:
            return v, basis
    return None, "none"


def lead_source(lead: dict) -> tuple[int | None, str | None]:
    srcs = lead.get("lead_sources") or []
    if not srcs:
        return None, None
    first = srcs[0]
    sid, name = (obj_id(first), obj_name(first)) if isinstance(first, dict) else (None, clean(first))
    if name and "opentable" in name.replace(" ", "").lower():
        name = "OpenTable"
    return sid, name


def lead_row(lead: dict, venues: dict[int, str]) -> dict | None:
    loc = obj_id(lead.get("location")) or to_int(lead.get("location_id"))
    if loc not in venues:
        return None
    sid, sname = lead_source(lead)
    conv = parse_ts(lead.get("converted_at"))
    return {
        "lead_id": to_int(lead.get("id")), "location_id": loc, "venue": venues[loc],
        "created_at": parse_ts(lead.get("created_at")),
        "converted_on": conv.date() if conv else None,
        "turned_down_at": parse_ts(lead.get("turned_down_at")),
        "event_id": to_int(lead.get("event_id")),
        "requested_event_date": parse_date(lead.get("event_date_iso8601") or lead.get("event_date")),
        "guest_count": to_int(lead.get("guest_count")),
        "lead_source_id": sid, "lead_source": sname,
        "referral_source_id": to_int(lead.get("referral_source_id")),
        "lead_form_id": to_int(lead.get("lead_form_id")),
        "utm_source": clean(lead.get("campaign_source")), "utm_medium": clean(lead.get("campaign_medium")),
        "utm_campaign": clean(lead.get("campaign_name")),
        "has_gclid": bool(clean(lead.get("gclid"))),
        "deleted_at": parse_ts(lead.get("deleted_at")),
    }


def event_row(ev: dict, venues: dict[int, str], min_year: int = 2015) -> dict | None:
    loc = obj_id(ev.get("location")) or to_int(ev.get("location_id"))
    if loc not in venues:
        return None
    booking = ev.get("booking") or {}
    ed = parse_date(ev.get("event_date_iso8601") or ev.get("event_date"))
    if ed and ed.year < min_year:
        ed = None
    actual, grand, fbmin = num(ev.get("actual_amount")), num(ev.get("grand_total")), num(ev.get("food_and_beverage_min"))
    value, basis = value_rule(actual, grand, fbmin)
    lost = ev.get("lost_reason") if isinstance(ev.get("lost_reason"), dict) else {}
    rooms = ev.get("room_ids") or [obj_id(r) for r in (ev.get("rooms") or [])]
    return {
        "event_id": to_int(ev.get("id")),
        "booking_id": obj_id(booking) or to_int(ev.get("booking_id")),
        "lead_id": obj_id(ev.get("lead")) or to_int(ev.get("lead_id")),
        "location_id": loc, "venue": venues[loc],
        "room_ids": [r for r in (to_int(x) for x in rooms) if r is not None],
        "room_class": None,  # needs Ben's room map sign-off
        "event_type": obj_name(ev.get("event_type")),
        "market_segment": clean(booking.get("market_segment")),
        "status": (clean(ev.get("status")) or "").upper() or None,
        "created_at": parse_ts(ev.get("created_at")), "updated_at": parse_ts(ev.get("updated_at")),
        "deleted_at": parse_ts(ev.get("deleted_at")),
        "event_date": ed,
        **timeline(ev.get("status_changes")),
        "booking_definite_date": parse_date(booking.get("definite_date")),
        "booking_lost_date": parse_date(booking.get("lost_date")),
        "guest_count": to_int(ev.get("guest_count")),
        "food_and_beverage_min": fbmin, "grand_total": grand, "actual_amount": actual,
        "deposit_amount": num(ev.get("deposit_amount")),
        "value": value, "value_basis": basis,
        "lost_reason": clean(lost.get("name")), "lost_reason_id": to_int(lost.get("id")),
    }


def room_names(ev: dict) -> list[tuple[int, str]]:
    """(room id, room name) pairs from an event's rooms list. Room names are venue spaces, not people."""
    out = []
    for r in ev.get("rooms") or []:
        if isinstance(r, dict):
            r = unwrap(r) if "id" not in r else r
            rid, name = obj_id(r), obj_name(r)
            if rid is not None and name:
                out.append((rid, name))
    return out


def results_of(payload) -> tuple[list, int | None]:
    """Search responses: a list, or an object holding the rows plus a page count."""
    if isinstance(payload, list):
        return [unwrap(r) for r in payload], None
    if not isinstance(payload, dict):
        return [], None
    pages = to_int(payload.get("total_pages") or (payload.get("meta") or {}).get("total_pages"))
    for key in ("results", "events", "leads", "bookings", "locations", "data"):
        if isinstance(payload.get(key), list):
            return [unwrap(r) for r in payload[key]], pages
    lists = [v for v in payload.values() if isinstance(v, list)]
    return ([unwrap(r) for r in lists[0]] if len(lists) == 1 else []), pages


def unwrap(row):
    """Some endpoints wrap each row as {"location": {...}}; take the inner object."""
    if isinstance(row, dict) and len(row) == 1:
        (inner,) = row.values()
        if isinstance(inner, dict):
            return inner
    return row


# ------------------------------------------------------------------ client

class Tripleseat:
    def __init__(self, api: str = "https://api.tripleseat.com", rps: float = 5.0,
                 client_id: str | None = None, client_secret: str | None = None):
        self.api = api.rstrip("/")
        self.gap = 1.0 / rps
        self._last = 0.0
        self.s = requests.Session()
        self.s.headers["Accept"] = "application/json"
        cid = client_id or os.environ.get("TRIPLESEAT_CLIENT_ID", "").strip()
        sec = client_secret or os.environ.get("TRIPLESEAT_CLIENT_SECRET", "").strip()
        if not cid or not sec:
            raise TripleseatError("TRIPLESEAT_CLIENT_ID and TRIPLESEAT_CLIENT_SECRET are not set")
        r = self.s.post(f"{self.api}/oauth2/token", timeout=60,
                        data={"grant_type": "client_credentials", "client_id": cid, "client_secret": sec})
        if r.status_code != 200:
            raise TripleseatError(f"token request failed ({r.status_code}): {r.text[:200]}")
        self.s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    def get(self, path: str, params: dict | None = None):
        url = f"{self.api}{path}"
        for attempt in range(5):
            wait = self.gap - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                r = self.s.get(url, params=params, timeout=120)
            except requests.RequestException as e:
                err = str(e)
            else:
                if r.status_code == 200:
                    return r.json()
                err = f"{r.status_code}: {r.text[:200]}"
                if r.status_code not in (429, 500, 502, 503, 504):
                    raise TripleseatError(f"GET {path} {err}")
            time.sleep(5 * (attempt + 1))
        raise TripleseatError(f"GET {path} failed after retries: {err}")

    def pages(self, path: str, params: dict, max_pages: int = 2000):
        """Yield every row of a paged search; stops on an empty page or the reported last page."""
        page = 1
        while page <= max_pages:
            rows, total = results_of(self.get(path, {**params, "page": page}))
            if not rows:
                return
            yield from rows
            if total is not None and page >= total:
                return
            page += 1
        raise TripleseatError(f"{path}: more than {max_pages} pages")

    # Searches. Dates are inclusive start, exclusive end (the API's own behaviour).
    def leads_created(self, start: date, end_excl: date):
        return self.pages("/v1/leads/search.json", {"created_after": start.isoformat(),
                                                     "created_before": end_excl.isoformat()})

    def events_created(self, start: date, end_excl: date, location_ids: list[int]):
        return self.pages("/v1/events/search.json", {
            "event_created_start_date": start.isoformat(), "event_created_end_date": end_excl.isoformat(),
            "location_ids": ",".join(str(i) for i in location_ids),
            "show_financial": "true", "include_deleted": "true"})

    def events_dated(self, start: date, end_excl: date, location_ids: list[int]):
        return self.pages("/v1/events/search.json", {
            "event_start_date": start.isoformat(), "event_end_date": end_excl.isoformat(),
            "location_ids": ",".join(str(i) for i in location_ids),
            "show_financial": "true", "include_deleted": "true"})

    def events_updated(self, start: date, location_ids: list[int]):
        return self.pages("/v1/events/search.json", {
            "event_updated_start_date": start.isoformat(),
            "event_updated_end_date": (date.today() + timedelta(days=1)).isoformat(),
            "location_ids": ",".join(str(i) for i in location_ids),
            "show_financial": "true", "include_deleted": "true"})

    def locations(self):
        rows, _ = results_of(self.get("/v1/locations.json"))
        return rows
