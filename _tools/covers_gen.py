#!/usr/bin/env python3
# Covers & Booking Channels report generator.  Usage: covers_gen.py <payload.json> <out.html>
# Data source: SevenRooms via Supabase project vklgpzrhjvjqhlpfennn, public.reservations.
# Covers = SUM(covers) by booking-created date (sr_created_at, market tz), net of
# cancellations/deleted, Bar seating areas excluded.
#
# Channels on booking_source:
#   widget (Website) = Booking Widget + '%Landing Page%' + Nav/Hero CTA + Menu Page + PPC + campaign tags
#   gr    = Google Reserve Integration
#   ot    = market platform (London/USA OpenTable[+Resy], HK OpenRice)
#   walk  = Walk In
#   recep = reception / reservations desks
#   ota   = TheFork + First Table
#   tp    = other third-party (BuyAGift, Virgin, Amex, DoorDash, gifting, concierge)
# EXCLUDED entirely (Ben, 13 Jul 2026): named-host / staff-entered bookings (large groups and
# private dining keyed in by the events and reservations teams). Not a marketing channel, so they
# are dropped from the covers total rather than parked in an "Other" bucket.
import json, sys

P = json.load(open(sys.argv[1])); OUT = sys.argv[2]


def pct(cur, base):
    if not base:
        return None
    return (cur - base) / base * 100.0


def dchip(p):
    if p is None:
        return '<span class="d na">n/a</span>'
    cls = 'flat' if abs(p) < 1.5 else ('up' if p > 0 else 'down')
    return f'<span class="d {cls}">{"+" if p >= 0 else ""}{p:.0f}%</span>'


def otd(p):
    if p is None:
        return ''
    cls = 'up' if p > 0 else ('down' if p < 0 else 'flat')
    return f'<span class="otd"><span class="d {cls}">{"+" if p >= 0 else ""}{p:.0f}%</span></span>'


V = P['venues']
KEYS = ['covers_cur', 'covers_prior', 'covers_yoy', 'widget', 'widget_prior', 'widget_yoy',
        'gr', 'gr_prior', 'gr_yoy', 'ot', 'ot_prior', 'ot_yoy', 'walk', 'recep', 'ota', 'tp', 'ga4']
tot = {k: sum(v.get(k, 0) for v in V) for k in KEYS}
MKT = P.get('market', 'London'); PLAT = P.get('platform', 'OpenTable'); TZ = P.get('tz', 'Europe/London')


def mixbar(v):
    c = v['covers_cur'] or 1
    seg = [('s-w', v['widget']), ('s-g', v['gr']), ('s-o', v['ot']),
           ('s-k', v['walk']), ('s-r', v['recep']), ('s-x', v['ota'] + v['tp'])]
    return '<div class="bar">' + ''.join(
        f'<i class="{cl}" style="width:{n / c * 100:.1f}%"></i>' for cl, n in seg) + '</div>'


rows = ''
for v in V + [{'name': f'{MKT} portfolio', 'total': True, **tot}]:
    isT = v.get('total')
    wow = pct(v['covers_cur'], v['covers_prior']); yoy = pct(v['covers_cur'], v['covers_yoy'])
    cov = f"{v['covers_cur']:,}"
    cls = ' class="total"' if isT else ''
    rows += (f'<tr{cls}><td>{v["name"]}</td>'
             f'<td class="num">{cov if isT else "<b>" + cov + "</b>"}</td>'
             f'<td class="num">{dchip(wow)}</td><td class="num">{dchip(yoy)}</td>'
             f'<td class="num">{v["widget"]:,}</td><td class="num">{v["gr"]:,}</td>'
             f'<td class="num">{v["ot"]:,} {otd(pct(v["ot"], v["ot_yoy"]))}</td>'
             f'<td class="num">{v["walk"]:,}</td><td class="num">{v["recep"]:,}</td>'
             f'<td class="num">{v["ota"]:,}</td><td class="num">{v["tp"]:,}</td>'
             f'<td class="num mut">{v["ga4"]:,}</td>'
             f'<td style="min-width:110px">{mixbar(v)}</td></tr>')

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


def pt(k):
    return sum(v.get(k, 0) for v in V)


cov_yoy = pct(tot['covers_cur'], tot['covers_yoy'])
cards = (kpi('Covers created', f"{tot['covers_cur']:,}",
             f"WoW {dchip(pct(tot['covers_cur'], tot['covers_prior']))} · YoY {dchip(cov_yoy)}") +
         kpi('Website covers', f"{tot['widget']:,}",
             f"WoW {dchip(pct(tot['widget'], pt('widget_prior')))} · YoY {dchip(pct(tot['widget'], pt('widget_yoy')))}") +
         kpi(f'{PLAT} covers', f"{tot['ot']:,}",
             f"WoW {dchip(pct(tot['ot'], pt('ot_prior')))} · YoY {dchip(pct(tot['ot'], pt('ot_yoy')))} · <b>not in GA4</b>") +
         kpi('Walk-in covers', f"{tot['walk']:,}", "Never visible to GA4") +
         kpi('GA4 bookings (website)', f"{tot['ga4']:,}", P['ga4_meta']))

ot_mult = tot['ot'] / (tot['ot_yoy'] or 1)
default_callout = (
    f'<b>Why this sits alongside the GA4 dashboard.</b> GA4 is becoming steadily less reliable as cookie consent '
    f'and privacy tracking cut what it can see, so treat it as a guide to overall website performance rather than a '
    f'count of bookings. <b>GA4 <code>sevenrooms_booking_complete</code></b> only fires for bookings made on our own '
    f'website. It cannot see <b>{PLAT}</b>, only partly captures <b>Google Reserve</b>, and never sees walk-ins or the '
    f'reception desks. {PLAT} covers are <b>{tot["ot"]:,}</b> this week, from <b>{tot["ot_yoy"]:,}</b> the same week '
    f'last year, roughly {ot_mult:.1f}x. So while GA4 reads <b>{P["ga4_yoy"]}</b>, total covers created are '
    f'<b>{dchip(cov_yoy)} YoY</b>. This report is the more accurate view of what we are actually creating.')
CALLOUT = P.get('callout', default_callout)
PLATFOOT = P.get('platform_foot', '<b>OpenTable</b> = OT Guestcenter + OpenTable sources')
COMBNOTE = P.get('combined_note', '<b>Regent St</b> = Aqua Kyoto + Aqua Nueva combined. ')

HTML = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua {MKT} — Covers &amp; Booking Channels — {P['week']}</title>
<style>@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',system-ui,sans-serif;background:#fff;color:#0f172a;line-height:1.5;padding:28px;max-width:1280px;margin:0 auto}}
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
.kpi .meta{{font-size:11.5px;color:#475569;margin-top:5px}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}}
th,td{{padding:9px 7px;text-align:right;border-bottom:1px solid #eef2f6;white-space:nowrap}}
th:first-child,td:first-child{{text-align:left}}
thead th{{font-size:10px;text-transform:uppercase;letter-spacing:.4px;color:#64748b;border-bottom:2px solid #e2e8f0}}
tr.total{{font-weight:700;background:#f1f5f9}} tr.total td{{border-top:2px solid #cbd5e1}}
.mut{{color:#94a3b8}}
.d{{font-size:11px;font-weight:600;padding:1px 5px;border-radius:6px}}
.up{{color:#16a34a;background:#ecfdf3}}.down{{color:#dc2626;background:#fef2f2}}.flat{{color:#475467;background:#f2f4f7}}.na{{color:#98a2b3}}
.otd .d,.otd{{font-size:10px}}
.bar{{display:flex;height:13px;border-radius:4px;overflow:hidden;background:#eef2f6}}
.bar i{{display:block;height:100%}}
.s-w{{background:#2563eb}}.s-g{{background:#16a34a}}.s-o{{background:#da3743}}.s-k{{background:#f59e0b}}.s-r{{background:#8b5cf6}}.s-x{{background:#cbd2d9}}
.legend{{display:flex;gap:14px;font-size:12px;color:#475569;margin:14px 0 2px;flex-wrap:wrap}}
.legend i{{display:inline-block;width:11px;height:11px;border-radius:2px;vertical-align:-1px;margin-right:5px}}
.sec{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;margin:28px 0 8px;border-bottom:1px solid #eef2f6;padding-bottom:6px}}
footer{{margin-top:30px;color:#94a3b8;font-size:11px;border-top:1px solid #eef2f6;padding-top:12px;line-height:1.55}}
@media(max-width:1100px){{.cards{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body>
<a class="back" href="../index.html">← All {MKT} reports</a>
<h1>Aqua {MKT} — Covers &amp; Booking Channels</h1>
<div class="sub">{P['week']} (Mon–Sun) · SevenRooms covers by booking-created date · WoW vs {P['wow']} · YoY vs {P['yoy']}</div>

<div class="callout">{CALLOUT}</div>

<div class="cards">{cards}</div>

<div class="sec">Covers by venue &amp; booking channel</div>
<table><thead><tr>
<th>Venue</th><th>Covers</th><th>WoW</th><th>YoY</th>
<th>Website</th><th>Google Reserve</th><th>{PLAT}</th><th>Walk-in</th><th>Reception</th>
<th>TheFork / First Table</th><th>Other 3rd party</th><th>GA4 bk</th><th>Channel mix</th>
</tr></thead><tbody>{rows}</tbody></table>
<div class="legend">
<span><i class="s-w"></i>Website</span><span><i class="s-g"></i>Google Reserve</span>
<span><i class="s-o"></i>{PLAT}</span><span><i class="s-k"></i>Walk-in</span>
<span><i class="s-r"></i>Reception</span><span><i class="s-x"></i>Third party</span>
</div>

<div class="sec">{PLAT} covers vs total covers — last 8 weeks</div>
<div class="legend"><span><i class="s-x" style="background:#c7dbf2"></i>Total covers (bars)</span><span><i class="s-o"></i>{PLAT} covers (line)</span></div>
{svg}

<footer>
<b>Covers</b> = SevenRooms covers by booking-created date (<code>sr_created_at</code>, {TZ}), net of cancellations and deleted bookings. Bar seating areas excluded; private dining and afternoon tea included.
<b>Website</b> = all bookings originating on our own site: booking widget, campaign landing pages, on-site CTAs (Nav/Hero), menu page and paid-search landing pages. {PLATFOOT}; <b>Google Reserve</b> = Google Reserve Integration; <b>Walk-in</b> = Walk In; <b>Reception</b> = venue reception and reservations desks; <b>TheFork / First Table</b> and <b>Other 3rd party</b> = booking platforms, gifting and concierge partners.
<b>Named-host bookings are excluded from this report:</b> large groups and private dining keyed in by the events and reservations teams are not a marketing channel, so they are removed from the covers total rather than parked in an "Other" bucket. This means covers totals here are lower than in reports before 13 Jul 2026 and are not comparable with them. {COMBNOTE}<b>GA4 bk</b> = website <code>sevenrooms_booking_complete</code> events (shown for context, not directly comparable to covers). Generated {P['generated']}. Source: SevenRooms via Supabase.
</footer>
</body></html>'''
open(OUT, 'w').write(HTML)
print("wrote", OUT, len(HTML), "bytes")
