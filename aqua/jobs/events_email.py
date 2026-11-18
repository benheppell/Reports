"""Email the London events report as a PDF: monthly (last month) and weekly (last ISO week).

    python -m aqua.jobs.events_email --period month            # last complete month
    python -m aqua.jobs.events_email --period week             # last complete Monday-Sunday week
    python -m aqua.jobs.events_email --period month --date 2026-10-01 --send

Without --send it renders the PDF to out/ and stops (a dry run). The emailed copy carries the team
conversion table, which the public page never shows. This repo is public, so the PDF is never
uploaded as a build artifact and no team figure is ever printed to the log.

Needs SUPABASE_DB_URL, and to send: EVENTS_REPORT_FROM (the work mailbox it sends as) and EVENTS_REPORT_TO
(comma-separated addresses), plus an Entra ID (Azure AD) app registration with the Mail.Send application
permission: MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET. Mail goes out through Microsoft Graph as that
mailbox and lands in its Sent Items. All of these live in GitHub secrets, not in the repo.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "london" / "events" / "index.html"
SITE = "https://aquareports.netlify.app/london/events/"
MON = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def period(kind: str, on: date | None) -> tuple[date, date]:
    """[start, end) of the period holding `on`, or of the last complete period before today."""
    today = datetime.now(ZoneInfo("Europe/London")).date()
    if kind == "week":
        ref = on or (today - timedelta(days=7))
        start = ref - timedelta(days=ref.weekday())
        return start, start + timedelta(days=7)
    ref = on or (today.replace(day=1) - timedelta(days=1))
    start = ref.replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1)
    return start, end


def payload(start: date, end: date, kind: str) -> dict:
    from ..sources.sevenrooms import SevenRooms
    rows = SevenRooms().query("select public.events_report_period(%s, %s, %s, true)", (start, end, kind))
    p = rows[0][0]
    return p if isinstance(p, dict) else json.loads(p)


def render_pdf(p: dict, out: Path) -> None:
    from playwright.sync_api import sync_playwright
    html = PAGE.read_text()
    q = f"week={p['start']}" if p["kind"] == "week" else f"month={p['month']}"
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 900})
        errors: list[str] = []
        pg.on("pageerror", lambda e: errors.append(str(e)))

        def route(r):
            u = r.request.url
            if "events-report" in u:
                return r.fulfill(status=200, content_type="application/json", body=json.dumps(p, default=str))
            if u.startswith("http://report.local/"):
                return r.fulfill(status=200, content_type="text/html", body=html)
            if "fonts.g" in u:
                return r.continue_()
            return r.abort()
        pg.route("**/*", route)
        pg.goto(f"http://report.local/london/events/?{q}")
        pg.wait_for_selector("table", timeout=30000)
        # The back link and pickers mean nothing on paper.
        pg.add_style_tag(content="a.back,.pick,button.copy{display:none!important}body{padding:0 8px}"
                                 ".sec{break-inside:avoid}")
        pg.wait_for_timeout(500)
        if errors:
            raise RuntimeError(f"page errors: {errors}")
        pg.pdf(path=str(out), format="A4", landscape=True, print_background=True, scale=0.72,
               margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"})
        b.close()


def label(p: dict) -> str:
    s = date.fromisoformat(str(p["start"]))
    if p["kind"] == "week":
        return f"w/c {s.day} {MON[s.month - 1]} {s.year}"
    return f"{MON[s.month - 1]} {s.year}"


def headline(p: dict) -> list[str]:
    def tot(key, y, f, flt=lambda r: True):
        return sum(float(r.get(f) or 0) for r in (p.get(key) or []) if r.get("y") == y and flt(r))

    def chg(a, b):
        return "" if not b else f" ({'up' if a >= b else 'down'} {abs(a - b) / b * 100:.0f}% on last year)"

    def k(v):
        return f"£{v / 1e6:.2f}m" if v >= 1e6 else f"£{v / 1e3:,.0f}k"
    e, el = tot("enquiries", "ty", "month_n"), tot("enquiries", "ly", "month_n")
    c, cl = tot("confirmed", "ty", "val"), tot("confirmed", "ly", "val")
    h, hl = tot("held_period", "ty", "val"), tot("held_period", "ly", "val")
    le = tot("lost", "ty", "n", lambda r: r["kind"] == "enquiry")
    lb = tot("lost", "ty", "n", lambda r: r["kind"] == "booking")
    fy = p.get("full_year") or []
    fc = sum(float(r.get("done_val") or 0) + float(r.get("up_fc") or 0) for r in fy)
    target = sum(float(t.get("target") or 0) for t in (p.get("targets") or []))
    return [f"Enquiries: {e:,.0f}{chg(e, el)}",
            f"Bookings confirmed: {k(c)}{chg(c, cl)}",
            f"Events held: {k(h)}{chg(h, hl)}",
            f"Lost: {le:,.0f} enquiries and {lb:,.0f} confirmed bookings",
            f"{p['fy_label']} forecast: {k(fc)}" + (f", {fc / target * 100:.0f}% of the {k(target)} target" if target else "")]


def body(p: dict) -> tuple[str, str]:
    lab = label(p)
    link = SITE + (f"?week={p['start']}" if p["kind"] == "week" else f"?month={p['month']}")
    lines = "".join(f"<p style='margin:0 0 6px'>{x}</p>" for x in headline(p))
    html = (f"<div style='font-family:Arial,sans-serif;font-size:14px;color:#0f172a'>"
            f"<p>London events report, {lab}. The full report is attached, including team conversion by site.</p>"
            f"{lines}<p style='margin-top:14px'>Live version (without the team table): <a href='{link}'>{link}</a></p>"
            f"<p style='color:#64748b;font-size:12px'>From Tripleseat, net of VAT. Lost reasons and actual spend "
            f"are only as good as what is entered in Tripleseat.</p></div>")
    return f"Events report | {lab}", html


def send(p: dict, pdf: Path) -> None:
    """Send as the work mailbox through Microsoft Graph (app-only token, Mail.Send)."""
    import requests
    to = [a.strip() for a in os.environ["EVENTS_REPORT_TO"].split(",") if a.strip()]
    sender = os.environ["EVENTS_REPORT_FROM"].strip()
    tok = requests.post(
        f"https://login.microsoftonline.com/{os.environ['MS_TENANT_ID'].strip()}/oauth2/v2.0/token", timeout=30,
        data={"grant_type": "client_credentials", "client_id": os.environ["MS_CLIENT_ID"].strip(),
              "client_secret": os.environ["MS_CLIENT_SECRET"].strip(), "scope": "https://graph.microsoft.com/.default"})
    if tok.status_code != 200:
        raise RuntimeError(f"Microsoft sign-in failed ({tok.status_code}): {tok.text[:300]}")
    subject, html = body(p)
    msg = {"message": {
        "subject": subject,
        "body": {"contentType": "HTML", "content": html},
        "toRecipients": [{"emailAddress": {"address": a}} for a in to],
        "attachments": [{"@odata.type": "#microsoft.graph.fileAttachment", "name": pdf.name,
                         "contentType": "application/pdf",
                         "contentBytes": base64.b64encode(pdf.read_bytes()).decode()}]},
        "saveToSentItems": True}
    r = requests.post(f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail", json=msg, timeout=60,
                      headers={"Authorization": f"Bearer {tok.json()['access_token']}"})
    if r.status_code != 202:
        raise RuntimeError(f"Outlook send failed ({r.status_code}): {r.text[:300]}")
    print(f"sent to {len(to)} recipient(s)")


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--period", choices=["month", "week"], required=True)
    a.add_argument("--date", type=date.fromisoformat)
    a.add_argument("--send", action="store_true")
    a.add_argument("--test", action="store_true", help="send only to the sending mailbox, not the recipient list")
    args = a.parse_args()
    start, end = period(args.period, args.date)
    p = payload(start, end, args.period)
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    pdf = out / f"Aqua London events report {label(p)}.pdf"
    render_pdf(p, pdf)
    # Headline totals only: no names reach the log.
    print(f"{args.period} {start} to {end - timedelta(days=1)}: {pdf.name} ({pdf.stat().st_size // 1024} KB)")
    for line in headline(p):
        print(" ", line)
    if not args.send:
        return 0
    missing = [k for k in ("MS_TENANT_ID", "MS_CLIENT_ID", "MS_CLIENT_SECRET", "EVENTS_REPORT_FROM", "EVENTS_REPORT_TO")
               if not os.environ.get(k, "").strip()]
    if missing:
        print(f"not sent: set {', '.join(missing)} as GitHub secrets")
        return 1
    if args.test:
        os.environ["EVENTS_REPORT_TO"] = os.environ["EVENTS_REPORT_FROM"]
        print("test: sending to the sending mailbox only")
    send(p, pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
