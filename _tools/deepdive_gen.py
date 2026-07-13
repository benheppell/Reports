#!/usr/bin/env python3
# Generic venue deep-dive generator. Usage: deepdive_gen.py <payload.json> <out.html>
import json, sys

P = json.load(open(sys.argv[1])); OUT = sys.argv[2]
SYM = P['sym']; V = P['venues']; TH = P['cpa']
COL = ['#EF4444', '#F59E0B', '#3B82F6', '#8B5CF6', '#10B981', '#EC4899']


def money(x, d=0):
    return f"{SYM}{x:,.{d}f}"


def arrow(p):
    if p is None:
        return '<span class="num">n/a</span>'
    cls = 'pos' if p >= 0 else 'neg'
    return f'<span class="{cls} num">{"▲" if p >= 0 else "▼"} {abs(p):.1f}%</span>'


def cpacell(v, good, poor):
    cls = 'pos' if v <= good else ('neg' if v >= poor else '')
    return f'<td class="num {cls}">{money(v, 2)}</td>'


def mmss(s):
    return f"{int(s) // 60}:{int(s) % 60:02d}"


# ---------- cards ----------
tot_b = sum(v['act'] for v in V); tot_t = sum(v['tgt'] for v in V)
tot_bp = sum(v['wow_b'] for v in V); tot_by = sum(v['yoy_b'] for v in V)
tot_ms = sum(v['meta_s'] for v in V); tot_gs = sum(v['goog_s'] for v in V)
tot_u = sum(v['users'] for v in V); ad = tot_ms + tot_gs
wowp = (tot_b - tot_bp) / tot_bp * 100 if tot_bp else None
yoyp = (tot_b - tot_by) / tot_by * 100 if tot_by else None
varp = (tot_b - tot_t) / tot_t * 100 if tot_t else None
cvr = tot_b / tot_u * 100 if tot_u else 0

# ---------- Meta ----------
mrows = ''
for v in V:
    cps = v['meta_s'] / v['meta_sch'] if v['meta_sch'] else 0
    w = (v['meta_sch'] - v['meta_sch_prior']) / v['meta_sch_prior'] * 100 if v['meta_sch_prior'] else None
    mrows += (f'<tr><td>{v["name"]}</td><td class="num">{money(v["meta_s"])}</td>'
              f'<td class="num">{v["meta_sch"]:,}</td>{cpacell(cps, TH["meta_good"], TH["meta_poor"])}'
              f'<td>{arrow(w)}</td></tr>')
tms = sum(v['meta_sch'] for v in V); tmsp = sum(v['meta_sch_prior'] for v in V)
mrows += (f'<tr class="total"><td>Total</td><td class="num">{money(tot_ms)}</td><td class="num">{tms:,}</td>'
          f'<td class="num">{money(tot_ms / tms, 2) if tms else "—"}</td>'
          f'<td>{arrow((tms - tmsp) / tmsp * 100 if tmsp else None)}</td></tr>')

# ---------- Google ----------
grows = ''
for v in V:
    cpc = v['goog_s'] / v['goog_c'] if v['goog_c'] else 0
    w = (v['goog_c'] - v['goog_c_prior']) / v['goog_c_prior'] * 100 if v['goog_c_prior'] else None
    sh = ' <span class="mut">(shared)</span>' if v.get('shared') else ''
    grows += (f'<tr><td>{v["name"]}{sh}</td><td class="num">{money(v["goog_s"])}</td>'
              f'<td class="num">{v["goog_c"]:,.0f}</td>{cpacell(cpc, TH["goog_good"], TH["goog_poor"])}'
              f'<td>{arrow(w)}</td></tr>')
tgc = sum(v['goog_c'] for v in V); tgcp = sum(v['goog_c_prior'] for v in V)
grows += (f'<tr class="total"><td>Total</td><td class="num">{money(tot_gs)}</td><td class="num">{tgc:,.0f}</td>'
          f'<td class="num">{money(tot_gs / tgc, 2) if tgc else "—"}</td>'
          f'<td>{arrow((tgc - tgcp) / tgcp * 100 if tgcp else None)}</td></tr>')

# ---------- GA4 ----------
arows = ''
for v in V:
    ucvr = v['act'] / v['users'] * 100 if v['users'] else 0
    scvr = v['act'] / v['sessions'] * 100 if v['sessions'] else 0
    bcls = 'neg' if v['bounce'] > 0.45 else ''
    ccls = 'pos' if ucvr > 6 else ('neg' if ucvr < 4 else '')
    bkcls = 'pos' if v['act'] >= v['wow_b'] else 'neg'
    arows += (f'<tr><td>{v["name"]}</td><td class="num">{v["sessions"]:,}</td><td class="num">{v["users"]:,}</td>'
              f'<td class="num">{mmss(v["asd"])}</td><td class="num {bcls}">{v["bounce"] * 100:.1f}%</td>'
              f'<td class="num {bkcls}">{v["act"]:,}</td><td class="num {ccls}">{ucvr:.2f}%</td>'
              f'<td class="num">{scvr:.2f}%</td></tr>')
ts = sum(v['sessions'] for v in V)
arows += (f'<tr class="total"><td>Total</td><td class="num">{ts:,}</td><td class="num">{tot_u:,}</td>'
          f'<td class="num">—</td><td class="num">—</td><td class="num">{tot_b:,}</td>'
          f'<td class="num">{cvr:.2f}%</td><td class="num">{tot_b / ts * 100:.2f}%</td></tr>')


def obs(title, items):
    li = ''.join(f'<li>{i}</li>' for i in items)
    return f'<div class="obs"><b>{title}</b><ul>{li}</ul></div>'


# ---------- trends ----------
S = P['series']; labels = S['labels']
names = [v['name'] for v in V]
bk = {n: S['venues'][n]['bookings'] for n in names}
us = {n: S['venues'][n]['users'] for n in names}
cv = {n: [round(b / u * 100, 2) if u else 0 for b, u in zip(bk[n], us[n])] for n in names}

trows = ''
for i, n in enumerate(names):
    b0, b1 = bk[n][0], bk[n][-1]
    tb = (b1 - b0) / b0 * 100 if b0 else 0
    c0, c1 = cv[n][0], cv[n][-1]
    trows += (f'<tr><td>{n}</td><td>Bookings</td>'
              + ''.join(f'<td class="num">{x:,}</td>' for x in bk[n])
              + f'<td class="num {"pos" if tb >= 0 else "neg"}">{"+" if tb >= 0 else ""}{tb:.1f}%</td></tr>')
    trows += (f'<tr><td></td><td>User CVR</td>'
              + ''.join(f'<td class="num">{x:.2f}%</td>' for x in cv[n])
              + f'<td class="num {"pos" if c1 >= c0 else "neg"}">{"+" if c1 >= c0 else ""}{c1 - c0:.2f}pp</td></tr>')

DS = json.dumps({'labels': labels, 'names': names, 'bk': bk, 'us': us, 'cv': cv, 'col': COL[:len(names)],
                 'tgt': {v['name']: v['tgt'] for v in V}})

HTML = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua {P['market']} — Venue Deep Dive — {P['week']}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',system-ui,sans-serif;background:#fff;color:#0f172a;line-height:1.5;padding:28px;max-width:1240px;margin:0 auto}}
h1{{font-size:24px;font-weight:700;letter-spacing:-.3px}}
.sub{{color:#64748b;font-size:13px;margin-top:4px}}
.num{{font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums}}
.badge{{display:inline-block;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;background:#fef2f2;color:#dc2626;margin-left:8px;vertical-align:middle}}
.tabs{{display:flex;gap:4px;margin:20px 0 0;border-bottom:2px solid #e2e8f0}}
.tab{{padding:9px 18px;font-size:13px;font-weight:600;color:#64748b;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px}}
.tab.on{{color:#2563eb;border-bottom-color:#2563eb}}
.pane{{display:none}} .pane.on{{display:block}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}}
.card{{border:1px solid #e2e8f0;border-radius:12px;padding:16px;background:#fafafa}}
.card .lab{{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:#64748b;font-weight:600}}
.card .big{{font-size:26px;font-weight:700;margin-top:6px;font-family:'JetBrains Mono',monospace}}
.card .meta{{font-size:12px;color:#475569;margin-top:6px}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}}
th,td{{padding:9px 10px;text-align:right;border-bottom:1px solid #eef2f6;white-space:nowrap}}
th:first-child,td:first-child{{text-align:left}}
th:nth-child(2),td:nth-child(2){{text-align:left}}
thead th{{font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:#64748b;border-bottom:2px solid #e2e8f0}}
tbody tr:hover{{background:#f8fafc}}
tr.total{{font-weight:700;background:#f1f5f9}} tr.total td{{border-top:2px solid #cbd5e1}}
.pos{{color:#16a34a;font-weight:600}} .neg{{color:#dc2626;font-weight:600}} .mut{{color:#94a3b8;font-weight:400}}
.sec{{margin-top:26px;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden}}
.sec h2{{font-size:14px;padding:11px 14px;color:#fff;font-weight:600}}
.sec .body{{padding:6px 14px 14px}}
.blue h2{{background:#2563eb}} .green h2{{background:#16a34a}} .amber h2{{background:#d97706}}
.obs{{background:#f8fafc;border-left:3px solid #94a3b8;padding:10px 14px;margin:12px 14px 2px;border-radius:0 8px 8px 0;font-size:13px}}
.obs b{{display:block;margin-bottom:4px;font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:#475569}}
.obs ul{{margin-left:16px}} .obs li{{margin:3px 0}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}}
.chart{{border:1px solid #e2e8f0;border-radius:12px;padding:14px;height:280px}}
.chart h3{{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#64748b;margin-bottom:8px}}
footer{{margin-top:30px;color:#94a3b8;font-size:11px;border-top:1px solid #eef2f6;padding-top:12px}}
a.back{{font-size:12px;color:#2563eb;text-decoration:none}}
@media(max-width:900px){{.cards,.grid2{{grid-template-columns:1fr 1fr}}}}
</style></head><body>
<div><a class="back" href="../index.html">← All reports</a>
<h1 style="margin-top:8px">Aqua {P['market']} — Venue Deep Dive<span class="badge">{P['badge']}</span></h1>
<div class="sub">{P['week']} (Mon–Sun) · Currency {P['ccy']} · {', '.join(names)} · WoW vs {P['wow']} · YoY vs {P['yoy']}</div></div>

<div class="tabs"><div class="tab on" data-t="p">Performance</div><div class="tab" data-t="t">Weekly Trends</div></div>

<div class="pane on" id="p">
<div class="cards">
<div class="card"><div class="lab">Combined Bookings</div><div class="big">{tot_b:,}</div>
<div class="meta">Target {tot_t:,} · {"+" if varp >= 0 else ""}{varp:.1f}% · WoW {arrow(wowp)}</div></div>
<div class="card"><div class="lab">Combined Ad Spend</div><div class="big">{money(ad)}</div>
<div class="meta">Cost per booking {money(ad / tot_b, 2)} · Meta {money(tot_ms)} + Google {money(tot_gs)}</div></div>
<div class="card"><div class="lab">Combined Users</div><div class="big">{tot_u:,}</div>
<div class="meta">Blended user CVR {cvr:.2f}%</div></div>
<div class="card"><div class="lab">YoY Bookings</div><div class="big">{"+" if yoyp >= 0 else ""}{yoyp:.1f}%</div>
<div class="meta">{tot_b:,} vs {tot_by:,} same week last year</div></div>
</div>

<div class="sec blue"><h2>Meta Ads</h2><div class="body">
<table><thead><tr><th>Venue</th><th>Spend</th><th>Schedules</th><th>Cost/Sched</th><th>WoW Sched</th></tr></thead>
<tbody>{mrows}</tbody></table></div>
{obs('Observations', P['obs']['meta'])}</div>

<div class="sec green"><h2>Google Ads</h2><div class="body">
<table><thead><tr><th>Venue</th><th>Spend</th><th>Conversions</th><th>Cost/Conv</th><th>WoW Conv</th></tr></thead>
<tbody>{grows}</tbody></table></div>
{obs('Observations', P['obs']['google'])}</div>

<div class="sec amber"><h2>GA4 Website</h2><div class="body">
<table><thead><tr><th>Venue</th><th>Sessions</th><th>Users</th><th>Avg Sess Dur</th><th>Bounce Rate</th><th>Bookings</th><th>User CVR</th><th>Sess CVR</th></tr></thead>
<tbody>{arows}</tbody></table></div>
{obs('Observations', P['obs']['ga4'])}</div>
</div>

<div class="pane" id="t">
<p class="sub" style="margin-top:18px">8-week trend ({labels[0]} to {labels[-1]}) across GA4 bookings, user conversion rate, and users.</p>
<div class="grid2">
<div class="chart"><h3>GA4 Bookings (weekly)</h3><canvas id="c1"></canvas></div>
<div class="chart"><h3>User Conversion Rate (%)</h3><canvas id="c2"></canvas></div>
<div class="chart"><h3>Users (weekly)</h3><canvas id="c3"></canvas></div>
<div class="chart"><h3>Bookings vs Target (latest week)</h3><canvas id="c4"></canvas></div>
</div>
<table style="margin-top:24px"><thead><tr><th>Venue</th><th>Metric</th>
{''.join(f'<th>{l}</th>' for l in labels)}<th>Trend</th></tr></thead><tbody>{trows}</tbody></table>
</div>

<footer>Bookings = GA4 <code>sevenrooms_booking_complete</code>. Meta schedules = <code>offsite_conversion.fb_pixel_custom</code>. Google conversions filtered to the venue booking action. Generated {P['generated']}.</footer>
<script>
const D={DS};
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
  document.querySelectorAll('.pane').forEach(x=>x.classList.remove('on'));
  t.classList.add('on');document.getElementById(t.dataset.t).classList.add('on');
  if(t.dataset.t==='t'&&!window._drawn){{window._drawn=1;draw();}}
}});
function line(id,get,suf){{
 new Chart(document.getElementById(id),{{type:'line',
  data:{{labels:D.labels,datasets:D.names.map((n,i)=>({{label:n,data:get(n),borderColor:D.col[i],backgroundColor:D.col[i],tension:.3,borderWidth:2,pointRadius:3}}))}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10,font:{{size:10}}}}}}}},
   scales:{{y:{{beginAtZero:false,ticks:{{callback:v=>v+(suf||'')}}}}}}}}}});
}}
function draw(){{
 line('c1',n=>D.bk[n]);line('c2',n=>D.cv[n],'%');line('c3',n=>D.us[n]);
 new Chart(document.getElementById('c4'),{{type:'bar',
  data:{{labels:D.names,datasets:[
   {{label:'Actual',data:D.names.map(n=>D.bk[n][D.bk[n].length-1]),backgroundColor:'#3B82F6'}},
   {{label:'Target',data:D.names.map(n=>D.tgt[n]),backgroundColor:'#cbd5e1'}}]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10,font:{{size:10}}}}}}}}}}}});
}}
</script></body></html>'''
open(OUT, 'w').write(HTML)
print("wrote", OUT, len(HTML), "bytes")
