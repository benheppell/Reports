#!/usr/bin/env python3
# Generic monthly dashboard generator. Usage: monthly_gen.py <payload.json> <out.html>
# Payload: {market, sym, month_label, generated, venues:[{name,act,tgt,mom,yoy,nc}], note}
import json, sys
P = json.load(open(sys.argv[1])); OUT = sys.argv[2]
sym = P.get('sym', '')
mkt = P['market']
back = mkt.replace('Aqua ', '').strip()
month = P['month_label']
gen = P.get('generated', '')
ccy = P.get('ccy', {'HK$':'HKD','£':'GBP','$':'USD'}.get(sym, ''))
vs = P['venues']

def n(x): return f"{round(x):,}"
def pct(cur, base):
    if not base: return None
    return (cur - base) / base * 100.0

def arrow_span(p, inverse=False):
    if p is None: return '<span class="num">—</span>'
    up = p >= 0
    good = up if not inverse else (not up)
    cls = 'pos' if good else 'neg'
    ar = '▲' if up else '▼'
    return f'<span class="{cls}">{ar} {abs(p):.1f}%</span>'

rows = []
tot_act = tot_tgt = tot_mom = tot_yoy = 0
below = 0; counted = 0
for v in vs:
    act = v['act']; tgt = v.get('tgt', 0); mom = v.get('mom', 0); yoy = v.get('yoy', 0)
    nc = v.get('nc', False)
    tot_act += act; tot_tgt += tgt; tot_mom += mom; tot_yoy += yoy
    # variance
    if nc:
        var_html = '<span class="pill" style="background:#eff6ff;color:#2563eb">n/c</span>'
        yoy_html = '<span class="pill" style="background:#eff6ff;color:#2563eb">n/c</span>'
    else:
        counted += 1
        d = act - tgt
        vp = pct(act, tgt)
        cls = 'pos' if d >= 0 else 'neg'
        sign = '+' if d >= 0 else ''
        var_html = f'<span class="{cls}">{sign}{n(d)} ({sign}{vp:.1f}%)</span>' if vp is not None else '—'
        if d < 0: below += 1
        yoy_html = arrow_span(pct(act, yoy))
    mom_html = arrow_span(pct(act, mom))
    rows.append(f'<tr><td>{v["name"]}</td><td class="num">{n(act)}</td><td class="num">{n(tgt)}</td>'
                f'<td class="num">{var_html}</td><td class="num">{mom_html}</td><td class="num">{yoy_html}</td></tr>')

# portfolio
pd = tot_act - tot_tgt
pvp = pct(tot_act, tot_tgt)
pcls = 'pos' if pd >= 0 else 'neg'
psign = '+' if pd >= 0 else ''
prow = (f'<tr class="total"><td>Portfolio</td><td class="num">{n(tot_act)}</td><td class="num">{n(tot_tgt)}</td>'
        f'<td class="num"><span class="{pcls}">{psign}{n(pd)} ({psign}{pvp:.1f}%)</span></td>'
        f'<td class="num">{arrow_span(pct(tot_act, tot_mom))}</td>'
        f'<td class="num">{arrow_span(pct(tot_act, tot_yoy))}</td></tr>')

mom_card = pct(tot_act, tot_mom); yoy_card = pct(tot_act, tot_yoy)
def card_pct(p):
    if p is None: return '—'
    return f'{"+" if p>=0 else ""}{p:.1f}%'
mom_cls = 'pos' if (mom_card or 0) >= 0 else 'neg'
yoy_cls = 'pos' if (yoy_card or 0) >= 0 else 'neg'
note = P.get('note', '')
note_html = f'<div class="obs"><b>Summary</b>{note}</div>' if note else ''

html = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{mkt} — Monthly — {month}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',system-ui,sans-serif;background:#fff;color:#0f172a;line-height:1.5;padding:28px;max-width:1240px;margin:0 auto}}
h1{{font-size:24px;font-weight:700;letter-spacing:-.3px}}
.sub{{color:#64748b;font-size:13px;margin-top:4px}}
.num{{font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}}
.card{{border:1px solid #e2e8f0;border-radius:12px;padding:16px;background:#fafafa}}
.card .lab{{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:#64748b;font-weight:600}}
.card .big{{font-size:26px;font-weight:700;margin-top:6px;font-family:'JetBrains Mono',monospace}}
.card .meta{{font-size:12px;color:#475569;margin-top:6px}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}}
th,td{{padding:9px 10px;text-align:right;border-bottom:1px solid #eef2f6;white-space:nowrap}}
th:first-child,td:first-child{{text-align:left}}
thead th{{font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:#64748b;border-bottom:2px solid #e2e8f0}}
tbody tr:hover{{background:#f8fafc}}
tr.total{{font-weight:700;background:#f1f5f9}}
tr.total td{{border-top:2px solid #cbd5e1}}
.pos{{color:#16a34a;font-weight:600}}
.neg{{color:#dc2626;font-weight:600}}
.pill{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}}
.obs{{background:#f8fafc;border-left:3px solid #94a3b8;padding:10px 14px;margin:18px 0 2px;border-radius:0 8px 8px 0;font-size:13px}}
.obs b{{display:block;margin-bottom:4px;font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:#475569}}
footer{{margin-top:30px;color:#94a3b8;font-size:11px;border-top:1px solid #eef2f6;padding-top:12px}}
a.back{{font-size:12px;color:#2563eb;text-decoration:none}}
@media(max-width:900px){{.cards{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><div><a class="back" href="../index.html">← {back} reports</a>
<h1 style="margin-top:8px">{mkt} — Monthly Performance</h1>
<div class="sub">{month} · GA4 bookings vs monthly target · {ccy} · MoM vs prior month · YoY vs same month last year</div></div>
<div class="cards">
<div class="card"><div class="lab">Monthly Bookings</div><div class="big">{n(tot_act)}</div><div class="meta">Target {n(tot_tgt)} · <span class="{pcls}">{psign}{pvp:.1f}%</span></div></div>
<div class="card"><div class="lab">Month on Month</div><div class="big">{card_pct(mom_card)}</div><div class="meta">vs {n(tot_mom)}</div></div>
<div class="card"><div class="lab">Year on Year</div><div class="big">{card_pct(yoy_card)}</div><div class="meta">vs {n(tot_yoy)}</div></div>
<div class="card"><div class="lab">Venues vs Target</div><div class="big">{counted-below} / {counted}</div><div class="meta">{below} below target.</div></div>
</div>
<table><thead><tr><th>Venue</th><th>Bookings</th><th>Target</th><th>Variance</th><th>MoM</th><th>YoY</th></tr></thead>
<tbody>{''.join(rows)}{prow}</tbody></table>
{note_html}
<footer>GA4 bookings = sevenrooms_booking_complete. Monthly target per the FY26 targets file. Generated {gen}.</footer></body></html>'''
open(OUT, 'w').write(html)
print(f"wrote {OUT} ({len(html)} bytes)")
