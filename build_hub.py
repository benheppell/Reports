#!/usr/bin/env python3
# Regenerates index.html (global hub) and each market's landing page from manifest.json.
import json,os
HERE=os.path.dirname(os.path.abspath(__file__))
M=json.load(open(os.path.join(HERE,"manifest.json")))
CSS='''@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',system-ui,sans-serif;background:#fff;color:#0f172a;padding:40px;max-width:920px;margin:0 auto}
h1{font-size:26px;font-weight:700}.sub{color:#64748b;margin:6px 0 24px;font-size:14px}
.tabs{display:flex;gap:6px;border-bottom:1px solid #e2e8f0;margin-bottom:22px;flex-wrap:wrap}
.tab{padding:10px 20px;cursor:pointer;font-weight:600;font-size:14px;color:#64748b;border-bottom:2px solid transparent;margin-bottom:-1px}
.tab.active{color:#0f172a;border-bottom-color:#2563eb}
.market{display:none}.market.active{display:block}
.grp{font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:#94a3b8;font-weight:700;margin:18px 0 10px}
.item{border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.item .t{font-weight:600;font-size:14px}.item .d{color:#64748b;font-size:12px;margin-top:2px}
.links{display:flex;gap:8px;flex-wrap:wrap}
a.btn{font-size:12.5px;font-weight:600;text-decoration:none;color:#2563eb;border:1px solid #dbeafe;background:#f0f6ff;padding:6px 12px;border-radius:8px}
a.btn:hover{background:#dbeafe}
a.back{font-size:12px;color:#2563eb;text-decoration:none}
.note{font-size:12px;color:#94a3b8;margin-top:6px}
footer{margin-top:34px;color:#94a3b8;font-size:11px;border-top:1px solid #eef2f6;padding-top:12px}'''

def lists(mk, prefix):
    # prefix='' for market landing (links relative to market root), '{slug}/' for global hub
    h=''
    if mk['weekly']:
        h+='<div class="grp">Weekly</div>'
        for w in mk['weekly']:
            h+=f'''<div class="item"><div><div class="t">{w['label']}</div><div class="d">{w['dates']} · {mk['ccy']}</div></div>
<div class="links"><a class="btn" href="{prefix}{w['folder']}/dashboard.html">Dashboard</a><a class="btn" href="{prefix}{w['folder']}/deep-dive.html">Deep dive</a></div></div>'''
    if mk.get('monthly'):
        h+='<div class="grp">Monthly</div>'
        for m in mk['monthly']:
            h+=f'''<div class="item"><div><div class="t">{m['label']}</div><div class="d">Monthly performance · {mk['ccy']}</div></div>
<div class="links"><a class="btn" href="{prefix}{m['folder']}/dashboard.html">Dashboard</a></div></div>'''
    return h

# ---- global hub ----
tabs=''.join(f'<div class="tab{" active" if i==0 else ""}" onclick="sel({i})">{mk["name"]}</div>' for i,mk in enumerate(M['markets']))
body=''
for i,mk in enumerate(M['markets']):
    body+=f'<div class="market{" active" if i==0 else ""}" id="m{i}">{lists(mk, mk["slug"]+"/")}'
    if mk['slug']=='usa': body+='<div class="note">USA targets are FY26 strategic goals (aggressive); see report footnotes.</div>'
    body+='</div>'
g=f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua — Global Performance Reports</title><style>{CSS}</style></head><body>
<h1>Aqua — Global Performance Reports</h1>
<div class="sub">Weekly and monthly GA4 booking performance vs targets, by market.</div>
<div class="tabs">{tabs}</div>{body}
<footer>Generated {M['generated']}. GA4 bookings = sevenrooms_booking_complete. New weeks added automatically each Monday.</footer>
<script>function sel(i){{document.querySelectorAll('.tab').forEach(function(t,j){{t.classList.toggle('active',j==i);}});document.querySelectorAll('.market').forEach(function(m,j){{m.classList.toggle('active',j==i);}});}}</script>
</body></html>'''
open(os.path.join(HERE,"index.html"),"w").write(g)

# ---- per-market landings ----
for mk in M['markets']:
    p=f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua {mk['name']} — Performance Reports</title><style>{CSS}</style></head><body>
<h1>Aqua {mk['name']} — Performance Reports</h1>
<div class="sub">GA4 booking performance vs targets · {mk['ccy']}</div>
{lists(mk,'')}
<footer>Generated {M['generated']}. GA4 bookings = sevenrooms_booking_complete.</footer></body></html>'''
    open(os.path.join(HERE,mk['slug'],"index.html"),"w").write(p)
print("Built global hub + landings for:", ", ".join(mk['name'] for mk in M['markets']))
