#!/usr/bin/env python3
"""Regenerates index.html (global hub) and each market's landing page from manifest.json.

The site is three live pages, each read from Supabase when it opens:
  Booking pipeline   /pipeline/<market>/      every market
  Covers pace        /<market>-pace-tracker   London, Hong Kong, USA
  Daily bookings     /london/daily/           London
Never hand-edit the index pages; change manifest.json and run this.
"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, "manifest.json")))

CSS = """@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',system-ui,sans-serif;background:#fff;color:#0f172a;padding:40px 16px;max-width:1040px;margin:0 auto}
h1{font-size:26px;font-weight:700}.sub{color:#64748b;margin:6px 0 28px;font-size:14px;line-height:1.5}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
.card{border:1px solid #e2e8f0;border-radius:12px;padding:16px 18px}
.card h2{font-size:16px;font-weight:700;display:flex;justify-content:space-between;align-items:baseline}
.card h2 a{color:inherit;text-decoration:none}.card h2 span{font-size:12px;color:#94a3b8;font-weight:500}
.links{display:flex;flex-direction:column;gap:8px;margin-top:12px}
a.livelink{display:flex;align-items:center;gap:9px;font-size:14px;font-weight:600;color:#2563eb;text-decoration:none;
 border:1px solid #bfdbfe;background:#eff6ff;padding:10px 13px;border-radius:10px}
a.livelink:hover{background:#dbeafe;border-color:#2563eb}
a.livelink .dot{width:7px;height:7px;border-radius:50%;background:#16a34a;flex:none}
a.livelink b{font-weight:600;white-space:nowrap}
a.livelink small{margin-left:auto;font-weight:500;color:#64748b;font-size:12px;text-align:right}
a.back{font-size:12px;color:#2563eb;text-decoration:none}
footer{margin-top:34px;color:#94a3b8;font-size:11px;border-top:1px solid #eef2f6;padding-top:12px;line-height:1.5}"""

FOOT = ("All pages read live data when they open: SevenRooms reservations from Supabase, refreshed through the day, "
        "and ad and website figures written each morning.")


def links(mk):
    return "".join(
        f'<a class="livelink" href="{html.escape(x["href"])}"><span class="dot"></span><b>{html.escape(x["label"])}</b>'
        f'<small>{html.escape(x.get("note", ""))}</small></a>' for x in mk["live"])


def page(title, body):
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>'
            f'<style>{CSS}</style></head><body>{body}<footer>{FOOT}</footer></body></html>\n')


cards = "".join(
    f'<div class="card"><h2><a href="/{mk["slug"]}/">{html.escape(mk["name"])}</a><span>{mk["ccy"]}</span></h2>'
    f'<div class="links">{links(mk)}</div></div>' for mk in M["markets"])
with open(os.path.join(HERE, "index.html"), "w") as f:
    f.write(page("Aqua: Live Reports",
                 '<h1>Aqua: Live Reports</h1><div class="sub">Bookings created and where they are for, covers '
                 'on the books against last year, and yesterday\'s bookings, by market.</div>'
                 f'<div class="grid">{cards}</div>'))

for mk in M["markets"]:
    d = os.path.join(HERE, mk["slug"])
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "index.html"), "w") as f:
        f.write(page(f'Aqua {html.escape(mk["name"])}: Live Reports',
                     f'<a class="back" href="/">← All markets</a><h1 style="margin-top:8px">'
                     f'Aqua {html.escape(mk["name"])}</h1><div class="sub">Live reports, currency {mk["ccy"]}.</div>'
                     f'<div class="links" style="max-width:520px">{links(mk)}</div>'))
print("hub and", len(M["markets"]), "market pages written")
