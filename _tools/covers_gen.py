#!/usr/bin/env python3
# Covers & Booking Channels report generator.  Usage: covers_gen.py <payload.json> <out.html>
# Data source: SevenRooms via Supabase project vklgpzrhjvjqhlpfennn, public.reservations.
# Covers = SUM(covers) by booking-created date (sr_created_at, market tz), net of
# cancellations/deleted, Bar seating areas excluded.
#
# Payload venues: [{name, ga4, ch:{web|gr|ot|walk|recep|ota|tp: {c,p,y}}}]
#   web   (Website) = Booking Widget + '%Landing Page%' + Nav/Hero CTA + Menu Page + PPC + campaign tags
#   gr    = Google Reserve Integration
#   ot    = market platform (London/USA OpenTable[+Resy], HK OpenRice)
#   walk  = Walk In
#   recep = reception / reservations desks
#   ota   = TheFork + First Table
#   tp    = other third-party (BuyAGift, Virgin, Amex, DoorDash, gifting, concierge)
# Every channel cell shows value + WoW + YoY.
# EXCLUDED entirely (Ben, 13 Jul 2026): named-host / staff-entered bookings (large groups and private
# dining keyed in by the events and reservations teams). Not a marketing channel, so dropped from the
# covers total rather than parked in an "Other" bucket.
import json, sys

P = json.load(open(sys.argv[1])); OUT = sys.argv[2]
V = P['venues']
MKT = P.get('market', 'London'); PLAT = P.get('platform', 'OpenTable'); TZ = P.get('tz', 'Europe/London')
CH = ['web', 'gr', 'ot', 'walk', 'recep', 'ota', 'tp']
HEAD = {'web': 'Website', 'gr': 'Google Reserve', 'ot': PLAT, 'walk': 'Walk-in',
        'recep': 'Reception', 'ota': 'TheFork / First Table', 'tp': 'Other 3rd party'}
CLS = {'web': 's-w', 'gr': 's-g', 'ot': 's-o', 'walk': 's-k', 'recep': 's-r', 'ota': 's-x', 'tp': 's-x'}


def pct(cur, base):
    if not base:
        return None
    return (cur - base) / base * 100.0


def chip(p, lab):
    if p is None:
        return f'<span class="d na">{lab} n/a</span>'
    cls = 'flat' if abs(p) < 1.5 else ('up' if p > 0 else 'down')
    return f'<span class="d {cls}">{lab} {"+" if p >= 0 else ""}{p:.0f}%</span>'


def cell(t):
    """t = {c,p,y} -> value with WoW and YoY chips."""
    return (f'<td class="ch"><div class="v num">{t["c"]:,}</div>'
            f'<div class="chips">{chip(pct(t["c"], t["p"]), "W")}{chip(pct(t["c"], t["y"]), "Y")}</div></td>')


def totals(vs):
    out = {}
    for k in CH:
        out[k] = {f: sum(v['ch'][k][f] for v in vs) for f in ('c', 'p', 'y')}
    return out


def covtot(t):
    return {f: sum(t[k][f] for k in CH) for f in ('c', 'p', 'y')}


TOT = totals(V); TCOV = covtot(TOT)


def mixbar(chs, tot_c):
    c = tot_c or 1
    return '<div class="bar">' + ''.join(
        f'<i class="{CLS[k]}" style="width:{chs[k]["c"] / c * 100:.1f}%"></i>' for k in CH) + '</div>'


rows = ''
for v in V:
    cov = covtot(v['ch'])
    rows += (f'<tr><td class="vn">{v["name"]}</td>'
             f'<td class="ch"><div class="v num"><b>{cov["c"]:,}</b></div>'
             f'<div class="chips">{chip(pct(cov["c"], cov["p"]), "W")}{chip(pct(cov["c"], cov["y"]), "Y")}</div></td>'
             + ''.join(cell(v['ch'][k]) for k in CH)
             + f'<td class="num mut">{v["ga4"]:,}</td>'
             f'<td style="min-width:110px">{mixbar(v["ch"], cov["c"])}</td></tr>')
rows += (f'<tr class="total"><td class="vn">{MKT} portfolio</td>'
         f'<td class="ch"><div class="v num">{TCOV["c"]:,}</div>'
         f'<div class="chips">{chip(pct(TCOV["c"], TCOV["p"]), "W")}{chip(pct(TCOV["c"], TCOV["y"]), "Y")}</div></td>'
         + ''.join(cell(TOT[k]) for k in CH)
         + f'<td class="num mut">{sum(v["ga4"] for v in V):,}</td>'
         f'<td style="min-width:110px">{mixbar(TOT, TCOV["c"])}</td></tr>')

# ---- 8-week SVG (bars = total covers, line = platform covers) ----
T = P['trend']; labels = T['labels']; tt = T['total']; oo = T['ot']
n = len(tt); maxT = max(tt); maxO = max(oo); base = 144.0
bw = 60.6; x0 = 26.2; step = 101.0
bars = ''; cx = []
for i, t in enumerate(tt):
    h = t / maxT * 132.0; x = x0 + i * step
    bars += f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="#c7dbf2" rx="2"/>'
    cx.append(x + bw / 2)
pts = ''; circ = ''
for i, o in enumerate(oo):
    y = base - (o / maxO * 125.0); pts += f'{cx[i]:.1f},{y:.1f} '
    circ += f'<circle cx="{cx[i]:.1f}" cy="{y:.1f}" r="3" fill="#da3743"/>'
labs = ''.join(f'<text x="{cx[i]:.1f}" y="162" font-size="10" fill="#94a3b8" text-anchor="middle" '
               f'font-family="JetBrains Mono,monospace">{labels[i]}</text>' for i in range(n))
svg = (f'<svg viewBox="0 0 820 170" style="width:100%;height:170px;display:block">{bars}'
       f'<polyline fill="none" stroke="#da3743" stroke-width="2.4" points="{pts}"/>{circ}{labs}</svg>')


def kpi(lab, big, meta):
    return f'<div class="kpi"><div class="lab">{lab}</div><div class="big">{big}</div><div class="meta">{meta}</div></div>'


def kmeta(t):
    return f'WoW {chip(pct(t["c"], t["p"]), "")} · YoY {chip(pct(t["c"], t["y"]), "")}'


cov_yoy = pct(TCOV['c'], TCOV['y'])
cards = (kpi('Covers created', f"{TCOV['c']:,}", kmeta(TCOV)) +
         kpi('Website covers', f"{TOT['web']['c']:,}", kmeta(TOT['web'])) +
         kpi(f'{PLAT} covers', f"{TOT['ot']['c']:,}", kmeta(TOT['ot']) + ' · <b>not in GA4</b>') +
         kpi('Walk-in covers', f"{TOT['walk']['c']:,}", kmeta(TOT['walk']) + ' · <b>not in GA4</b>') +
         kpi('GA4 bookings (website)', f"{sum(v['ga4'] for v in V):,}", P['ga4_meta']))

ot_mult = TOT['ot']['c'] / (TOT['ot']['y'] or 1)
default_callout = (
    f'<b>Why this sits alongside the GA4 dashboard.</b> GA4 is becoming steadily less reliable as cookie consent '
    f'and privacy tracking cut what it can see, so treat it as a guide to overall website performance rather than a '
    f'count of bookings. <b>GA4 <code>sevenrooms_booking_complete</code></b> only fires for bookings made on our own '
    f'website. It cannot see <b>{PLAT}</b>, only partly captures <b>Google Reserve</b>, and never sees walk-ins or the '
    f'reception desks. {PLAT} covers are <b>{TOT["ot"]["c"]:,}</b> this week, from <b>{TOT["ot"]["y"]:,}</b> the same '
    f'week last year, roughly {ot_mult:.1f}x. So while GA4 reads <b>{P["ga4_yoy"]}</b>, total covers created are '
    f'<b>{"+" if cov_yoy >= 0 else ""}{cov_yoy:.0f}% YoY</b>. This report is the more accurate view of what we are '
    f'actually creating.')
CALLOUT = P.get('callout', default_callout)
PLATFOOT = P.get('platform_foot', '<b>OpenTable</b> = OT Guestcenter + OpenTable sources')
COMBNOTE = P.get('combined_note', '<b>Regent St</b> = Aqua Kyoto + Aqua Nueva combined. ')
ths = ''.join(f'<th>{HEAD[k]}</th>' for k in CH)
legend = ''.join(f'<span><i class="{CLS[k]}"></i>{HEAD[k]}</span>' for k in CH)

HTML = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua {MKT} — Covers &amp; Booking Channels — {P['week']}</title>
<style>@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',system-ui,sans-serif;background:#fff;color:#0f172a;line-height:1.5;padding:28px;max-width:1340px;margin:0 auto}}
a.back{{font-size:12px;color:#2563eb;text-decoration:none}}
h1{{font-size:24px;font-weight:700;margin-top:8px;letter-spacing:-.3px}}
.sub{{color:#64748b;font-size:13px;margin-top:4px}}
.num{{font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums}}
.callout{{background:#eff6ff;border:1px solid #dbeafe;border-left:3px solid #2563eb;border-radius:10px;padding:14px 16px;margin:18px 0;font-size:13.5px;line-height:1.55;color:#1e293b}}
.callout b{{color:#0f172a}}
.cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:18px 0}}
.kpi{{border:1px solid #e2e8f0;border-radius:12px;padding:14px 15px;background:#fafafa}}
.kpi .lab{{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#64748b;font-weight:600}}
.kpi .big{{font-size:24px;font-weight:700;margin-top:5px;font-family:'JetBrains Mono',monospace}}
.kpi .meta{{font-size:11.5px;color:#475569;margin-top:6px}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}}
th,td{{padding:8px 6px;text-align:right;border-bottom:1px solid #eef2f6;white-space:nowrap;vertical-align:top}}
th:first-child,td:first-child{{text-align:left}}
thead th{{font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:#64748b;border-bottom:2px solid #e2e8f0;vertical-align:bottom}}
td.vn{{font-weight:600;vertical-align:middle}}
td.ch .v{{font-size:13px;line-height:1.25}}
td.ch .chips{{display:flex;gap:3px;justify-content:flex-end;margin-top:3px}}
tr.total{{font-weight:700;background:#f1f5f9}} tr.total td{{border-top:2px solid #cbd5e1}}
.mut{{color:#94a3b8;vertical-align:middle}}
.d{{font-size:9.5px;font-weight:600;padding:1px 4px;border-radius:5px;font-family:'JetBrains Mono',monospace}}
.up{{color:#16a34a;background:#ecfdf3}}.down{{color:#dc2626;background:#fef2f2}}.flat{{color:#475467;background:#f2f4f7}}.na{{color:#98a2b3;background:#f8fafc}}
.bar{{display:flex;height:13px;border-radius:4px;overflow:hidden;background:#eef2f6;margin-top:2px}}
.bar i{{display:block;height:100%}}
.s-w{{background:#2563eb}}.s-g{{background:#16a34a}}.s-o{{background:#da3743}}.s-k{{background:#f59e0b}}.s-r{{background:#8b5cf6}}.s-x{{background:#cbd2d9}}
.legend{{display:flex;gap:14px;font-size:12px;color:#475569;margin:14px 0 2px;flex-wrap:wrap}}
.legend i{{display:inline-block;width:11px;height:11px;border-radius:2px;vertical-align:-1px;margin-right:5px}}
.key{{font-size:11.5px;color:#94a3b8;margin-top:8px}}
.sec{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;margin:28px 0 8px;border-bottom:1px solid #eef2f6;padding-bottom:6px}}
footer{{margin-top:30px;color:#94a3b8;font-size:11px;border-top:1px solid #eef2f6;padding-top:12px;line-height:1.55}}
@media(max-width:1150px){{.cards{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body>
<a class="back" href="../index.html">← All {MKT} reports</a>
<h1>Aqua {MKT} — Covers &amp; Booking Channels</h1>
<div class="sub">{P['week']} (Mon–Sun) · SevenRooms covers by booking-created date · WoW vs {P['wow']} · YoY vs {P['yoy']}</div>

<div class="callout">{CALLOUT}</div>

<div class="cards">{cards}</div>

<div class="sec">Covers by venue &amp; booking channel</div>
<table><thead><tr><th>Venue</th><th>Covers</th>{ths}<th>GA4 bk</th><th>Channel mix</th></tr></thead>
<tbody>{rows}</tbody></table>
<div class="key">Each cell shows covers this week, with <b>W</b> = week on week and <b>Y</b> = year on year beneath.</div>
<div class="legend">{legend}</div>

<div class="sec">{PLAT} covers vs total covers — last 8 weeks</div>
<div class="legend"><span><i class="s-x" style="background:#c7dbf2"></i>Total covers (bars)</span><span><i class="s-o"></i>{PLAT} covers (line)</span></div>
{svg}

<footer>
<b>Covers</b> = SevenRooms covers by booking-created date (<code>sr_created_at</code>, {TZ}), net of cancellations and deleted bookings. Bar seating areas excluded; private dining and afternoon tea included.
<b>Website</b> = all bookings originating on our own site: booking widget, campaign landing pages, on-site CTAs (Nav/Hero), menu page and paid-search landing pages. {PLATFOOT}; <b>Google Reserve</b> = Google Reserve Integration; <b>Walk-in</b> = Walk In; <b>Reception</b> = venue reception and reservations desks; <b>TheFork / First Table</b> and <b>Other 3rd party</b> = booking platforms, gifting and concierge partners.
<b>Named-host bookings are excluded from this report:</b> large groups and private dining keyed in by the events and reservations teams are not a marketing channel, so they are removed from the covers total rather than parked in an "Other" bucket. Covers totals here are therefore lower than in reports before 13 Jul 2026 and are not comparable with them. {COMBNOTE}<b>GA4 bk</b> = website <code>sevenrooms_booking_complete</code> events (shown for context, not directly comparable to covers). Generated {P['generated']}. Source: SevenRooms via Supabase.
</footer>
</body></html>'''
open(OUT, 'w').write(HTML)
print("wrote", OUT, len(HTML), "bytes")
