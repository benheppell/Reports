#!/usr/bin/env python3
# Builds london/m2026-06/dashboard.html (full per-venue monthly) from _tools/london_data/*.json
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "london_data")
OUT  = os.path.join(HERE, "..", "london", "m2026-06", "dashboard.html")

# Dined covers (SevenRooms), by venue -> period. Revenue omitted (total_payment unreliable for several London venues).
COVERS = {
 "shard":  {"2026-06":14696,"2026-05":15549,"2025-06":15977},
 "regent": {"2026-06":6528, "2026-05":6603, "2025-06":6518},
 "hutong": {"2026-06":8959, "2026-05":10346,"2025-06":9194},
 "azzurra":{"2026-06":3398, "2026-05":4564, "2025-06":2788},
 "dsl":    {"2026-06":10728,"2026-05":11019,"2025-06":3972},
 "shiro":  {"2026-06":3456, "2026-05":2338, "2025-06":3007},
}
VENUES = [
 ("shard","Aqua Shard"),
 ("hutong","Hutong London"),
 ("regent","Regent St — Kyoto + Nueva"),
 ("dsl","Dim Sum Library"),
 ("azzurra","Azzurra"),
 ("shiro","Shiro Sushi"),
]
def load(k): return json.load(open(os.path.join(DATA,k+".json")))
G = load("google")

def ga4norm(d):
    if "2026-06" in d: return d
    if "202606" in d: return {"2026-06":d["202606"],"2026-05":d["202605"],"2025-06":d["202506"]}
    tu,bk=d["totalUsers"],d["bookings"]
    return {p2:{"users":tu[p1],"bookings":bk[p1]} for p1,p2 in [("202606","2026-06"),("202605","2026-05"),("202506","2025-06")]}
def metanorm(t):
    if "2026-06" in t: return t
    return {"2026-06":t["202606"],"2026-05":t["202605"],"2025-06":t["202506"]}

def pct(c,p):
    if not p: return None
    return (c-p)/p*100.0
def chip(c,p,inv=False,pt=False):
    v=pct(c,p)
    if v is None: return '<span class="flat">—</span>'
    good = (v<0) if inv else (v>0)
    cls = "flat" if abs(v)<1.0 else ("pos" if good else "neg")
    ar = "▬" if abs(v)<1.0 else ("▲" if v>0 else "▼")
    if pt:
        return f'<span class="{cls}">{ar} {abs(c-p):.1f}pt</span>'
    return f'<span class="{cls}">{ar} {abs(v):.1f}%</span>'
def nf(n): return f"{round(n):,}"
def gbp(n): return "£"+f"{round(n):,}"

# ---- gather per venue ----
data={}
metajs={}
for k,disp in VENUES:
    v=load(k)
    ga=ga4norm(v["ga4"]); mt=metanorm(v["meta"]["totals"]); gg=G[k]
    data[k]={"disp":disp,"ga":ga,"mt":mt,"gg":gg,"cov":COVERS[k],"meta_ads":v["meta"]["ads"]}
    metajs[k]=v["meta"]["ads"]

# portfolio aggregates (June)
port_cov={p:sum(COVERS[k][p] for k,_ in VENUES) for p in ("2026-06","2026-05","2025-06")}
port_meta_sp=sum(data[k]["mt"]["2026-06"]["spend"] for k,_ in VENUES)
port_goog_sp=sum(data[k]["gg"]["2026-06"]["cost"] for k,_ in VENUES)
port_spend=port_meta_sp+port_goog_sp
port_ga_bk={p:sum(data[k]["ga"][p]["bookings"] for k,_ in VENUES) for p in ("2026-06","2026-05","2025-06")}
n_meta_ads=sum(len(metajs[k]) for k,_ in VENUES)
n_goog_ads=sum(len(data[k]["gg"]["ads"]) for k,_ in VENUES)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',system-ui,sans-serif;background:#fff;color:#0f172a;line-height:1.5;padding:24px;max-width:1240px;margin:0 auto}
a.back{font-size:12px;color:#2563eb;text-decoration:none}
h1{font-size:24px;font-weight:700;letter-spacing:-.3px;margin-top:8px}
.sub{color:#64748b;font-size:13px;margin-top:4px}
.exec{background:#fbf7f4;border:1px solid #ecd9cf;border-left:4px solid #7c2d3a;border-radius:10px;padding:14px 16px;margin:18px 0 6px;font-size:13.5px}
.exec b{color:#7c2d3a}
.num{font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums}
.nav{position:sticky;top:0;background:#fff;z-index:5;display:flex;gap:6px;flex-wrap:wrap;padding:10px 0;border-bottom:1px solid #eef2f6;margin:14px 0}
.nav a{font-size:12px;font-weight:600;color:#475569;text-decoration:none;padding:5px 10px;border:1px solid #e2e8f0;border-radius:8px}
.nav a:hover{border-color:#7c2d3a;color:#7c2d3a}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
th,td{padding:7px 9px;text-align:right;border-bottom:1px solid #eef2f6;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
thead th{font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:#64748b;border-bottom:2px solid #e2e8f0}
tbody tr:hover{background:#f8fafc}
tr.total{font-weight:700;background:#f1f5f9}
tr.total td{border-top:2px solid #cbd5e1}
.pos{color:#16a34a;font-weight:600}.neg{color:#dc2626;font-weight:600}.flat{color:#94a3b8;font-weight:600}
.tag{display:inline-block;padding:1px 7px;border-radius:999px;font-size:10.5px;font-weight:600}
.t-pro{background:#e0edff;color:#1d4ed8}.t-rem{background:#dcfce7;color:#15803d}.t-awr{background:#fef3c7;color:#b45309}
.thumb{display:inline-block;width:32px;height:32px;border-radius:6px;overflow:hidden;border:1px solid #e2e8f0;vertical-align:middle;background:#f1f5f9}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.pv{font-size:11px;color:#2563eb;text-decoration:none;font-weight:600;margin-left:6px}
.venue{margin-top:34px;border-top:3px solid #7c2d3a;padding-top:12px}
.venue h2{font-size:19px;font-weight:700}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:12px 0}
.card{border:1px solid #e2e8f0;border-radius:12px;padding:13px 14px;background:#fafafa}
.card .lab{font-size:10.5px;text-transform:uppercase;letter-spacing:.5px;color:#64748b;font-weight:600}
.card .big{font-size:22px;font-weight:700;margin-top:5px;font-family:'JetBrains Mono',monospace}
.card .meta{font-size:11.5px;color:#475569;margin-top:5px}
.sec{margin-top:16px;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden}
.sec h3{font-size:12.5px;padding:8px 12px;color:#fff;font-weight:600}
.sec .body{padding:6px 12px 12px}
.maroon h3{background:#7c2d3a}.blue h3{background:#2563eb}.green h3{background:#16a34a}.slate h3{background:#475569}
.mini{font-size:11px;color:#94a3b8;margin-top:6px}
details{margin-top:8px}summary{cursor:pointer;font-size:12.5px;font-weight:600;color:#334155;padding:6px 0}
footer{margin-top:34px;color:#94a3b8;font-size:11px;border-top:1px solid #eef2f6;padding-top:12px;line-height:1.6}
@media(max-width:900px){.cards{grid-template-columns:repeat(2,1fr)}}
"""

def covers_cards(k):
    c=data[k]["cov"]; ga=data[k]["ga"]; mt=data[k]["mt"]; gg=data[k]["gg"]
    cr=lambda p: (ga[p]["bookings"]/ga[p]["users"]*100.0) if ga[p]["users"] else 0
    sp=mt["2026-06"]["spend"]+gg["2026-06"]["cost"]
    return f"""<div class="cards">
<div class="card"><div class="lab">Dined covers</div><div class="big">{nf(c['2026-06'])}</div><div class="meta">MoM {chip(c['2026-06'],c['2026-05'])} · YoY {chip(c['2026-06'],c['2025-06'])}</div></div>
<div class="card"><div class="lab">Web bookings (GA4)</div><div class="big">{nf(ga['2026-06']['bookings'])}</div><div class="meta">MoM {chip(ga['2026-06']['bookings'],ga['2026-05']['bookings'])} · YoY {chip(ga['2026-06']['bookings'],ga['2025-06']['bookings'])}</div></div>
<div class="card"><div class="lab">Conversion rate</div><div class="big">{cr('2026-06'):.1f}%</div><div class="meta">MoM {chip(cr('2026-06'),cr('2026-05'),pt=True)} · YoY {chip(cr('2026-06'),cr('2025-06'),pt=True)}</div></div>
<div class="card"><div class="lab">Paid spend (Jun)</div><div class="big">{gbp(sp)}</div><div class="meta">Meta {gbp(mt['2026-06']['spend'])} · Google {gbp(gg['2026-06']['cost'])}</div></div>
</div>"""

def website_tbl(k):
    ga=data[k]["ga"]
    def cr(p): return (ga[p]["bookings"]/ga[p]["users"]*100.0) if ga[p]["users"] else 0
    return f"""<table><thead><tr><th>Website (GA4)</th><th>Jun 2026</th><th>May 2026</th><th>MoM</th><th>Jun 2025</th><th>YoY</th></tr></thead><tbody>
<tr><td>Users</td><td class="num">{nf(ga['2026-06']['users'])}</td><td class="num">{nf(ga['2026-05']['users'])}</td><td class="num">{chip(ga['2026-06']['users'],ga['2026-05']['users'])}</td><td class="num">{nf(ga['2025-06']['users'])}</td><td class="num">{chip(ga['2026-06']['users'],ga['2025-06']['users'])}</td></tr>
<tr><td>Web bookings</td><td class="num">{nf(ga['2026-06']['bookings'])}</td><td class="num">{nf(ga['2026-05']['bookings'])}</td><td class="num">{chip(ga['2026-06']['bookings'],ga['2026-05']['bookings'])}</td><td class="num">{nf(ga['2025-06']['bookings'])}</td><td class="num">{chip(ga['2026-06']['bookings'],ga['2025-06']['bookings'])}</td></tr>
<tr class="total"><td>Conversion rate</td><td class="num">{cr('2026-06'):.2f}%</td><td class="num">{cr('2026-05'):.2f}%</td><td class="num">{chip(cr('2026-06'),cr('2026-05'),pt=True)}</td><td class="num">{cr('2025-06'):.2f}%</td><td class="num">{chip(cr('2026-06'),cr('2025-06'),pt=True)}</td></tr>
</tbody></table>"""

def paid_tbl(k):
    mt=data[k]["mt"]; gg=data[k]["gg"]
    def row(label,sp,bk,spP,spY):
        cpa = (sp/bk) if bk else 0
        return f'<tr><td>{label}</td><td class="num">{gbp(sp)}</td><td class="num">{nf(bk)}</td><td class="num">{gbp(cpa) if bk else "—"}</td><td class="num">{chip(sp,spP)}</td><td class="num">{chip(sp,spY)}</td></tr>'
    m=mt["2026-06"]; g=gg["2026-06"]
    tot_sp=m["spend"]+g["cost"]
    return f"""<table><thead><tr><th>Paid media (Jun)</th><th>Spend</th><th>Bookings*</th><th>CPA</th><th>Spend MoM</th><th>Spend YoY</th></tr></thead><tbody>
{row('Meta',m['spend'],m['bk'],mt['2026-05']['spend'],mt['2025-06']['spend'])}
{row('Google',g['cost'],g['bk'],gg['2026-05']['cost'],gg['2025-06']['cost'])}
<tr class="total"><td>Total spend</td><td class="num">{gbp(tot_sp)}</td><td class="num">—</td><td class="num">—</td><td class="num"></td><td class="num"></td></tr>
</tbody></table>
<div class="mini">*Platform-reported conversions: Meta = SCHEDULE event; Google = SevenRooms "booking complete" (bookings-only — store-visits, calls and enquiries excluded). Each platform uses its own attribution (view-through included), so the two overlap each other and GA4 and are <b>not additive</b> to covers.</div>"""

def google_tbl(k):
    ads=data[k]["gg"]["ads"]
    if not ads: return '<div class="mini">No Google ad delivery in June.</div>'
    rows=""
    tc=ti=tk=0
    for name,cost,impr,clk in ads:
        ctr=(clk/impr*100.0) if impr else 0
        rows+=f'<tr><td>{name}</td><td class="num">{gbp(cost)}</td><td class="num">{nf(impr)}</td><td class="num">{nf(clk)}</td><td class="num">{ctr:.1f}%</td></tr>'
        tc+=cost;ti+=impr;tk+=clk
    tctr=(tk/ti*100.0) if ti else 0
    return f"""<table><thead><tr><th>Campaign · ad group</th><th>Cost</th><th>Impr.</th><th>Clicks</th><th>CTR</th></tr></thead><tbody>
{rows}<tr class="total"><td>Total — {len(ads)} ad groups</td><td class="num">{gbp(tc)}</td><td class="num">{nf(ti)}</td><td class="num">{nf(tk)}</td><td class="num">{tctr:.1f}%</td></tr>
</tbody></table>"""

# per venue blocks
blocks=""
for k,disp in VENUES:
    mt=data[k]["mt"];gg=data[k]["gg"]
    blocks+=f"""<div class="venue" id="{k}"><h2>{disp}</h2>
{covers_cards(k)}
<div class="sec blue"><h3>Website</h3><div class="body">{website_tbl(k)}</div></div>
<div class="sec green"><h3>Paid media</h3><div class="body">{paid_tbl(k)}</div></div>
<div class="sec slate"><h3>Live ads — Meta ({len(metajs[k])})</h3><div class="body">
<div class="mini">Every Meta ad that delivered in June. Click a thumbnail to open the creative.</div>
<details open><summary>Show ad-by-ad table</summary>
<table><thead><tr><th>Preview</th><th>Ad</th><th>Stage</th><th>Spend</th><th>Impr.</th><th>Clicks</th><th>CTR</th><th>Bk</th><th>CPA</th></tr></thead>
<tbody id="mb_{k}"></tbody></table></details></div></div>
<div class="sec slate"><h3>Live ads — Google search ({len(gg['ads'])})</h3><div class="body">{google_tbl(k)}</div></div>
</div>"""

nav="".join(f'<a href="#{k}">{disp.split(" — ")[0]}</a>' for k,disp in VENUES)

# portfolio summary table
psum=""
for k,disp in VENUES:
    c=data[k]["cov"];ga=data[k]["ga"];sp=data[k]["mt"]["2026-06"]["spend"]+data[k]["gg"]["2026-06"]["cost"]
    psum+=f'<tr><td><a href="#{k}" style="color:#2563eb;text-decoration:none">{disp.split(" — ")[0]}</a></td><td class="num">{nf(c["2026-06"])}</td><td class="num">{chip(c["2026-06"],c["2026-05"])}</td><td class="num">{chip(c["2026-06"],c["2025-06"])}</td><td class="num">{nf(ga["2026-06"]["bookings"])}</td><td class="num">{gbp(sp)}</td></tr>'
psum+=f'<tr class="total"><td>Portfolio</td><td class="num">{nf(port_cov["2026-06"])}</td><td class="num">{chip(port_cov["2026-06"],port_cov["2026-05"])}</td><td class="num">{chip(port_cov["2026-06"],port_cov["2025-06"])}</td><td class="num">{nf(port_ga_bk["2026-06"])}</td><td class="num">{gbp(port_spend)}</td></tr>'

exec_txt=f"""<b>The read.</b> Across the six London venues, June delivered <b>{nf(port_cov['2026-06'])} dined covers</b> — down {abs(pct(port_cov['2026-06'],port_cov['2026-05'])):.0f}% on May but up {pct(port_cov['2026-06'],port_cov['2025-06']):.0f}% YoY, almost entirely on Dim Sum Library, which has roughly tripled year-on-year post-rebrand ({nf(COVERS['dsl']['2025-06'])}→{nf(COVERS['dsl']['2026-06'])}). Aqua Shard remains the volume anchor at {nf(COVERS['shard']['2026-06'])} covers, and Shiro (+15% YoY) and Azzurra (+22% YoY, on the Jazz Night push) are the other bright spots; Hutong and Regent St softened month-on-month. Paid media spent <b>{gbp(port_spend)}</b> in June ({gbp(port_meta_sp)} Meta + {gbp(port_goog_sp)} Google). One measurement caveat carried throughout: Google's reported "bookings" are its own SevenRooms conversion attribution (view-through included) and run far higher than GA4 last-click — they are directional efficiency signals, not additive covers."""

html=f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua London — Monthly — June 2026</title><style>{CSS}</style></head><body>
<a class="back" href="../index.html">← All London reports</a>
<h1>Aqua London — Monthly Performance</h1>
<div class="sub">June 2026 (full calendar month) · GBP · MoM vs May 2026 · YoY vs June 2025 · six venues, reported separately</div>
<div class="exec">{exec_txt}</div>
<div class="nav">{nav}</div>
<table><thead><tr><th>Venue</th><th>Dined covers</th><th>MoM</th><th>YoY</th><th>Web bk</th><th>Paid spend</th></tr></thead><tbody>{psum}</tbody></table>
<div class="mini">Dined covers = SevenRooms completed covers by service date. Regent St combines Aqua Kyoto + Aqua Nueva. Revenue omitted for London (SevenRooms total_payment is not reliably populated across these venues).</div>
{blocks}
<footer>
Aqua London portfolio · June 2026 full calendar month · GBP · MoM vs May 2026 · YoY vs June 2025.
Covers: SevenRooms via Supabase (status Complete by service date). Website: GA4 per venue, metric totalUsers, booking event sevenrooms_booking_complete (Regent St = Kyoto+Nueva GA4 combined).
Meta: per-venue ad accounts, bookings = SCHEDULE conversion. Google Ads: per-venue accounts via MCC, bookings = SevenRooms "booking complete" conversions only (store-visits, calls, private-event enquiries and GA4-duplicate actions excluded); cost in GBP.
Platform-reported ad bookings use each platform's own attribution, overlap each other and GA4, and are not additive to covers. {n_meta_ads} Meta ads and {n_goog_ads} Google ad groups delivered across the portfolio in June. Generated 2 July 2026.
</footer>
<script>
var B="https://assets-organizer-cdn.gomarble.ai/mcp-agent/ad-assets/";
var ADS={json.dumps(metajs)};
var STG={{"pro":["Prospecting","t-pro"],"rem":["Remarketing","t-rem"],"awr":["Awareness","t-awr"]}};
function nf(n){{return Math.round(n).toLocaleString();}}
Object.keys(ADS).forEach(function(k){{
 var rows="";
 ADS[k].slice().sort(function(a,b){{return b[2]-a[2];}}).forEach(function(a){{
  var cpa=a[6]?("£"+Math.round(a[2]/a[6])):"—";
  var st=STG[a[1]]||STG["pro"];
  var asset=B+a[7], thumb=B+a[8], isVid=/\\.mp4$/.test(a[7]);
  var prev='<a class="thumb" href="'+asset+'" target="_blank" rel="noopener"><img loading="lazy" src="'+thumb+'" alt=""></a><a class="pv" href="'+asset+'" target="_blank" rel="noopener">'+(isVid?'▶':'◱')+'</a>';
  rows+='<tr><td style="text-align:left">'+prev+'</td><td>'+a[0]+'</td><td style="text-align:left"><span class="tag '+st[1]+'">'+st[0]+'</span></td><td class="num">£'+nf(a[2])+'</td><td class="num">'+nf(a[3])+'</td><td class="num">'+nf(a[4])+'</td><td class="num">'+a[5].toFixed(2)+'%</td><td class="num">'+a[6]+'</td><td class="num">'+cpa+'</td></tr>';
 }});
 var el=document.getElementById("mb_"+k); if(el) el.innerHTML=rows;
}});
</script>
</body></html>"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT,"w").write(html)
print("WROTE",OUT,len(html),"bytes")
print("Portfolio June covers",port_cov,"spend £%.0f"%port_spend,"meta £%.0f goog £%.0f"%(port_meta_sp,port_goog_sp))
print("Meta ads",n_meta_ads,"Google ad groups",n_goog_ads)
for k,disp in VENUES:
    print(k, "cov",data[k]["cov"]["2026-06"],"metaBk",data[k]["mt"]["2026-06"]["bk"],"googBk %.0f"%data[k]["gg"]["2026-06"]["bk"])
