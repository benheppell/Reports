#!/usr/bin/env python3
# Generic SLT weekly dashboard generator.  Usage: dashboard_gen.py <payload.json> <out.html>
# Payload: {market, ccy, sym, week, wow, yoy, generated, ytd_label, note,
#           venues:[{name,act,tgt,wow,yoy,ytd,ytdt,meta_s,goog_s}], }
import json, sys

P = json.load(open(sys.argv[1])); OUT = sys.argv[2]
SYM = P['sym']; V = P['venues']


def money(x):
    return f"{SYM}{x:,.0f}"


def pctspan(p, inv=False):
    if p is None:
        return '<span class="num">n/a</span>'
    good = (p < 0) if inv else (p >= 0)
    cls = 'pos' if good else 'neg'
    return f'<span class="{cls} num">{"+" if p >= 0 else ""}{p:.1f}%</span>'


def arrow(p):
    if p is None:
        return '<span class="num">n/a</span>'
    cls = 'pos' if p >= 0 else 'neg'
    ar = '▲' if p >= 0 else '▼'
    return f'<span class="{cls} num">{ar} {abs(p):.1f}%</span>'


rows = ''
tot = {k: 0 for k in ['act', 'tgt', 'ytd', 'ytdt', 'meta_s', 'goog_s', 'wowb', 'yoyb']}
for v in V:
    ad = v['meta_s'] + v['goog_s']
    var = v['act'] - v['tgt']
    varp = var / v['tgt'] * 100 if v['tgt'] else None
    wowp = (v['act'] - v['wow']) / v['wow'] * 100 if v['wow'] else None
    yoyp = (v['act'] - v['yoy']) / v['yoy'] * 100 if v['yoy'] else None
    ytdvar = v['ytd'] - v['ytdt']
    ytdvarp = ytdvar / v['ytdt'] * 100 if v['ytdt'] else None
    cpb = ad / v['act'] if v['act'] else 0
    for k, s in [('act', v['act']), ('tgt', v['tgt']), ('ytd', v['ytd']), ('ytdt', v['ytdt']),
                 ('meta_s', v['meta_s']), ('goog_s', v['goog_s']), ('wowb', v['wow']), ('yoyb', v['yoy'])]:
        tot[k] += s
    nc = ' <span class="pill" style="background:#eff6ff;color:#2563eb">not comparable</span>' if v.get('nc') else ''
    rows += (f'<tr><td>{v["name"]}{nc}</td><td class="num">{v["act"]:,}</td><td class="num">{v["tgt"]:,}</td>'
             f'<td>{pctspan(varp)}</td><td>{arrow(wowp)}</td><td>{arrow(yoyp)}</td>'
             f'<td class="num">{v["ytd"]:,}</td><td>{pctspan(ytdvarp)}</td>'
             f'<td class="num">{money(ad)}</td><td class="num">{money(cpb)}</td></tr>')

ad_t = tot['meta_s'] + tot['goog_s']
varp = (tot['act'] - tot['tgt']) / tot['tgt'] * 100
wowp = (tot['act'] - tot['wowb']) / tot['wowb'] * 100
yoyp = (tot['act'] - tot['yoyb']) / tot['yoyb'] * 100
ytdvarp = (tot['ytd'] - tot['ytdt']) / tot['ytdt'] * 100
rows += (f'<tr class="total"><td>Portfolio</td><td class="num">{tot["act"]:,}</td><td class="num">{tot["tgt"]:,}</td>'
         f'<td>{pctspan(varp)}</td><td>{arrow(wowp)}</td><td>{arrow(yoyp)}</td>'
         f'<td class="num">{tot["ytd"]:,}</td><td>{pctspan(ytdvarp)}</td>'
         f'<td class="num">{money(ad_t)}</td><td class="num">{money(ad_t / tot["act"])}</td></tr>')

below = [v for v in V if v['ytd'] < v['ytdt']]
blist = ', '.join(f'{v["name"]} ({(v["ytd"] - v["ytdt"]) / v["ytdt"] * 100:.1f}%)' for v in below) or 'none'
ontrack = len(V) - len(below)

HTML = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua {P['market']} — SLT Weekly Dashboard — {P['week']}</title>
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
.note{{background:#f8fafc;border-left:3px solid #94a3b8;padding:10px 14px;margin:16px 0 2px;border-radius:0 8px 8px 0;font-size:12.5px;color:#475569}}
footer{{margin-top:30px;color:#94a3b8;font-size:11px;border-top:1px solid #eef2f6;padding-top:12px}}
a.back{{font-size:12px;color:#2563eb;text-decoration:none}}
@media(max-width:900px){{.cards{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><div><a class="back" href="../index.html">← All reports</a>
<h1 style="margin-top:8px">Aqua {P['market']} — SLT Weekly Dashboard</h1>
<div class="sub">{P['week']} (Mon–Sun) · Currency {P['ccy']} · WoW vs {P['wow']} · YoY vs {P['yoy']}</div></div>
<div class="cards">
<div class="card"><div class="lab">Weekly Bookings</div><div class="big">{tot['act']:,}</div>
<div class="meta">Target {tot['tgt']:,} · {pctspan(varp)} · WoW {arrow(wowp)} · YoY {arrow(yoyp)}</div></div>
<div class="card"><div class="lab">YTD Bookings ({P['ytd_label']})</div><div class="big">{tot['ytd']:,}</div>
<div class="meta">Target {tot['ytdt']:,} · {pctspan(ytdvarp)}</div></div>
<div class="card"><div class="lab">Total Ad Spend</div><div class="big">{money(ad_t)}</div>
<div class="meta">Cost per booking {money(ad_t / tot['act'])} · Meta {money(tot['meta_s'])} + Google {money(tot['goog_s'])}</div></div>
<div class="card"><div class="lab">Venues vs Target</div><div class="big">{ontrack} / {len(V)}</div>
<div class="meta">{len(below)} below YTD target: {blist}</div></div>
</div>
<table><thead><tr><th>Venue</th><th>Actual</th><th>Target</th><th>Variance</th><th>WoW</th><th>YoY</th><th>YTD Actual</th><th>YTD vs Target</th><th>Ad Spend</th><th>Cost/Book</th></tr></thead><tbody>
{rows}
</tbody></table>
<div class="note">{P['note']}</div>
<footer>Bookings = GA4 <code>sevenrooms_booking_complete</code>. Ad spend = Meta + Google Ads. Generated {P['generated']}.</footer>
</body></html>'''
open(OUT, 'w').write(HTML)
print("wrote", OUT, len(HTML), "bytes")
