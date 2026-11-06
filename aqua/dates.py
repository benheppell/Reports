"""Week and calendar arithmetic shared by every report.

Reporting week: Monday to Sunday that has fully ended. Folder w<YYYY-MM-DD> is that Monday.
Prior week: the 7 days before. Year on year: minus 364 days, so weekdays line up.
FY week: W1 is the first Monday on or after the FY start (1 Feb or 1 Jan).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_LONG = list(calendar.month_name)[1:]
EN_DASH = "–"


def last_completed_monday(today: date) -> date:
    """Monday of the most recent Monday-to-Sunday week whose Sunday has passed."""
    this_monday = today - timedelta(days=today.weekday())
    return this_monday - timedelta(days=7)


def fy_start(d: date, fy_start_month: int) -> date:
    y = d.year if d.month >= fy_start_month else d.year - 1
    return date(y, fy_start_month, 1)


def fy_w1(d: date, fy_start_month: int) -> date:
    s = fy_start(d, fy_start_month)
    return s + timedelta(days=(7 - s.weekday()) % 7)


def fy_week_no(monday: date, fy_start_month: int) -> int:
    w1 = fy_w1(monday, fy_start_month)
    if monday < w1:  # the stub days before W1 belong to the previous FY's numbering
        w1 = fy_w1(w1 - timedelta(days=1), fy_start_month)
    return (monday - w1).days // 7 + 1


def fy_label(monday: date, fy_start_month: int) -> str:
    """FY26 for the year starting Feb 2026 (or Jan 2026)."""
    return f"FY{fy_start(monday, fy_start_month).year % 100:02d}"


def range_label(start: date, end: date, year: bool = True) -> str:
    """'5–11 Oct 2026' within a month, '28 Sep–4 Oct 2026' across months."""
    y = f" {end.year}" if year else ""
    if start.month == end.month:
        return f"{start.day}{EN_DASH}{end.day} {MONTHS[end.month - 1]}{y}"
    sy = f" {start.year}" if year and start.year != end.year else ""
    return f"{start.day} {MONTHS[start.month - 1]}{sy}{EN_DASH}{end.day} {MONTHS[end.month - 1]}{y}"


def long_date(d: date) -> str:
    return f"{d.day} {MONTHS_LONG[d.month - 1]} {d.year}"


@dataclass(frozen=True)
class Week:
    monday: date

    @property
    def sunday(self) -> date:
        return self.monday + timedelta(days=6)

    @property
    def prior(self) -> "Week":
        return Week(self.monday - timedelta(days=7))

    @property
    def yoy(self) -> "Week":
        return Week(self.monday - timedelta(days=364))

    @property
    def folder(self) -> str:
        return f"w{self.monday.isoformat()}"

    def back(self, n: int) -> list["Week"]:
        """This week and the n-1 before it, oldest first."""
        return [Week(self.monday - timedelta(days=7 * i)) for i in range(n - 1, -1, -1)]

    def label(self, year: bool = True) -> str:
        return range_label(self.monday, self.sunday, year)

    def days(self) -> list[date]:
        return [self.monday + timedelta(days=i) for i in range(7)]


def week_target(monthly: dict[str, float], week: Week) -> float | None:
    """Prorate monthly targets onto a week.

    From w2026-09-28: a week that straddles two months takes each month's figure divided by the
    days in that month, times the days of the week falling in it. A week wholly inside one month
    stays on the standing month x 7/30 convention. `monthly` is keyed 'YYYY-MM'.
    """
    d0, d1 = week.monday, week.sunday
    k0, k1 = d0.strftime("%Y-%m"), d1.strftime("%Y-%m")
    if k0 == k1:
        m = monthly.get(k0)
        return None if m is None else m * 7 / 30
    total = 0.0
    for d in week.days():
        m = monthly.get(d.strftime("%Y-%m"))
        if m is None:
            return None
        total += m / calendar.monthrange(d.year, d.month)[1]
    return total


def week_basis_note(week: Week) -> str:
    if week.monday.month == week.sunday.month:
        return "The weekly target is the monthly target x 7/30, the standing convention for a week inside one month."
    n0 = sum(1 for d in week.days() if d.month == week.monday.month)
    return (
        f"This week straddles a month boundary, so the weekly target is prorated by days in each month: "
        f"{MONTHS_LONG[week.monday.month - 1]} / {calendar.monthrange(week.monday.year, week.monday.month)[1]} x {n0} "
        f"plus {MONTHS_LONG[week.sunday.month - 1]} / {calendar.monthrange(week.sunday.year, week.sunday.month)[1]} x {7 - n0}."
    )
