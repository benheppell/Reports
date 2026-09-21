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
# ---- optional extensions (HK Sep 2026). Absent keys => original behaviour, byte-identical output.
GROUPS = P.get('groups', [])      # [{name,label,members:[...],tgt,ytdt,meta_s,goog_s}] combined target + shared ads
OUTSIDE = P.get('outside', [])    # rows shown below the portfolio line, excluded from totals
EXT = bool(GROUPS or OUTSIDE)
DASH = '<span class="num" style="color:#94a3b8">&ndash;</span>'


def _pill(t, bg='#eff6ff', fg='#2563eb'):
    return f' <span class="pill" style="background:{bg};color:{fg}">{t}</span>'


def ext_row(v, cls=''):
    tgt = v.get('tgt'); ytdt = v.get('ytdt')
    varp = (v['act'] - tgt) / tgt * 100 if tgt else None
    wowp = (v['act'] - v['wow']) / v['wow'] * 100 if v.get('wow') else None
    yoyp = (v['act'] - v['yoy']) / v['yoy'] * 100 if v.get('yoy') else None
    ytdvarp = (v['ytd'] - ytdt) / ytdt * 100 if ytdt else None
    if v.get('shared_ads'):
        adc = cpc = _pill('shared', '#f1f5f9', '#475569')
    else:
        ad = v['meta_s'] + v['goog_s']
        base = v.get('cpb_spend', ad)
        adc = f'{money(ad)}'
        cpc = f'{money(base / v["act"])}' if v['act'] else DASH
    pill = _pill(v['pill']) if v.get('pill') else ''
    return (f'<tr{cls}><td>{v["name"]}{pill}</td><td class="num">{v["act"]:,}</td>'
            f'<td class="num">{f"{tgt:,}" if tgt is not None else v.get("tgt_label", DASH)}</td>'
            f'<td>{pctspan(varp) if tgt else DASH}</td><td>{arrow(wowp)}</td>'
            f'<td>{_pill("new venue") if v.get("noyoy") else arrow(yoyp)}</td>'
            f'<td class="num">{v["ytd"]:,}</td><td>{pctspan(ytdvarp) if ytdt else DASH}</td>'
            f'<td class="num">{adc}</td><td class="num">{cpc}</td></tr>')


GROUP_OF = {m: g for g in GROUPS for m in g['members']}
for v in V:
    if EXT and (v.get('tgt') is None or v.get('shared_ads') or v.get('noyoy') or v.get('pill')):
        rows += ext_row(v)
        for k, s in [('act', v['act']), ('ytd', v['ytd']), ('wowb', v['wow']), ('yoyb', v.get('yoy') or 0)]:
            tot[k] += s
        if v.get('tgt') is not None:
            tot['tgt'] += v['tgt']; tot['ytdt'] += v['ytdt']
        if not v.get('shared_ads'):
            tot['meta_s'] += v['meta_s']; tot['goog_s'] += v['goog_s']
        g = GROUP_OF.get(v['name'])
        if g and v['name'] == g['members'][-1]:
            mem = [x for x in V if x['name'] in g['members']]
            gv = {'name': g['label'], 'act': sum(x['act'] for x in mem), 'tgt': g['tgt'], 'ytdt': g['ytdt'],
                  'wow': sum(x['wow'] for x in mem), 'yoy': sum(x.get('yoy') or 0 for x in mem),
                  'ytd': sum(x['ytd'] for x in mem), 'meta_s': g['meta_s'], 'goog_s': g['goog_s']}
            g['_v'] = gv
            rows += ext_row(gv, ' class="grp"')
            tot['tgt'] += g['tgt']; tot['ytdt'] += g['ytdt']
            tot['meta_s'] += g['meta_s']; tot['goog_s'] += g['goog_s']
        continue
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
if OUTSIDE:
    rows += f'<tr class="osep"><td colspan="10">{P.get("outside_label", "Outside the target set")}</td></tr>'
    rows += ''.join(ext_row(v) for v in OUTSIDE)

UNITS = V
if EXT:
    UNITS = [v for v in V if v.get('tgt') is not None] + [dict(g['_v'], name=g['name']) for g in GROUPS if '_v' in g]
below = [v for v in UNITS if v['ytd'] < v['ytdt']]
blist = ', '.join(f'{v["name"]} ({(v["ytd"] - v["ytdt"]) / v["ytdt"] * 100:.1f}%)' for v in below) or 'none'
ontrack = len(UNITS) - len(below)
EXTCSS = ('tr.grp td{background:#fafafa;font-style:italic;color:#334155}'
          'tr.osep td{font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:#64748b;font-weight:700;'
          'padding-top:18px;border-bottom:2px solid #e2e8f0;text-align:left}\n') if EXT else ''

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
{EXTCSS}</style></head><body><div><a class="back" href="../index.html">← All reports</a>
<h1 style="margin-top:8px">Aqua {P['market']} — SLT Weekly Dashboard</h1>
<div class="sub">{P['week']} (Mon–Sun) · Currency {P['ccy']} · WoW vs {P['wow']} · YoY vs {P['yoy']}</div></div>
<div class="cards">
<div class="card"><div class="lab">Weekly Bookings</div><div class="big">{tot['act']:,}</div>
<div class="meta">Target {tot['tgt']:,} · {pctspan(varp)} · WoW {arrow(wowp)} · YoY {arrow(yoyp)}</div></div>
<div class="card"><div class="lab">YTD Bookings ({P['ytd_label']})</div><div class="big">{tot['ytd']:,}</div>
<div class="meta">Target {tot['ytdt']:,} · {pctspan(ytdvarp)}</div></div>
<div class="card"><div class="lab">Total Ad Spend</div><div class="big">{money(ad_t)}</div>
<div class="meta">Cost per booking {money(ad_t / tot['act'])} · Meta {money(tot['meta_s'])} + Google {money(tot['goog_s'])}</div></div>
<div class="card"><div class="lab">Venues vs Target</div><div class="big">{ontrack} / {len(UNITS)}</div>
<div class="meta">{len(below)} below YTD target: {blist}</div></div>
</div>
<table><thead><tr><th>Venue</th><th>Actual</th><th>Target</th><th>Variance</th><th>WoW</th><th>YoY</th><th>YTD Actual</th><th>YTD vs Target</th><th>Ad Spend</th><th>Cost/Book</th></tr></thead><tbody>
{rows}
</tbody></table>
<div class="note">{P['note']}</div>
<footer>Bookings = GA4 <code>sevenrooms_booking_complete</code>. Ad spend = Meta + Google Ads. Generated {P['generated']}.{P.get('foot_extra', '')}</footer>
</body></html>'''
open(OUT, 'w').write(HTML)
print("wrote", OUT, len(HTML), "bytes")
