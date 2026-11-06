"""SevenRooms covers and bookings from Supabase (project vklgpzrhjvjqhlpfennn).

The channel classification is written down here once per market, versioned with the code,
rather than re-derived each Monday. Rules come from public.london_daily_covers_base (London)
and the HK and USA rule sets recorded in hk/w2026-09-28 and usa/w2026-10-26 _covers_raw.json.

Covers = SUM(covers) by booking-created date in market timezone, is_deleted false, status not
Canceled, seating areas containing "bar" excluded, staff-named sources excluded. Late records
(service date before the Monday of the created week) are dropped from 16 Oct 2026.
Date predicates are plain sargable ranges on sr_created_at, both ends bounded, one contiguous
range per query.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

from ..dates import Week

CHANNELS = ["web", "gr", "ot", "walk", "recep", "ota", "tp", "other"]

STAFF = (r"""(src ~ '^[A-ZÀ-Þ][a-zà-þ''’.-]+( [A-ZÀ-Þ][a-zà-þ''’.-]+)+$' AND src !~* """
         r"""'(widget|landing|page|cta|reception|host|integration|table|walk|ppc|group|experience|session|"""
         r"""transfer|gift|website|reserve|guestcenter|concierge|theatre|offer|menu|brunch|lunch|dinner|bar|"""
         r"""terrace|hour|night|roast|tea)')""")

WEB = ("(src ILIKE 'booking widget' OR src ILIKE '%landing page%' OR src ILIKE 'PPC%' OR lower(src) IN "
       "('nav cta','hero cta','menu page','website','popup','edm','what''s on'))")
GR = "src = 'Google Reserve Integration'"
WALK = "src = 'Walk In'"
OPENTABLE = ("(src ILIKE '%open table%' OR src ILIKE '%opentable%' OR src = 'OT Guestcenter' "
             "OR lower(src) = 'ot' OR src ILIKE '%otgc%')")

RULES: dict[str, list[tuple[str, str]]] = {
    # Order matters: the first match wins. 'excluded' rows are left out of covers entirely.
    "london": [
        ("excluded", STAFF),
        ("web", WEB), ("gr", GR), ("ot", OPENTABLE), ("walk", WALK),
        ("recep", "(src ILIKE '%reception%' OR src = 'DSL Host')"),
        ("ota", "(src ILIKE 'thefork%' OR src ILIKE 'first table%')"),
        ("tp", "TRUE"),
    ],
    "hk": [
        ("ot", "src ILIKE '%openrice%'"),
        ("tp", "(src ILIKE '%trip advisor%' OR src ILIKE '%tripadvisor%')"),
        ("gr", GR), ("walk", WALK), ("web", WEB),
        ("recep", "(src ILIKE '%reception%' OR src ILIKE '%reservation%' OR src ~* "
                  "'^(the )?(chinese library|cantina|pacific place|hutong|vesu|vista|canton library)' OR src ~ ',')"),
        ("excluded", "TRUE"),
    ],
    "usa": [
        ("recep", "(src ILIKE '%reception%' OR src ILIKE 'reservation team' OR src ILIKE 'reservations team')"),
        ("tp", "(src ILIKE '%doordash%' OR src ILIKE 'bilt integration' OR src ILIKE 'flaming duck%' "
               "OR src ILIKE 'capital one%')"),
        ("excluded", STAFF),
        ("web", WEB), ("gr", GR), ("walk", WALK),
        ("ot", f"({OPENTABLE[1:-1]} OR src ILIKE 'resy%')"),
        ("other", "TRUE"),
    ],
    # Dubai and Paris have no covers report; the pipeline uses its own rules.
}


def channel_case(market_rules: str) -> str:
    parts = [f"WHEN {cond} THEN '{ch}'" for ch, cond in RULES[market_rules]]
    return "CASE " + " ".join(parts) + " END"


def covers_sql(market_rules: str, tz: str, venue_names: list[str], start: date, end_excl: date,
               late_rule: bool = True) -> tuple[str, list]:
    """One contiguous created-date range; returns rows (venue, week_monday, ch, covers, bookings, late_covers)."""
    sql = f"""
WITH c AS (
  SELECT v.name AS sr_venue, res.covers AS cov, res.service_date AS sd,
         COALESCE(res.booking_source, '') AS src,
         date_trunc('week', ((res.sr_created_at AT TIME ZONE %(tz)s)::date)::timestamp)::date AS cw
  FROM reservations res JOIN venues v ON v.id = res.venue_id
  WHERE v.name = ANY(%(venues)s)
    AND res.is_deleted = false
    AND COALESCE(res.status_simple, '') <> 'Canceled'
    AND COALESCE(res.raw->>'venue_seating_area_name', '') NOT ILIKE '%%bar%%'
    AND res.sr_created_at >= (%(start)s::timestamp AT TIME ZONE %(tz)s)
    AND res.sr_created_at <  (%(end)s::timestamp AT TIME ZONE %(tz)s)
), k AS (
  SELECT sr_venue, cw, cov, {channel_case(market_rules).replace('%', '%%')} AS ch,
         {"(sd IS NOT NULL AND sd < cw)" if late_rule else "false"} AS late
  FROM c
)
SELECT sr_venue, cw, ch,
       COALESCE(SUM(cov) FILTER (WHERE NOT late), 0)::int AS covers,
       COUNT(*) FILTER (WHERE NOT late)::int AS bookings,
       COALESCE(SUM(cov) FILTER (WHERE late), 0)::int AS late_covers
FROM k GROUP BY sr_venue, cw, ch ORDER BY sr_venue, cw, ch
"""
    return sql, {"tz": tz, "venues": venue_names, "start": start.isoformat(), "end": end_excl.isoformat()}


def dsn_parts(dsn: str) -> dict:
    """Split a postgresql:// URL into keyword arguments ourselves. Pasted secrets often carry a
    trailing newline or space, and passwords with @ # / ? confuse URL parsing; splitting on the
    last @ and unquoting avoids both."""
    import socket
    from urllib.parse import unquote
    s = dsn.strip()
    scheme, _, rest = s.partition("://")
    if scheme not in ("postgresql", "postgres"):
        raise ValueError("SUPABASE_DB_URL must start with postgresql://")
    userinfo, _, hostpart = rest.rpartition("@")
    user, _, password = userinfo.partition(":")
    hostport, _, dbname = hostpart.partition("/")
    host, _, port = hostport.partition(":")
    host = host.strip()
    try:
        socket.getaddrinfo(host, int(port or 5432), socket.AF_INET)
    except OSError as e:
        raise ConnectionError(f"cannot resolve {host!r} over IPv4: {e}") from None
    return {"host": host, "port": int(port or 5432), "user": unquote(user), "password": unquote(password),
            "dbname": (dbname.split("?")[0] or "postgres").strip(), "sslmode": "require"}


class SevenRooms:
    def __init__(self, dsn: str | None = None):
        import psycopg  # only the live run needs a database driver
        self.conn = psycopg.connect(autocommit=True, connect_timeout=30,
                                    **dsn_parts(dsn or os.environ["SUPABASE_DB_URL"]))

    def query(self, sql: str, params) -> list[tuple]:
        with self.conn.cursor() as cur:
            cur.execute("SET statement_timeout = '120s'")
            cur.execute(sql, params)
            return cur.fetchall()

    def covers_by_week(self, market: dict, weeks: list[Week]) -> dict:
        """{report venue: {week folder: {channel: covers, ..., '_bookings': {ch: n}, '_late': n}}}"""
        names = sorted({n for v in market["venue"] for n in v["sr"]})
        sql, params = covers_sql(market["covers_rules"], market["tz"], names,
                                 weeks[0].monday, weeks[-1].sunday + timedelta(days=1))
        rows = self.query(sql, params)
        return fold(market, weeks, rows)


    def gross_web_rows(self, market: dict, weeks: list[Week]) -> dict:
        """Website booking rows on a gross basis (all statuses, bar included), the denominator of
        the GA4 capture ratio: GA4 create-path bookings / these rows. SevenRooms cannot be affected by
        anything on our own site, so the ratio isolates measurement from demand."""
        names = sorted({n for v in market["venue"] for n in v["sr"]})
        sql = f"""
WITH c AS (
  SELECT v.name AS sr_venue, COALESCE(res.booking_source, '') AS src,
         date_trunc('week', ((res.sr_created_at AT TIME ZONE %(tz)s)::date)::timestamp)::date AS cw
  FROM reservations res JOIN venues v ON v.id = res.venue_id
  WHERE v.name = ANY(%(venues)s) AND res.is_deleted = false
    AND res.sr_created_at >= (%(start)s::timestamp AT TIME ZONE %(tz)s)
    AND res.sr_created_at <  (%(end)s::timestamp AT TIME ZONE %(tz)s))
SELECT sr_venue, cw, COUNT(*)::int FROM c WHERE {WEB.replace('%', '%%')} GROUP BY sr_venue, cw"""
        rows = self.query(sql, {"tz": market["tz"], "venues": names, "start": weeks[0].monday.isoformat(),
                                "end": (weeks[-1].sunday + timedelta(days=1)).isoformat()})
        folders = {w.monday: w.folder for w in weeks}
        out = {v["name"]: {w.folder: 0 for w in weeks} for v in market["venue"]}
        for sr_venue, cw, n in rows:
            for v in market["venue"]:
                if sr_venue in v["sr"] and cw in folders:
                    out[v["name"]][folders[cw]] += n
        return out


def fold(market: dict, weeks: list[Week], rows) -> dict:
    """Map SevenRooms rows onto report venues, applying sr_from."""
    by_sr = {}
    for v in market["venue"]:
        for n in v["sr"]:
            by_sr.setdefault(n, []).append(v)
    folders = {w.monday: w.folder for w in weeks}
    out = {v["name"]: {w.folder: {**{ch: 0 for ch in CHANNELS}, "_bookings": {}, "_late": 0} for w in weeks}
           for v in market["venue"]}
    for sr_venue, cw, ch, cov, n, late in rows:
        if cw not in folders:
            continue
        for v in by_sr.get(sr_venue, []):
            if v.get("sr_from") and cw < date.fromisoformat(v["sr_from"]) - timedelta(days=date.fromisoformat(v["sr_from"]).weekday()):
                continue
            cell = out[v["name"]][folders[cw]]
            cell["_late"] += late
            if ch == "excluded":
                continue
            cell[ch] += cov
            cell["_bookings"][ch] = cell["_bookings"].get(ch, 0) + n
    return out
