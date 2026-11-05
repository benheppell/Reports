"""Google Ads: spend, impressions, clicks, booking conversions and local actions per week.

Two backends, chosen by GOOGLE_ADS_SOURCE:
  bigquery  (default once configured) reads Aqua's own Google Ads tables. The SQL lives in
            aqua/sql/google_ads_*.sql; set GOOGLE_ADS_BQ_PROJECT and GOOGLE_ADS_BQ_DATASET.
  gomarble  runs GAQL through GoMarble. Works today with the same API key as GA4 and Meta.

Both return the same shapes, so nothing downstream knows which ran.

Booking rule: sum conversion actions whose name contains "booking" and "complete" and not
"ga4"; never raw metrics.conversions. A venue can override with an explicit action list, or with
"ga4_named_ok" where its GA4-named action is its only booking action (Cantina, Shiro HK).
GAQL cannot select segments.conversion_action_name alongside cost, so spend and conversions are
two queries. GoMarble returns metrics.cost already converted from micros: never divide again.
"""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from ..dates import Week
from .gomarble import GoMarble

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
LOCAL_PREFIX = "Local actions"


def is_booking_action(name: str, rule: str | list[str] | None) -> bool:
    if isinstance(rule, list):
        return name in rule
    n = name.lower()
    if "booking" not in n or "complete" not in n:
        return False
    return rule == "ga4_named_ok" or "ga4" not in n


LOCAL_ACTIONS = ("store visits", "local actions - directions", "local actions - menu views",
                 "local actions - orders", "calls from ads", "clicks to call")


def is_local_action(name: str) -> bool:
    """Walk-in signals: store visits, directions, menu views, Book Now (Orders) and calls.
    Google reports these under all_conversions only; their `conversions` column is 0."""
    return name.strip().lower() in LOCAL_ACTIONS


class GoogleAds:
    def __init__(self, gm: GoMarble | None = None):
        self.backend = os.environ.get("GOOGLE_ADS_SOURCE", "gomarble")
        self.gm = gm
        self._bq = None
        if self.backend == "bigquery":
            from google.cloud import bigquery  # imported lazily: only the BigQuery backend needs it
            self._bq = bigquery.Client(project=os.environ["GOOGLE_ADS_BQ_PROJECT"])
            self._ds = os.environ["GOOGLE_ADS_BQ_DATASET"]

    # ---------------------------------------------------------------- raw fetches
    def _gaql(self, venue: dict, q: str) -> list[dict]:
        args = {"customer_id": venue["google"], "query": q}
        if venue.get("google_mgr"):
            args["manager_id"] = venue["google_mgr"]
        res = self.gm.call("google_ads_run_gaql", args)
        if res.get("response_complete") is False:
            raise RuntimeError(f"Google Ads {venue['google']}: incomplete response")
        return res.get("results") or []

    def _bq_rows(self, name: str, venue: dict, start, end) -> list[dict]:
        from google.cloud import bigquery
        sql = (SQL_DIR / f"google_ads_{name}.sql").read_text().replace("{dataset}", self._ds)
        cfg = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("customer_id", "STRING", venue["google"]),
            bigquery.ScalarQueryParameter("start", "DATE", start),
            bigquery.ScalarQueryParameter("end", "DATE", end),
        ])
        return [dict(r) for r in self._bq.query(sql, job_config=cfg).result()]

    def _cost_rows(self, venue, start, end):
        """-> [{week, campaign_id, campaign, cost, impr, clicks}] with cost in account currency."""
        if self._bq:
            return self._bq_rows("cost", venue, start, end)
        q = ("SELECT segments.week, campaign.id, campaign.name, metrics.cost_micros, metrics.impressions, "
             f"metrics.clicks FROM campaign WHERE segments.date BETWEEN '{start}' AND '{end}' "
             "AND metrics.impressions > 0")
        out = []
        for r in self._gaql(venue, q):
            m = r.get("metrics", {})
            out.append({"week": r["segments"]["week"], "campaign_id": str(r["campaign"]["id"]),
                        "campaign": r["campaign"].get("name", ""),
                        # GoMarble returns `cost` already converted; raw `costMicros` needs /1e6
                        "cost": float(m["cost"]) if "cost" in m else float(m.get("costMicros", 0) or 0) / 1e6,
                        "impr": float(m.get("impressions", 0) or 0), "clicks": float(m.get("clicks", 0) or 0)})
        return out

    def _conv_rows(self, venue, start, end):
        """-> [{week, campaign_id, action, conversions}]"""
        if self._bq:
            return self._bq_rows("conversions", venue, start, end)
        q = ("SELECT segments.week, campaign.id, segments.conversion_action_name, metrics.conversions, "
             f"metrics.all_conversions FROM campaign WHERE segments.date BETWEEN '{start}' AND '{end}'")
        return [{"week": r["segments"]["week"], "campaign_id": str(r["campaign"]["id"]),
                 "action": r["segments"]["conversionActionName"],
                 "conversions": float(r["metrics"].get("conversions", 0) or 0),
                 "all_conversions": float(r["metrics"].get("allConversions", 0) or 0)} for r in self._gaql(venue, q)]

    # ---------------------------------------------------------------- shaped outputs
    def weekly(self, venue: dict, weeks: list[Week]) -> dict[str, dict]:
        """spend, bookings, impr, clicks, local per week folder.
        Weeks are segments.week, which starts on Monday."""
        start, end = weeks[0].monday, weeks[-1].sunday
        fx = venue.get("google_fx", 1.0)
        rule = venue.get("google_actions")
        acc = defaultdict(lambda: {"spend": 0.0, "bookings": 0.0, "impr": 0.0, "clicks": 0.0, "local": 0.0})
        for r in self._cost_rows(venue, start, end):
            a = acc[str(r["week"])]
            a["spend"] += r["cost"] * fx
            a["impr"] += r["impr"]
            a["clicks"] += r["clicks"]
        for r in self._conv_rows(venue, start, end):
            a = acc[str(r["week"])]
            if is_booking_action(r["action"], rule):
                a["bookings"] += r["conversions"]
            elif is_local_action(r["action"]):
                a["local"] += r.get("all_conversions", 0)
        return {w.folder: dict(acc[w.monday.isoformat()]) for w in weeks}

    def campaigns(self, venue: dict, week: Week) -> list[dict]:
        fx = venue.get("google_fx", 1.0)
        rule = venue.get("google_actions")
        by = {}
        for r in self._cost_rows(venue, week.monday, week.sunday):
            c = by.setdefault(r["campaign_id"], {"id": r["campaign_id"], "name": r["campaign"], "platform": "Google",
                                                 "spend": 0.0, "bookings": 0.0})
            c["spend"] += r["cost"] * fx
        for r in self._conv_rows(venue, week.monday, week.sunday):
            if r["campaign_id"] in by and is_booking_action(r["action"], rule):
                by[r["campaign_id"]]["bookings"] += r["conversions"]
        return list(by.values())
