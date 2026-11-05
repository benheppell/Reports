"""Shared helpers for turning a facts file into report payloads."""
from __future__ import annotations

import re
from datetime import date

from ..dates import Week, fy_week_no, week_target

FLAT = 1.5  # change chips call anything under 1.5% flat


def num(x, nd=0):
    if x is None:
        return None
    return round(x) if nd == 0 else round(x, nd)


def pct(cur, base):
    if cur is None or base in (None, 0):
        return None
    return (cur - base) / base * 100


def fmt_int(x) -> str:
    return "n/a" if x is None else f"{round(x):,}"


def fmt_pct(p, signed=True) -> str:
    if p is None:
        return "n/a"
    return f"{p:+.1f}%" if signed else f"{p:.1f}%"


def direction(p, flat=FLAT) -> str:
    if p is None:
        return "flat"
    return "flat" if abs(p) < flat else ("up" if p > 0 else "down")


def words(p, flat=FLAT) -> str:
    """'up 6.3 per cent' / 'down 11.7 per cent' / 'flat'."""
    if p is None:
        return "not comparable"
    if abs(p) < flat:
        return "flat"
    return f"{'up' if p > 0 else 'down'} {abs(p):.1f} per cent"


def md(s: str) -> str:
    """Override text allows **bold**; pages take HTML."""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)


def no_dashes(s: str) -> str:
    """House style: no em dashes in generated text."""
    return s.replace("—", ":").replace("&mdash;", ":")


class Ctx:
    """Everything a builder needs: market config, facts, the week, targets and overrides."""

    def __init__(self, market: dict, defaults: dict, facts: dict, week: Week, targets: dict, overrides: dict,
                 generated: date):
        self.m, self.d, self.f, self.w = market, defaults, facts, week
        self.targets = targets.get(market["slug"], {})
        self.ov = overrides
        self.generated = generated
        self.weeks8 = week.back(8)

    # ---------------------------------------------------------------- config views
    @property
    def venues(self):
        return self.m["venue"]

    def portfolio(self):
        return [v for v in self.venues if not v.get("outside")]

    def outside(self):
        return [v for v in self.venues if v.get("outside")]

    def vf(self, name):
        return self.f["venues"].get(name) or {}

    def wk_no(self, w: Week) -> int:
        return fy_week_no(w.monday, self.m["fy_start_month"])

    # ---------------------------------------------------------------- withholding
    def withheld(self, venue: str, source: str, w: Week) -> str | None:
        for o in self.ov.get("withhold", []):
            if o["market"] != self.m["slug"] or o["venue"] != venue or o["source"] != source:
                continue
            if w.folder >= o["from"] and (not o.get("until") or w.folder <= o["until"]):
                return o.get("reason", "withheld")
        return None

    def week_notes(self) -> list[str]:
        return [md(n["text"]) for n in self.ov.get("note", [])
                if n["market"] == self.m["slug"] and n["week"] == self.w.folder]

    # ---------------------------------------------------------------- figures
    def ga4(self, name, w: Week):
        if self.withheld(name, "ga4_bookings", w):
            return None
        g = self.vf(name).get("ga4_book")
        return None if g is None else g.get(w.folder)

    def web(self, name, w: Week):
        g = self.vf(name).get("web")
        return None if g is None else g.get(w.folder)

    def _ads(self, name, plat, w):
        g = self.vf(name).get(plat)
        return None if g is None else g.get(w.folder)

    def meta(self, name, w: Week):
        return self._ads(name, "meta", w)

    def google(self, name, w: Week):
        return self._ads(name, "google", w)

    def meta_bookings(self, name, w):
        a = self.meta(name, w)
        if a is None or self.withheld(name, "meta_bookings", w):
            return None
        return a["bookings"]

    def google_bookings(self, name, w):
        v = self.venue(name)
        a = self.google(name, w)
        if a is None or v.get("google_excluded") or self.withheld(name, "google_bookings", w):
            return None
        return a["bookings"]

    def spend(self, name, plat, w):
        a = self._ads(name, plat, w)
        return None if a is None else a["spend"]

    def venue(self, name):
        return next(v for v in self.venues if v["name"] == name)

    def is_shared_copy(self, name) -> bool:
        """True for the second and later rows that share one ad account: show its spend once."""
        v = self.venue(name)
        return bool(v.get("shared_ads")) and self.f.get("shared_owner", {}).get(v["shared_ads"]) != name

    def is_shared(self, name) -> bool:
        return bool(self.venue(name).get("shared_ads"))

    # ---------------------------------------------------------------- targets
    def monthly_targets(self, key):
        return self.targets.get(key) or {}

    def tgt(self, key, w: Week | None = None):
        t = week_target(self.monthly_targets(key), w or self.w)
        return None if t is None else round(t)

    def ytd_tgt(self, key):
        from ..dates import fy_w1
        w1 = fy_w1(self.w.monday, self.m["fy_start_month"])
        n = (self.w.monday - w1).days // 7 + 1
        total = 0.0
        for w in self.w.back(n):
            t = week_target(self.monthly_targets(key), w)
            if t is None:
                return None
            total += t
        return round(total)
