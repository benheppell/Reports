#!/usr/bin/env python3
# Regenerates index.html (global hub) and each market's landing page from manifest.json.
# Weekly + monthly reports are presented as dropdown selectors. Naming is date-consistent across markets.
import json,os
HERE=os.path.dirname(os.path.abspath(__file__))
M=json.load(open(os.path.join(HERE,"manifest.json")))
CSS='''@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',system-ui,sans-serif;background:#fff;color:#0f172a;padding:40px;max-width:920px;margin:0 auto}
h1{font-size:26px;font-weight:700}.sub{color:#64748b;margin:6px 0 24px;font-size:14px}
.tabs{display:flex;gap:6px;border-bottom:1px solid #e2e8f0;margin-bottom:24px;flex-wrap:wrap}
.tab{padding:10px 20px;cursor:pointer;font-weight:600;font-size:14px;color:#64748b;border-bottom:2px solid transparent;margin-bottom:-1px}
.tab.active{color:#0f172a;border-bottom-color:#2563eb}
.market{display:none}.market.active{display:block}
.pick{display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:620px}
.pick .col label{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;font-weight:700;margin-bottom:7px}
select{width:100%;font-family:inherit;font-size:14px;font-weight:500;color:#0f172a;padding:11px 12px;border:1px solid #cbd5e1;border-radius:10px;background:#fff;cursor:pointer}
select:hover{border-color:#2563eb}
.note{font-size:12px;color:#94a3b8;margin-top:16px}
a.back{font-size:12px;color:#2563eb;text-decoration:none}
footer{margin-top:34px;color:#94a3b8;font-size:11px;border-top:1px solid #eef2f6;padding-top:12px}
@media(max-width:560px){.pick{grid-template-columns:1fr}}'''

def selects(mk, prefix):
    wopts='<option value="" selected disabled>Select a week…</option>'
    for w in mk['weekly']:
        wopts+=f'<option value="{prefix}{w["folder"]}/dashboard.html">{w["dates"]} — Dashboard</option>'
        wopts+=f'<option value="{prefix}{w["folder"]}/deep-dive.html">{w["dates"]} — Deep dive</option>'
    mopts='<option value="" selected disabled>Select a month…</option>'
    for m in mk.get('monthly',[]):
        mopts+=f'<option value="{prefix}{m["folder"]}/dashboard.html">{m["label"]} — Dashboard</option>'
    return f'''<div class="pick">
<div class="col"><label>Weekly report</label><select onchange="if(this.value)location.href=this.value">{wopts}</select></div>
<div class="col"><label>Monthly report</label><select onchange="if(this.value)location.href=this.value">{mopts}</select></div>
</div>'''

# ---- global hub ----
tabs=''.join(f'<div class="tab{" active" if i==0 else ""}" onclick="sel({i})">{mk["name"]}</div>' for i,mk in enumerate(M['markets']))
body=''
for i,mk in enumerate(M['markets']):
    body+=f'<div class="market{" active" if i==0 else ""}" id="m{i}">{selects(mk, mk["slug"]+"/")}'
    body+=f'<div class="note">{mk["ccy"]} · weekly bookings vs target with WoW / YoY / YTD; monthly bookings vs target with MoM / YoY.'
    if mk['slug']=='usa': body+=' USA targets are FY26 strategic goals (aggressive); see report footnotes.'
    body+='</div></div>'
g=f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua — Global Performance Reports</title><style>{CSS}</style></head><body>
<h1>Aqua — Global Performance Reports</h1>
<div class="sub">Weekly and monthly GA4 booking performance vs targets. Pick a market, then a report.</div>
<div class="tabs">{tabs}</div>{body}
<footer>Generated {M['generated']}. GA4 bookings = sevenrooms_booking_complete. New reports added automatically each Monday.</footer>
<script>function sel(i){{document.querySelectorAll('.tab').forEach(function(t,j){{t.classList.toggle('active',j==i);}});document.querySelectorAll('.market').forEach(function(m,j){{m.classList.toggle('active',j==i);}});}}</script>
</body></html>'''
open(os.path.join(HERE,"index.html"),"w").write(g)

# ---- per-market landings ----
for mk in M['markets']:
    p=f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua {mk['name']} — Performance Reports</title><style>{CSS}</style></head><body>
<h1>Aqua {mk['name']} — Performance Reports</h1>
<div class="sub">GA4 booking performance vs targets · {mk['ccy']}. Pick a report.</div>
{selects(mk,'')}
<footer>Generated {M['generated']}. GA4 bookings = sevenrooms_booking_complete.</footer></body></html>'''
    open(os.path.join(HERE,mk['slug'],"index.html"),"w").write(p)
print("Rebuilt hub + landings with dropdowns.")
