#!/usr/bin/env python3
# London daily covers & bookings report.  Usage: daily_gen.py <payload.json> <out.html>
# Prints a JSON run-summary (alerts, portfolio numbers) on stdout for the run report / email draft.
#
# Payload contract (all series are 35 ints, oldest first, index 34 = reporting day):
#   {reporting_day, generated, dates:[35 ISO], notes:[str],
#    suppressed:{"<row name>":["YYYY-MM-DD", ...]},
#    venues:[{name, sr:[...], ga4:[...],
#             covers, web, widget, gr, ot, walk, recep, other, staff, bookings, users}]}
#
# Definitions (locked 8 Sep 2026, matching the weekly covers report _tools/covers_gen.py):
#   Covers        = SUM(covers) by booking-created date, Europe/London, is_deleted false,
#                   status_simple <> 'Canceled', seating area not ILIKE '%bar%'.
#   Website (web) = Booking Widget + '%Landing Page%' + Nav CTA + Hero CTA + Menu Page
#                   + 'Website' + PPC% + campaign tags (popup, edm).
#   Staff-name booking sources are EXCLUDED from covers entirely, not bucketed.
#   Alerts run on Website covers, NOT raw 'Booking Widget'.  Aqua Shard re-tagged its widget
#   traffic into named landing pages on 21 Aug 2026, so the raw widget series has a break
#   there and would fire a permanent false red.  Widget is still shown, for visibility.
import json, sys, statistics as st

P = json.load(open(sys.argv[1])); OUT = sys.argv[2]
D = P['dates']; RD = P['reporting_day']; N = len(D)
TREND = list(range(N - 7, N))              # last 7 days
SUPP = P.get('suppressed', {})
BAND = 0.20; MIX_PP = 10.0

SERIES = [('covers', 'Total covers'), ('web', 'Website covers'), ('bookings', 'GA4 bookings')]


def baseline(v, i):
    """Median of the same weekday over the 4 preceding weeks."""
    xs = [v[i - k] for k in (7, 14, 21, 28) if i - k >= 0]
    return st.median(xs) if xs else None


def below(val, base):
    return base is not None and base > 0 and val < base * (1 - BAND)


def assess(v, name, row):
    """Longest current run of below-band days ending on the reporting day, plus status."""
    supp = set(SUPP.get(row, []))
    run = 0
    for i in range(N - 1, N - 8, -1):
        if D[i] in supp:
            break
        if below(v[i], baseline(v, i)):
            run += 1
        else:
            break
    b = baseline(v, N - 1)
    cliff = b is not None and b > 0 and v[N - 1] < b * 0.5 and D[N - 1] not in supp
    status = 'red' if (run >= 3 or cliff) else ('amber' if run == 2 else 'green')
    return {'series': name, 'run': run, 'cliff': cliff, 'status': status,
            'value': v[N - 1], 'base': b}


def mix_alert(vn):
    """Website share more than 10pp under its own weekday baseline share, 2 days running."""
    supp = set(SUPP.get(vn['name'], []))
    share = [(vn['web'][i] / vn['covers'][i] * 100.0) if vn['covers'][i] else None for i in range(N)]
    def basesh(i):
        xs = [share[i - k] for k in (7, 14, 21, 28) if i - k >= 0 and share[i - k] is not None]
        return st.median(xs) if xs else None
    run = 0
    for i in range(N - 1, N - 8, -1):
        if D[i] in supp or share[i] is None:
            break
        bs = basesh(i)
        if bs is not None and share[i] < bs - MIX_PP:
            run += 1
        else:
            break
    return {'run': run, 'share': share[N - 1], 'base': basesh(N - 1),
            'status': 'amber' if run >= 2 else 'green'}


RANK = {'green': 0, 'amber': 1, 'red': 2}
rows = []
for v in P['venues']:
    a = [assess(v[k], lab, v['name']) for k, lab in SERIES]
    m = mix_alert(v)
    worst = max([x['status'] for x in a] + [m['status']], key=lambda s: RANK[s])
    rows.append({'v': v, 'a': {x['series']: x for x in a}, 'mix': m, 'status': worst})

TCOV = sum(v['covers'][N - 1] for v in P['venues'])
TWEB = sum(v['web'][N - 1] for v in P['venues'])
TBK = sum(v['bookings'][N - 1] for v in P['venues'])
def portbase(key):
    tot = [sum(v[key][i] for v in P['venues']) for i in range(N)]
    return baseline(tot, N - 1)
BCOV, BWEB, BBK = portbase('covers'), portbase('web'), portbase('bookings')

# ---------------------------------------------------------------- html helpers
def pct(c, b):
    return None if not b else (c - b) / b * 100.0

def chip(p):
    if p is None:
        return '<span class="d na">n/a</span>'
    cls = 'flat' if abs(p) < 5 else ('up' if p > 0 else 'down')
    return f'<span class="d {cls}">{"+" if p >= 0 else ""}{p:.0f}%</span>'

def alertchip(s, txt):
    return f'<span class="chip c-{s}">{txt}</span>'

def fmt(x):
    return f'{x:,.0f}' if x is not None else '–'

def spark(vals, dates, colour):
    """Hand-rolled SVG: value line + dashed weekday-baseline line. No CDN."""
    idx = TREND
    vs = [vals[i] for i in idx]
    bs = [baseline(vals, i) or 0 for i in idx]
    hi = max(vs + bs + [1]); lo = 0.0
    W, H, PADL, PADB, PADT = 268.0, 66.0, 4.0, 14.0, 6.0
    def X(k): return PADL + k * (W - 2 * PADL) / 6.0
    def Y(val): return PADT + (1 - (val - lo) / (hi - lo)) * (H - PADT - PADB)
    line = ' '.join(f'{X(k):.1f},{Y(v):.1f}' for k, v in enumerate(vs))
    bline = ' '.join(f'{X(k):.1f},{Y(b):.1f}' for k, b in enumerate(bs))
    dots = ''.join(
        f'<circle cx="{X(k):.1f}" cy="{Y(v):.1f}" r="{3.1 if k == 6 else 2.1}" fill="'
        f'{"#dc2626" if below(v, bs[k] or None) else colour}"/>' for k, v in enumerate(vs))
    labs = ''.join(
        f'<text x="{X(k):.1f}" y="{H - 3:.0f}" text-anchor="middle" font-size="8" fill="#94a3b8" '
        f'font-family="JetBrains Mono,monospace">{dates[i][8:10]}</text>' for k, i in enumerate(idx))
    return (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" height="{H:.0f}" '
            f'preserveAspectRatio="none" role="img">'
            f'<polyline points="{bline}" fill="none" stroke="#cbd5e1" stroke-width="1.2" '
            f'stroke-dasharray="4 3"/>'
            f'<polyline points="{line}" fill="none" stroke="{colour}" stroke-width="1.8"/>'
            f'{dots}{labs}</svg>')

# ---------------------------------------------------------------- alert strip
# Portfolio-level check. A day where every venue slips a little shows up here but crosses
# no venue's consecutive-day rule, so it would otherwise go unsaid.
PORT = []
for lab, cur, base in (('covers created', TCOV, BCOV), ('GA4 bookings', TBK, BBK)):
    if base and cur < base * (1 - BAND):
        PORT.append(f'<b>London portfolio {lab}</b> {cur:,} against a weekday baseline of '
                    f'{fmt(base)}, {pct(cur, base):.0f}%')

flagged = [r for r in rows if r['status'] != 'green']
flagged.sort(key=lambda r: -RANK[r['status']])
if flagged or PORT:
    items = ''.join(f'<li>{alertchip("amber", "PORTFOLIO")} {x}</li>' for x in PORT)
    for r in flagged:
        bits = []
        for _, lab in SERIES:
            a = r['a'][lab]
            if a['status'] == 'green':
                continue
            why = 'single day under half baseline' if a['cliff'] and a['run'] < 3 \
                else f'{a["run"]} day{"s" if a["run"] != 1 else ""} below band'
            bits.append(f'<b>{lab.lower()}</b> {why} ({fmt(a["value"])} vs {fmt(a["base"])} baseline)')
        if r['mix']['status'] != 'green':
            bits.append(f'<b>channel shift</b> website share {r["mix"]["share"]:.0f}% vs '
                        f'{r["mix"]["base"]:.0f}% baseline, {r["mix"]["run"]} days')
        items += (f'<li>{alertchip(r["status"], r["status"].upper())} '
                  f'<b>{r["v"]["name"]}</b> — ' + '; '.join(bits) + '</li>')
    STRIP = f'<div class="alerts"><ul>{items}</ul></div>'
else:
    STRIP = '<div class="clean">No venue outside its band.</div>'

# ---------------------------------------------------------------- venue table
trows = ''
for r in rows:
    v = r['v']; i = N - 1
    cov, web, wid = v['covers'][i], v['web'][i], v['widget'][i]
    gr, ot, oth = v['gr'][i], v['ot'][i], v['walk'][i] + v['recep'][i] + v['other'][i]
    bk, us = v['bookings'][i], v['users'][i]
    cvr = (bk / us * 100.0) if us else None
    sh = (web / cov * 100.0) if cov else 0
    cvrtxt = f'{cvr:.1f}%' if cvr is not None else '\u2013'
    trows += (
        f'<tr><td class="vn">{v["name"]}</td>'
        f'<td class="num"><b>{cov:,}</b><div class="chips">{chip(pct(cov, r["a"]["Total covers"]["base"]))}</div></td>'
        f'<td class="num">{web:,}<div class="chips">{chip(pct(web, r["a"]["Website covers"]["base"]))}</div></td>'
        f'<td class="num mut">{wid:,}</td>'
        f'<td class="num">{gr:,}</td><td class="num">{ot:,}</td><td class="num">{oth:,}</td>'
        f'<td class="num">{sh:.0f}%</td>'
        f'<td class="num">{bk:,}<div class="chips">{chip(pct(bk, r["a"]["GA4 bookings"]["base"]))}</div></td>'
        f'<td class="num mut">{cvrtxt}</td>'
        f'<td>{alertchip(r["status"], r["status"].upper())}</td></tr>')

trows += (f'<tr class="total"><td class="vn">London portfolio</td>'
          f'<td class="num">{TCOV:,}<div class="chips">{chip(pct(TCOV, BCOV))}</div></td>'
          f'<td class="num">{TWEB:,}<div class="chips">{chip(pct(TWEB, BWEB))}</div></td>'
          f'<td class="num mut">{sum(v["widget"][N-1] for v in P["venues"]):,}</td>'
          f'<td class="num">{sum(v["gr"][N-1] for v in P["venues"]):,}</td>'
          f'<td class="num">{sum(v["ot"][N-1] for v in P["venues"]):,}</td>'
          f'<td class="num">{sum(v["walk"][N-1]+v["recep"][N-1]+v["other"][N-1] for v in P["venues"]):,}</td>'
          f'<td class="num">{TWEB/TCOV*100:.0f}%</td>'
          f'<td class="num">{TBK:,}<div class="chips">{chip(pct(TBK, BBK))}</div></td>'
          f'<td class="num mut">–</td><td></td></tr>')

# ---------------------------------------------------------------- 7-day panels
panels = ''
for r in rows:
    v = r['v']
    panels += (f'<div class="panel"><div class="pt">{v["name"]} '
               f'{alertchip(r["status"], r["status"].upper())}</div>'
               f'<div class="pg"><div><div class="pl">Covers</div>{spark(v["covers"], D, "#2563eb")}</div>'
               f'<div><div class="pl">Website covers</div>{spark(v["web"], D, "#0ea5e9")}</div>'
               f'<div><div class="pl">GA4 bookings</div>{spark(v["bookings"], D, "#8b5cf6")}</div>'
               f'</div></div>')

NOTES = ''.join(f'<li>{n}</li>' for n in P.get('notes', []))
SUPPTXT = '; '.join(f'{k}: {", ".join(vv)}' for k, vv in SUPP.items()) or 'none'

HTML = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua London — Daily Covers &amp; Bookings — {RD}</title>
<style>@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',system-ui,sans-serif;background:#fff;color:#0f172a;line-height:1.5;padding:28px;max-width:1340px;margin:0 auto}}
a.back{{font-size:12px;color:#2563eb;text-decoration:none}}
h1{{font-size:24px;font-weight:700;margin-top:8px;letter-spacing:-.3px}}
.sub{{color:#64748b;font-size:13px;margin-top:4px}}
.num{{font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums}}
.alerts{{background:#fffbeb;border:1px solid #fde68a;border-left:3px solid #f59e0b;border-radius:10px;padding:14px 16px 14px 18px;margin:18px 0;font-size:13.5px;color:#1e293b}}
.alerts ul{{margin:0;padding-left:16px}} .alerts li{{margin:5px 0;line-height:1.5}}
.clean{{background:#f0fdf4;border:1px solid #bbf7d0;border-left:3px solid #16a34a;border-radius:10px;padding:13px 16px;margin:18px 0;font-size:13.5px;font-weight:600;color:#14532d}}
.chip{{display:inline-block;font-size:9.5px;font-weight:700;letter-spacing:.4px;padding:2px 6px;border-radius:5px;font-family:'JetBrains Mono',monospace}}
.c-green{{color:#16a34a;background:#ecfdf3}}.c-amber{{color:#b45309;background:#fffbeb}}.c-red{{color:#dc2626;background:#fef2f2}}.c-blue{{color:#2563eb;background:#eff6ff}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}}
.kpi{{border:1px solid #e2e8f0;border-radius:12px;padding:14px 15px;background:#fafafa}}
.kpi .lab{{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#64748b;font-weight:600}}
.kpi .big{{font-size:24px;font-weight:700;margin-top:5px;font-family:'JetBrains Mono',monospace}}
.kpi .meta{{font-size:11.5px;color:#475569;margin-top:6px}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}}
th,td{{padding:8px 6px;text-align:right;border-bottom:1px solid #eef2f6;white-space:nowrap;vertical-align:middle}}
th:first-child,td:first-child{{text-align:left}}
thead th{{font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:#64748b;border-bottom:2px solid #e2e8f0;vertical-align:bottom}}
td.vn{{font-weight:600}} .chips{{margin-top:2px}}
tr.total{{font-weight:700;background:#f1f5f9}} tr.total td{{border-top:2px solid #cbd5e1}}
.mut{{color:#94a3b8}}
.d{{font-size:9.5px;font-weight:600;padding:1px 4px;border-radius:5px;font-family:'JetBrains Mono',monospace}}
.up{{color:#16a34a;background:#ecfdf3}}.down{{color:#dc2626;background:#fef2f2}}.flat{{color:#475467;background:#f2f4f7}}.na{{color:#98a2b3;background:#f8fafc}}
.sec{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;margin:28px 0 8px;border-bottom:1px solid #eef2f6;padding-bottom:6px}}
.panels{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}}
.panel{{border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px}}
.pt{{font-size:13px;font-weight:700;margin-bottom:8px}}
.pg{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
.pl{{font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:#94a3b8;font-weight:700;margin-bottom:2px}}
footer{{margin-top:30px;color:#94a3b8;font-size:11px;border-top:1px solid #eef2f6;padding-top:12px;line-height:1.6}}
footer ul{{margin:6px 0 0 16px}}
@media(max-width:1000px){{.panels,.cards{{grid-template-columns:1fr}}}}
</style></head><body>
<a class="back" href="../index.html">← All London reports</a>
<h1>Aqua London — Daily Covers &amp; Bookings</h1>
<div class="sub">{RD} · covers by booking-created date · Europe/London</div>

{STRIP}

<div class="cards">
<div class="kpi"><div class="lab">Covers created</div><div class="big">{TCOV:,}</div>
<div class="meta">weekday baseline {fmt(BCOV)} · {chip(pct(TCOV, BCOV))}</div></div>
<div class="kpi"><div class="lab">GA4 bookings</div><div class="big">{TBK:,}</div>
<div class="meta">weekday baseline {fmt(BBK)} · {chip(pct(TBK, BBK))}</div></div>
<div class="kpi"><div class="lab">Website share of covers</div><div class="big">{TWEB/TCOV*100:.0f}%</div>
<div class="meta">{TWEB:,} website covers · baseline {fmt(BWEB)} · {chip(pct(TWEB, BWEB))}</div></div>
</div>

<div class="sec">By venue — {RD}</div>
<table><thead><tr><th>Venue</th><th>Covers</th><th>Website</th><th>of which widget</th>
<th>Google Reserve</th><th>OpenTable</th><th>Other</th><th>Web share</th>
<th>GA4 bookings</th><th>Conv rate</th><th>Alert</th></tr></thead><tbody>{trows}</tbody></table>
<div class="sub" style="margin-top:8px;font-size:11.5px">Variance chips compare the day with the median of the same weekday over the four preceding weeks. Other = walk-in, reception and third party.</div>

<div class="sec">Seven days to {RD} — solid line is actual, dashed is the weekday baseline</div>
<div class="panels">{panels}</div>

<footer>
<b>Method.</b> Covers = SUM(covers) from SevenRooms via Supabase, bucketed by booking-created date in Europe/London, excluding deleted and cancelled bookings and bar seating areas. Staff-name booking sources are excluded from covers entirely. Website = Booking Widget plus all landing pages, Nav and Hero CTAs, the menu page, PPC and campaign tags; the widget column is a subset of it, shown separately. GA4 bookings = event sevenrooms_booking_complete. Regent St combines Aqua Kyoto and Aqua Nueva.
<ul>
<li>Baseline for each day is the median of that same weekday across the four preceding weeks. Band is baseline plus or minus 20 percent. Red is three or more consecutive days below the band, or a single day under half baseline. Amber is two consecutive days.</li>
<li>Alerts run on Website covers, not on the raw Booking Widget source. Aqua Shard re-tagged widget traffic into named landing pages on 21 Aug 2026, so the raw widget series has a definition break there.</li>
<li>Google conversions and GA4 channel data are deliberately absent: both settle over two to three days and cannot be read on a daily cadence.</li>
<li>Covers re-settle downward as cancellations accrue, so the full 35-day window is re-pulled every morning rather than carried forward.</li>
<li>Suppressed dates (closures and known buyouts): {SUPPTXT}.</li>
{NOTES}
</ul>
Generated {P['generated']}.
</footer></body></html>'''

open(OUT, 'w').write(HTML)

summary = {
    'reporting_day': RD,
    'portfolio': {'covers': TCOV, 'covers_baseline': BCOV, 'website': TWEB,
                  'website_baseline': BWEB, 'bookings': TBK, 'bookings_baseline': BBK,
                  'web_share': round(TWEB / TCOV * 100, 1)},
    'portfolio_alert': [x.replace('<b>','').replace('</b>','') for x in PORT],
    'alerts': [{'venue': r['v']['name'], 'status': r['status'],
                'series': {k: {kk: vv for kk, vv in a.items() if kk != 'series'}
                           for k, a in r['a'].items() if a['status'] != 'green'},
                'mix': r['mix'] if r['mix']['status'] != 'green' else None}
               for r in flagged],
    'out': OUT,
}
print(json.dumps(summary, indent=1, default=float))
