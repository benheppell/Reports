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
SHORT = {'Covers': 'covers', 'Website': 'website', 'GA4 bookings': 'GA4 bookings'}
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


SCALE = 50.0  # chart y-range, plus/minus percent against baseline


def spark(vals, title):
    """7 days plotted as variance against the weekday baseline, so the plus/minus 20 percent
    band is a constant ribbon and every chart on the page reads on the same scale.
    Raw values live on the end label and in the hover tooltip. Hand-rolled SVG, no CDN."""
    idx = list(range(N - 7, N))
    vs = [vals[i] for i in idx]
    bs = [baseline(vals, i) or 0 for i in idx]
    dev = [((v - b) / b * 100.0 if b else 0.0) for v, b in zip(vs, bs)]
    W, H, PL, PR, PT, PB = 204.0, 92.0, 4.0, 34.0, 9.0, 14.0
    MIDY = PT + (H - PT - PB) / 2.0
    HALF = (H - PT - PB) / 2.0

    def X(k): return PL + k * (W - PL - PR) / 6.0
    def Y(d): return MIDY - max(-SCALE, min(SCALE, d)) / SCALE * HALF

    bandtop, bandbot = Y(BAND * 100), Y(-BAND * 100)
    grid = (f'<rect x="{PL - 3:.1f}" y="{bandtop:.1f}" width="{W - PL - PR + 6:.1f}" '
            f'height="{bandbot - bandtop:.1f}" fill="{BANDFILL}" rx="3"/>'
            f'<line x1="{PL - 3:.1f}" y1="{MIDY:.1f}" x2="{W - PR + 3:.1f}" y2="{MIDY:.1f}" '
            f'stroke="{GRID}" stroke-width="1"/>')
    line = ' '.join(f'{X(k):.1f},{Y(d):.1f}' for k, d in enumerate(dev))

    marks = ''
    for k, d in enumerate(dev):
        bad = below(vs[k], bs[k] or None)
        last = (k == 6)
        off = abs(d) > SCALE
        r = 3.4 if last else 2.5
        fillc = ALERT if bad else INK
        marks += (f'<g><title>{dlabel(D[idx[k]])} · {title} {vs[k]:,} · baseline {bs[k]:,.0f}'
                  f' · {d:+.0f}% · band {bs[k] * 0.8:,.0f} to {bs[k] * 1.2:,.0f}'
                  f'{" · BELOW BAND" if bad else ""}{" · off scale" if off else ""}</title>'
                  f'<circle cx="{X(k):.1f}" cy="{Y(d):.1f}" r="{r + 1.7:.1f}" fill="{SURF}"/>'
                  f'<circle cx="{X(k):.1f}" cy="{Y(d):.1f}" r="{r:.1f}" '
                  + (f'fill="{SURF}" stroke="{fillc}" stroke-width="1.8"/>' if off
                     else f'fill="{fillc}"/>')
                  + f'<rect x="{X(k) - 17:.1f}" y="0" width="34" height="{H - PB:.0f}" fill="transparent"/>'
                  f'</g>')

    endc = ALERT if below(vs[6], bs[6] or None) else '#334155'
    endlab = (f'<text x="{X(6) + 7:.1f}" y="{Y(dev[6]) - 1:.1f}" font-size="10" font-weight="700" '
              f'fill="{endc}" font-family="JetBrains Mono,monospace">{vs[6]:,}</text>'
              f'<text x="{X(6) + 7:.1f}" y="{Y(dev[6]) + 9:.1f}" font-size="8.5" '
              f'fill="#94a3b8" font-family="JetBrains Mono,monospace">{dev[6]:+.0f}%</text>')
    axis = ''
    labs = ''.join(
        f'<text x="{X(k):.1f}" y="{H - 4:.0f}" text-anchor="middle" font-size="7.5" fill="#a8b3c2" '
        f'font-family="JetBrains Mono,monospace">{D[i][8:10]}</text>' for k, i in enumerate(idx))
    return (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" role="img" '
            f'aria-label="{title}, seven days to {RD}, variance against weekday baseline">'
            f'{grid}{axis}'
            f'<polyline points="{line}" fill="none" stroke="{INK}" stroke-width="1.8" '
            f'stroke-linejoin="round" stroke-linecap="round"/>{marks}{endlab}{labs}</svg>')


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
            bits.append(f'<b>{SHORT[lab]}</b> {why} ({fmt(a["value"])} against a '
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
            WATCH.append(f'{r["v"]["name"]} {SHORT[lab]}')
WATCHTXT = (f'<div class="watch">One day into a run, so a repeat today turns these amber: '
            f'<b>{", ".join(WATCH)}</b>.</div>') if WATCH else ''

# ---------------------------------------------------------------- venue table
# One row per venue. Two numbers that matter (covers, GA4 bookings), two that explain
# them (website, walk-in), the rest of the mix as a bar rather than five more columns.
MIX = [('web', 'Website', '#2563eb'), ('walk', 'Walk-in', '#ea580c'),
       ('gr', 'Google Reserve', '#0d9488'), ('ot', 'OpenTable', '#8b5cf6'),
       ('rest', 'Reception / third party', '#cbd5e1')]


def vchip(cur, base):
    p = pct(cur, base)
    if p is None:
        return '<span class="v na">n/a</span>'
    cls = 'flat' if abs(p) < 5 else ('up' if p > 0 else 'down')
    return f'<span class="v {cls}">{"+" if p >= 0 else ""}{p:.0f}%</span>'


def numcell(cur, base, lead=False):
    return (f'<td class="n"><span class="big{" lead" if lead else ""}">{cur:,}</span>'
            f'{vchip(cur, base)}<div class="bl">vs {fmt(base)}</div></td>')


def mixbar(d, tot):
    if not tot:
        return ''
    segs = ''
    for k, lab, col in MIX:
        val = d[k]
        if not val:
            continue
        segs += (f'<i style="width:{val / tot * 100:.2f}%;background:{col}">'
                 f'<span>{lab} {val:,} · {val / tot * 100:.0f}%</span></i>')
    NAME = {'gr': 'Google Reserve', 'ot': 'OpenTable', 'rest': 'Other'}
    under = ' · '.join(f'{NAME[k]} {d[k]:,}'
                       for k, _, _ in MIX if k in NAME and d[k])
    return f'<div class="bar">{segs}</div><div class="bl mixnum">{under or "&nbsp;"}</div>'


trows = ''
for r in rows:
    v = r['v']; i = i0
    d = {'web': v['web'][i], 'walk': v['walk'][i], 'gr': v['gr'][i], 'ot': v['ot'][i],
         'rest': v['recep'][i] + v['other'][i]}
    cov, bk, us = v['covers'][i], v['bookings'][i], v['users'][i]
    runs = [SHORT[lab].replace(' bookings', '') for _, lab in SERIES if r['a'][lab]['run']]
    nrun = max([r['a'][lab]['run'] for _, lab in SERIES] + [0])
    why = (f'<div class="why">{", ".join(runs)} · {nrun} day{"s" if nrun != 1 else ""} below band</div>'
           if runs else '<div class="why">inside band</div>')
    trows += (
        f'<tr><td class="vn">{v["name"]}'
        f'<div class="bl">{f"{bk / us * 100:.1f}% conversion" if us else "&nbsp;"}</div></td>'
        + numcell(cov, r['a']['Covers']['base'], lead=True)
        + numcell(bk, r['a']['GA4 bookings']['base'])
        + numcell(d['web'], r['a']['Website']['base'])
        + numcell(d['walk'], baseline(v['walk'], i))
        + f'<td class="mixcell">{mixbar(d, cov)}</td>'
        + f'<td class="st">{alertchip(r["status"])}{why}</td></tr>')

dT = {'web': TWEB, 'walk': TWALK, 'gr': TOT['gr'][i0], 'ot': TOT['ot'][i0],
      'rest': TOT['recep'][i0] + TOT['other'][i0]}
trows += (f'<tr class="total"><td class="vn">London portfolio<div class="bl">six venues</div></td>'
          + numcell(TCOV, BCOV, lead=True) + numcell(TBK, BBK)
          + numcell(TWEB, BWEB) + numcell(TWALK, BWALK)
          + f'<td class="mixcell">{mixbar(dT, TCOV)}</td><td class="st"></td></tr>')

MIXLEG = ''.join(f'<span><i style="background:{c}"></i>{l}</span>' for _, l, c in MIX)

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
.sec{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;margin:30px 0 8px;border-bottom:1px solid #eef2f6;padding-bottom:6px}}
table{{width:100%;border-collapse:separate;border-spacing:0;font-size:13.5px;margin-top:4px}}
th,td{{padding:13px 12px;text-align:right;white-space:nowrap;vertical-align:middle;border-bottom:1px solid #eef2f6}}
th:first-child,td:first-child{{text-align:left;padding-left:14px}}
thead th{{font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;color:#7c8899;font-weight:700;border-bottom:1.5px solid #cbd5e1;padding-bottom:9px;white-space:normal;line-height:1.3}}
tbody tr:nth-child(even){{background:#fbfcfd}}
tbody tr:hover{{background:#f4f8ff}}
td.vn{{font-weight:700;font-size:14.5px;letter-spacing:-.15px}}
td.n .big{{font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums;font-size:16px;font-weight:600;letter-spacing:-.3px}}
td.n .big.lead{{font-size:19px;font-weight:700}}
.v{{font-size:11.5px;font-weight:700;font-family:'JetBrains Mono',monospace;margin-left:7px}}
.up{{color:#15803d}}.down{{color:#dc2626}}.flat{{color:#64748b}}.na{{color:#a8b3c2}}
.bl{{font-size:10.5px;color:#a8b3c2;font-weight:500;margin-top:3px;letter-spacing:.1px}}
tr.total{{background:#f1f5f9 !important;font-weight:700}} tr.total td{{border-top:2px solid #cbd5e1;border-bottom:none}}
td.mixcell{{min-width:190px;padding-right:14px}}
.bar{{display:flex;height:15px;border-radius:5px;overflow:hidden;background:#f1f5f9}}
.bar i{{display:block;height:100%;position:relative;border-right:2px solid #fff}}
.bar i:last-child{{border-right:none}}
.bar i span{{position:absolute;left:50%;bottom:20px;transform:translateX(-50%);background:#0f172a;color:#fff;font-size:11px;
  padding:4px 8px;border-radius:6px;white-space:nowrap;opacity:0;pointer-events:none;transition:opacity .12s;z-index:5;font-weight:500}}
.bar i:hover span{{opacity:1}}
td.st{{text-align:right}}
.why{{font-size:10.5px;color:#94a3b8;margin-top:4px;white-space:normal;max-width:150px;margin-left:auto;line-height:1.35}}
.mixnum{{text-align:left;margin-top:5px}}
.mixleg{{display:flex;gap:15px;font-size:11.5px;color:#64748b;margin:12px 0 2px;flex-wrap:wrap;align-items:center}}
.mixleg i{{display:inline-block;width:10px;height:10px;border-radius:2.5px;vertical-align:-1px;margin-right:6px}}
.panels{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}}
.panel{{border:1px solid #e2e8f0;border-radius:12px;padding:12px 14px}}
.pt{{font-size:13px;font-weight:700;margin-bottom:8px}}
.pg{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;align-items:end}}
.pg svg{{display:block;width:100%;height:auto}}
.pl{{font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:#94a3b8;font-weight:700;margin-bottom:2px;line-height:1.35}}
.runtag{{color:#dc2626;letter-spacing:0;text-transform:none;font-weight:700}}
.legend{{display:flex;gap:16px;font-size:11.5px;color:#64748b;margin:10px 0 14px;flex-wrap:wrap;align-items:center}}
.legend i{{display:inline-block;vertical-align:-1px;margin-right:6px}}
.lg-band{{width:14px;height:10px;background:#eef2f7;border-radius:2px}}
.lg-base{{width:14px;height:2px;background:#94a3b8}}
.lg-line{{width:14px;height:2px;background:#2563eb}}
.lg-dot{{width:8px;height:8px;border-radius:50%;background:#dc2626}}
.lg-off{{width:8px;height:8px;border-radius:50%;background:#fff;border:1.8px solid #2563eb}}
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

<div class="sec">Yesterday by venue — {RD}</div>
<div class="mixleg">{MIXLEG}<span style="color:#a8b3c2">hover a bar segment for its numbers</span></div>
<table><thead><tr>
<th>Venue</th><th>Covers created</th><th>GA4 bookings</th><th>Website covers</th>
<th>Walk-ins</th><th>Channel mix</th><th>Status</th></tr></thead>
<tbody>{trows}</tbody></table>
<div class="sub" style="margin-top:10px;font-size:12px">Every figure is compared with the median of the same weekday over the four preceding weeks, shown beneath it. Status counts consecutive days below the band ending on {RD}: three or more is red, two is amber, one is a watch. Walk-ins are shown but never alerted on, being footfall rather than a channel we run.</div>

<div class="sec">Seven days to {RD} — variance against the weekday baseline</div>
<div class="legend">
<span><i class="lg-line"></i>variance against the weekday baseline</span>
<span><i class="lg-base"></i>baseline, 0%</span>
<span><i class="lg-band"></i>band, ±20%</span>
<span><i class="lg-dot"></i>day below the band</span>
<span><i class="lg-off"></i>beyond ±50%, clamped to the edge</span>
<span style="color:#94a3b8">every chart is on the same ±50% scale · hover any point for the raw numbers</span>
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
