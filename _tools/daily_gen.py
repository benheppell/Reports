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
#   there and would fire a permanent false red.  Widget is carried but not displayed.
#   Walk-in is shown but never alerted on: it is footfall, not a channel we run.
import json, sys, datetime as dt, statistics as st

P = json.load(open(sys.argv[1])); OUT = sys.argv[2]
D = P['dates']; RD = P['reporting_day']; N = len(D)
SUPP = P.get('suppressed', {})
BAND = 0.20; MIX_PP = 10.0

SERIES = [('covers', 'Covers'), ('web', 'Website'), ('bookings', 'GA4 bookings')]
INK, ALERT, GRID, BANDFILL, SURF = '#2563eb', '#dc2626', '#94a3b8', '#eef2f7', '#ffffff'


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
        if D[i] in supp or not below(v[i], baseline(v, i)):
            break
        run += 1
    b = baseline(v, N - 1)
    cliff = b is not None and b > 0 and v[N - 1] < b * 0.5 and D[N - 1] not in supp
    status = 'red' if (run >= 3 or cliff) else ('amber' if run == 2 else ('blue' if run == 1 else 'green'))
    return {'series': name, 'run': run, 'cliff': cliff, 'status': status,
            'value': v[N - 1], 'base': b, 'floor': (b * (1 - BAND)) if b else None}


def mix_alert(vn):
    """Website share more than 10pp under its own weekday baseline share, 2 days running."""
    supp = set(SUPP.get(vn['name'], []))
    share = [(vn['web'][i] / vn['covers'][i] * 100.0) if vn['covers'][i] else None for i in range(N)]

    def basesh(i):
        xs = [share[i - k] for k in (7, 14, 21, 28) if i - k >= 0 and share[i - k] is not None]
        return st.median(xs) if xs else None
    run = 0
    for i in range(N - 1, N - 8, -1):
        bs = basesh(i)
        if D[i] in supp or share[i] is None or bs is None or share[i] >= bs - MIX_PP:
            break
        run += 1
    return {'run': run, 'share': share[N - 1], 'base': basesh(N - 1),
            'status': 'amber' if run >= 2 else ('blue' if run == 1 else 'green')}


# alert statuses only; 'blue' means one day in, which is watch-not-alert
RANK = {'green': 0, 'blue': 1, 'amber': 2, 'red': 3}
ALERTING = ('amber', 'red')
rows = []
for v in P['venues']:
    a = [assess(v[k], lab, v['name']) for k, lab in SERIES]
    m = mix_alert(v)
    worst = max([x['status'] for x in a] + [m['status']], key=lambda s: RANK[s])
    rows.append({'v': v, 'a': {x['series']: x for x in a}, 'mix': m, 'status': worst})

i0 = N - 1
TOT = {k: [sum(v[k][i] for v in P['venues']) for i in range(N)]
       for k in ('covers', 'web', 'walk', 'gr', 'ot', 'recep', 'other', 'bookings')}
TCOV, TWEB, TBK = TOT['covers'][i0], TOT['web'][i0], TOT['bookings'][i0]
TWALK = TOT['walk'][i0]
BCOV, BWEB, BBK = (baseline(TOT[k], i0) for k in ('covers', 'web', 'bookings'))
BWALK = baseline(TOT['walk'], i0)


# ---------------------------------------------------------------- html helpers
def pct(c, b):
    return None if not b else (c - b) / b * 100.0


def chip(p):
    if p is None:
        return '<span class="d na">n/a</span>'
    cls = 'flat' if abs(p) < 5 else ('up' if p > 0 else 'down')
    return f'<span class="d {cls}">{"+" if p >= 0 else ""}{p:.0f}%</span>'


LABEL = {'green': 'GREEN', 'blue': 'WATCH', 'amber': 'AMBER', 'red': 'RED'}


def alertchip(s, txt=None):
    return f'<span class="chip c-{s}">{txt or LABEL[s]}</span>'


def fmt(x):
    return f'{x:,.0f}' if x is not None else '–'


def dlabel(iso):
    return dt.date.fromisoformat(iso).strftime('%a %d %b')


def spark(vals, title):
    """7-day line against a shaded plus/minus 20 percent band. Hand-rolled SVG, no CDN."""
    idx = list(range(N - 7, N))
    vs = [vals[i] for i in idx]
    bs = [baseline(vals, i) or 0 for i in idx]
    lo_b = [b * (1 - BAND) for b in bs]
    hi_b = [b * (1 + BAND) for b in bs]
    hi = max(vs + hi_b + [1]) * 1.12
    W, H, PL, PR, PT, PB = 276.0, 84.0, 6.0, 30.0, 8.0, 15.0

    def X(k): return PL + k * (W - PL - PR) / 6.0
    def Y(val): return PT + (1 - val / hi) * (H - PT - PB)

    band = (' '.join(f'{X(k):.1f},{Y(b):.1f}' for k, b in enumerate(hi_b)) + ' ' +
            ' '.join(f'{X(k):.1f},{Y(b):.1f}' for k, b in reversed(list(enumerate(lo_b)))))
    mid = ' '.join(f'{X(k):.1f},{Y(b):.1f}' for k, b in enumerate(bs))
    line = ' '.join(f'{X(k):.1f},{Y(v):.1f}' for k, v in enumerate(vs))

    marks = ''
    for k, v in enumerate(vs):
        bad = below(v, bs[k] or None)
        last = (k == 6)
        r = 3.4 if last else 2.4
        fillc = ALERT if bad else INK
        marks += (f'<g><title>{dlabel(D[idx[k]])} · {title} {v:,} · baseline {bs[k]:,.0f}'
                  f' · band {lo_b[k]:,.0f} to {hi_b[k]:,.0f}'
                  f'{" · BELOW BAND" if bad else ""}</title>'
                  f'<circle cx="{X(k):.1f}" cy="{Y(v):.1f}" r="{r + 1.6:.1f}" fill="{SURF}"/>'
                  f'<circle cx="{X(k):.1f}" cy="{Y(v):.1f}" r="{r:.1f}" fill="{fillc}"/>'
                  f'<rect x="{X(k) - 16:.1f}" y="0" width="32" height="{H - PB:.0f}" fill="transparent"/>'
                  f'</g>')
    endc = ALERT if below(vs[6], bs[6] or None) else '#334155'
    ey = min(Y(vs[6]) + 3.4, H - PB - 2)
    endlab = (f'<text x="{X(6) + 6:.1f}" y="{ey:.1f}" font-size="10.5" font-weight="600" '
              f'fill="{endc}" font-family="JetBrains Mono,monospace">{vs[6]:,}</text>')
    labs = ''.join(
        f'<text x="{X(k):.1f}" y="{H - 4:.0f}" text-anchor="middle" font-size="8" fill="#a8b3c2" '
        f'font-family="JetBrains Mono,monospace">{D[i][8:10]}</text>' for k, i in enumerate(idx))
    return (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" height="{H:.0f}" role="img" '
            f'aria-label="{title}, seven days to {RD}">'
            f'<polygon points="{band}" fill="{BANDFILL}"/>'
            f'<polyline points="{mid}" fill="none" stroke="{GRID}" stroke-width="1"/>'
            f'<polyline points="{line}" fill="none" stroke="{INK}" stroke-width="1.8" '
            f'stroke-linejoin="round"/>{marks}{endlab}{labs}</svg>')


# ---------------------------------------------------------------- run matrix
MCOLS = [('Covers', 'covers'), ('Website', 'web'), ('GA4 bookings', 'bookings')]
mhead = ''.join(f'<th>{lab}</th>' for lab, _ in MCOLS) + '<th>Website mix</th>'
mrows = ''
for r in rows:
    cells = ''
    for lab, _ in MCOLS:
        a = r['a'][lab]
        v = pct(a['value'], a['base'])
        cells += (f'<td class="m m-{a["status"]}"><div class="mr">{a["run"]}</div>'
                  f'<div class="mv">{"+" if (v or 0) >= 0 else ""}{v:.0f}%</div></td>')
    m = r['mix']
    cells += (f'<td class="m m-{m["status"]}"><div class="mr">{m["run"]}</div>'
              f'<div class="mv">{m["share"]:.0f}% vs {m["base"]:.0f}%</div></td>')
    mrows += f'<tr><td class="vn">{r["v"]["name"]}</td>{cells}</tr>'

# ---------------------------------------------------------------- alert strip
PORT = []
for lab, cur, base in (('covers created', TCOV, BCOV), ('GA4 bookings', TBK, BBK)):
    if base and cur < base * (1 - BAND):
        PORT.append(f'<b>London portfolio {lab}</b> {cur:,} against a weekday baseline of '
                    f'{fmt(base)}, {pct(cur, base):.0f}%')

flagged = [r for r in rows if r['status'] in ALERTING]
flagged.sort(key=lambda r: -RANK[r['status']])
if flagged or PORT:
    items = ''.join(f'<li>{alertchip("amber", "PORTFOLIO")} {x}</li>' for x in PORT)
    for r in flagged:
        bits = []
        for _, lab in SERIES:
            a = r['a'][lab]
            if a['status'] not in ALERTING:
                continue
            why = 'single day under half baseline' if a['cliff'] and a['run'] < 3 \
                else f'{a["run"]} days below band'
            bits.append(f'<b>{lab.lower()}</b> {why} ({fmt(a["value"])} against a '
                        f'{fmt(a["base"])} baseline)')
        if r['mix']['status'] in ALERTING:
            bits.append(f'<b>channel shift</b> website share {r["mix"]["share"]:.0f}% against a '
                        f'{r["mix"]["base"]:.0f}% baseline, {r["mix"]["run"]} days')
        items += (f'<li>{alertchip(r["status"])} '
                  f'<b>{r["v"]["name"]}</b> — ' + '; '.join(bits) + '</li>')
    STRIP = f'<div class="alerts"><ul>{items}</ul></div>'
else:
    STRIP = '<div class="clean">No venue outside its band.</div>'

WATCH = []
for r in rows:
    for _, lab in SERIES:
        if r['a'][lab]['status'] == 'blue':
            WATCH.append(f'{r["v"]["name"]} {lab.lower()}')
WATCHTXT = (f'<div class="watch">One day into a run, so a repeat today turns these amber: '
            f'<b>{", ".join(WATCH)}</b>.</div>') if WATCH else ''

# ---------------------------------------------------------------- venue table
trows = ''
for r in rows:
    v = r['v']; i = i0
    cov, web, walk = v['covers'][i], v['web'][i], v['walk'][i]
    gr, ot, oth = v['gr'][i], v['ot'][i], v['recep'][i] + v['other'][i]
    bk, us = v['bookings'][i], v['users'][i]
    cvr = f'{bk / us * 100.0:.1f}%' if us else '–'
    trows += (
        f'<tr><td class="vn">{v["name"]}</td>'
        f'<td class="num"><b>{cov:,}</b><div class="chips">{chip(pct(cov, r["a"]["Covers"]["base"]))}</div></td>'
        f'<td class="num">{web:,}<div class="chips">{chip(pct(web, r["a"]["Website"]["base"]))}</div></td>'
        f'<td class="num">{walk:,}<div class="chips">{chip(pct(walk, baseline(v["walk"], i)))}</div></td>'
        f'<td class="num">{gr:,}</td><td class="num">{ot:,}</td><td class="num">{oth:,}</td>'
        f'<td class="num">{web / cov * 100:.0f}%</td>'
        f'<td class="num">{bk:,}<div class="chips">{chip(pct(bk, r["a"]["GA4 bookings"]["base"]))}</div></td>'
        f'<td class="num mut">{cvr}</td>'
        f'<td>{alertchip(r["status"])}</td></tr>')

TOTH = TOT['recep'][i0] + TOT['other'][i0]
trows += (f'<tr class="total"><td class="vn">London portfolio</td>'
          f'<td class="num">{TCOV:,}<div class="chips">{chip(pct(TCOV, BCOV))}</div></td>'
          f'<td class="num">{TWEB:,}<div class="chips">{chip(pct(TWEB, BWEB))}</div></td>'
          f'<td class="num">{TWALK:,}<div class="chips">{chip(pct(TWALK, BWALK))}</div></td>'
          f'<td class="num">{TOT["gr"][i0]:,}</td><td class="num">{TOT["ot"][i0]:,}</td>'
          f'<td class="num">{TOTH:,}</td>'
          f'<td class="num">{TWEB / TCOV * 100:.0f}%</td>'
          f'<td class="num">{TBK:,}<div class="chips">{chip(pct(TBK, BBK))}</div></td>'
          f'<td class="num mut">–</td><td></td></tr>')

# ---------------------------------------------------------------- 7-day panels
panels = ''
for r in rows:
    v = r['v']
    cards = ''
    for key, lab in SERIES:
        a = r['a'][lab]
        tag = f'<span class="runtag">{a["run"]}d below</span>' if a['run'] else ''
        cards += f'<div><div class="pl">{lab} {tag}</div>{spark(v[key], lab)}</div>'
    panels += (f'<div class="panel"><div class="pt">{v["name"]} '
               f'{alertchip(r["status"])}</div>'
               f'<div class="pg">{cards}</div></div>')

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
.alerts{{background:#fffbeb;border:1px solid #fde68a;border-left:3px solid #f59e0b;border-radius:10px;padding:14px 16px 14px 18px;margin:18px 0 10px;font-size:13.5px;color:#1e293b}}
.alerts ul{{margin:0;padding-left:16px}} .alerts li{{margin:5px 0;line-height:1.5}}
.clean{{background:#f0fdf4;border:1px solid #bbf7d0;border-left:3px solid #16a34a;border-radius:10px;padding:13px 16px;margin:18px 0 10px;font-size:13.5px;font-weight:600;color:#14532d}}
.watch{{font-size:12.5px;color:#475569;background:#f8fafc;border:1px solid #e2e8f0;border-radius:9px;padding:10px 14px;margin-bottom:18px}}
.chip{{display:inline-block;font-size:9.5px;font-weight:700;letter-spacing:.4px;padding:2px 6px;border-radius:5px;font-family:'JetBrains Mono',monospace}}
.c-green{{color:#16a34a;background:#ecfdf3}}.c-amber{{color:#b45309;background:#fffbeb}}.c-red{{color:#dc2626;background:#fef2f2}}.c-blue{{color:#2563eb;background:#eff6ff}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}}
.kpi{{border:1px solid #e2e8f0;border-radius:12px;padding:14px 15px;background:#fafafa}}
.kpi .lab{{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#64748b;font-weight:600}}
.kpi .big{{font-size:24px;font-weight:700;margin-top:5px;font-family:'DM Sans',sans-serif}}
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
.sec{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;margin:30px 0 8px;border-bottom:1px solid #eef2f6;padding-bottom:6px}}
table.matrix{{table-layout:fixed}}
table.matrix th{{text-align:center}} table.matrix th:first-child{{text-align:left}}
table.matrix td.vn,table.matrix th:first-child{{width:16%}}
table.matrix td.m{{text-align:center;border-radius:8px;border-bottom:3px solid #fff;padding:7px 6px}}
table.matrix .mr{{font-size:17px;font-weight:700;font-family:'JetBrains Mono',monospace;line-height:1.1}}
table.matrix .mv{{font-size:10px;font-family:'JetBrains Mono',monospace;opacity:.72;margin-top:1px}}
.m-green{{background:#f0fdf4;color:#15803d}}.m-blue{{background:#eff6ff;color:#1d4ed8}}
.m-amber{{background:#fffbeb;color:#b45309}}.m-red{{background:#fef2f2;color:#b91c1c}}
.panels{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}}
.panel{{border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px}}
.pt{{font-size:13px;font-weight:700;margin-bottom:8px}}
.pg{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
.pl{{font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:#94a3b8;font-weight:700;margin-bottom:2px;min-height:26px;line-height:1.3}}
.runtag{{color:#dc2626;letter-spacing:0;text-transform:none;font-weight:700}}
.legend{{display:flex;gap:16px;font-size:11.5px;color:#64748b;margin:10px 0 14px;flex-wrap:wrap;align-items:center}}
.legend i{{display:inline-block;vertical-align:-1px;margin-right:6px}}
.lg-band{{width:14px;height:10px;background:#eef2f7;border-radius:2px}}
.lg-base{{width:14px;height:2px;background:#94a3b8}}
.lg-line{{width:14px;height:2px;background:#2563eb}}
.lg-dot{{width:8px;height:8px;border-radius:50%;background:#dc2626}}
footer{{margin-top:32px;color:#94a3b8;font-size:11px;border-top:1px solid #eef2f6;padding-top:12px;line-height:1.6}}
footer ul{{margin:6px 0 0 16px}}
@media(max-width:1150px){{.cards{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:1000px){{.panels{{grid-template-columns:1fr}}}}
</style></head><body>
<a class="back" href="../index.html">← All London reports</a>
<h1>Aqua London — Daily Covers &amp; Bookings</h1>
<div class="sub">{RD} · covers by booking-created date · Europe/London</div>

{STRIP}
{WATCHTXT}

<div class="cards">
<div class="kpi"><div class="lab">Covers created</div><div class="big">{TCOV:,}</div>
<div class="meta">baseline {fmt(BCOV)} · {chip(pct(TCOV, BCOV))}</div></div>
<div class="kpi"><div class="lab">Website covers</div><div class="big">{TWEB:,}</div>
<div class="meta">baseline {fmt(BWEB)} · {chip(pct(TWEB, BWEB))} · {TWEB / TCOV * 100:.0f}% of covers</div></div>
<div class="kpi"><div class="lab">Walk-ins</div><div class="big">{TWALK:,}</div>
<div class="meta">baseline {fmt(BWALK)} · {chip(pct(TWALK, BWALK))} · {TWALK / TCOV * 100:.0f}% of covers</div></div>
<div class="kpi"><div class="lab">GA4 bookings</div><div class="big">{TBK:,}</div>
<div class="meta">baseline {fmt(BBK)} · {chip(pct(TBK, BBK))}</div></div>
</div>

<div class="sec">How close each venue is to an alert</div>
<div class="sub" style="font-size:12px;margin:0 0 8px">Consecutive days below the band, counting back from {RD}. Three or more is red, two is amber, one is a watch, and the small figure is today against its weekday baseline.</div>
<table class="matrix"><thead><tr><th>Venue</th>{mhead}</tr></thead><tbody>{mrows}</tbody></table>

<div class="sec">By venue — {RD}</div>
<table><thead><tr><th>Venue</th><th>Covers</th><th>Website</th><th>Walk-in</th>
<th>Google Reserve</th><th>OpenTable</th><th>Other</th><th>Web share</th>
<th>GA4 bookings</th><th>Conv rate</th><th>Alert</th></tr></thead><tbody>{trows}</tbody></table>
<div class="sub" style="margin-top:8px;font-size:11.5px">Variance chips compare the day with the median of the same weekday over the four preceding weeks. Other = reception plus third party. Walk-ins are shown but never alerted on: they are footfall, not a channel we run.</div>

<div class="sec">Seven days to {RD}</div>
<div class="legend">
<span><i class="lg-line"></i>actual</span>
<span><i class="lg-base"></i>weekday baseline</span>
<span><i class="lg-band"></i>band, baseline ±20%</span>
<span><i class="lg-dot"></i>day below the band</span>
<span style="color:#94a3b8">hover any point for the numbers</span>
</div>
<div class="panels">{panels}</div>

<footer>
<b>Method.</b> Covers = SUM(covers) from SevenRooms via Supabase, bucketed by booking-created date in Europe/London, excluding deleted and cancelled bookings and bar seating areas. Staff-name booking sources are excluded from covers entirely. Website = Booking Widget plus all landing pages, Nav and Hero CTAs, the menu page, PPC and campaign tags. GA4 bookings = event sevenrooms_booking_complete. Regent St combines Aqua Kyoto and Aqua Nueva.
<ul>
<li>Baseline for each day is the median of that same weekday across the four preceding weeks. Band is baseline plus or minus 20 percent. Red is three or more consecutive days below the band, or a single day under half baseline. Amber is two consecutive days. The run resets the moment a day lands back inside the band.</li>
<li>Alerts run on Website covers, not on the raw Booking Widget source. Aqua Shard re-tagged widget traffic into named landing pages on 21 Aug 2026, so the raw widget series has a definition break there. The widget series is carried in the payload but not shown: it measures how a booking was tagged rather than anything actionable.</li>
<li>Google conversions and GA4 channel data are deliberately absent: both settle over two to three days and cannot be read on a daily cadence.</li>
<li>Covers re-settle downward as cancellations accrue, so the full 35-day window is re-pulled every morning rather than carried forward.</li>
<li>Suppressed dates (closures and known buyouts): {SUPPTXT}.</li>
{NOTES}
</ul>
Generated {P['generated']}.
</footer></body></html>'''

open(OUT, 'w').write(HTML)

print(json.dumps({
    'reporting_day': RD,
    'portfolio': {'covers': TCOV, 'covers_baseline': BCOV, 'website': TWEB,
                  'website_baseline': BWEB, 'walkins': TWALK, 'walkins_baseline': BWALK,
                  'bookings': TBK, 'bookings_baseline': BBK,
                  'web_share': round(TWEB / TCOV * 100, 1),
                  'walk_share': round(TWALK / TCOV * 100, 1)},
    'portfolio_alert': [x.replace('<b>', '').replace('</b>', '') for x in PORT],
    'alerts': [{'venue': r['v']['name'], 'status': r['status'],
                'series': {k: {kk: vv for kk, vv in a.items() if kk != 'series'}
                           for k, a in r['a'].items() if a['status'] in ALERTING},
                'mix': r['mix'] if r['mix']['status'] in ALERTING else None}
               for r in flagged],
    'watch_one_day_in': WATCH,
    'out': OUT,
}, indent=1, default=float))
