#!/usr/bin/env python3
"""Booking pipeline report: bookings and covers created in a week, by the week they are for.
Usage: pipeline_gen.py <payload.json> <out.html>
Payload keys: market, slug, ccy, week{iso,ty_label,ly_label,snapshot}, nav[[slug,name]],
venues[{name, windows[{label,b_ty,b_ly,c_ty,c_ly}], total{...}, spend[ty,ly], sessions[ty,ly],
web_bookings[ty,ly], brand[ty,ly], not_comparable, tile_notes{}}]
"""
import json, sys, html, statistics as st

CSS = """:root{--ink:#111827;--mute:#6b7280;--line:#e5e7eb;--g:#15803d;--r:#b91c1c;--bg:#f9fafb;--blue:#2563eb}
*{box-sizing:border-box}
body{margin:0;padding:30px 20px 48px;background:#fff;color:var(--ink);
 font:15px/1.55 'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto}
.kicker{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin:0 0 6px}
h1{font-size:26px;font-weight:700;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--mute);font-size:13px;margin:0 0 16px}
.nav{display:flex;gap:6px;flex-wrap:wrap;border-bottom:1px solid var(--line);margin:0 0 22px}
.nav a{font-size:13px;font-weight:600;color:var(--mute);text-decoration:none;padding:9px 14px;
 border-bottom:2px solid transparent;margin-bottom:-1px}
.nav a:hover{color:var(--ink)}
.nav a.on{color:var(--ink);border-bottom-color:var(--blue)}
.card{border:1px solid var(--line);border-radius:8px;padding:18px 20px;margin:0 0 18px}
.card header{display:flex;flex-wrap:wrap;align-items:center;gap:16px;
 border-bottom:1px solid var(--line);padding-bottom:13px;margin-bottom:14px}
h2{font-size:17px;font-weight:650;margin:0;flex:1 1 180px}
.stats{display:flex;gap:22px;flex-wrap:wrap}
.st{display:flex;align-items:baseline;gap:7px}
.big{font:650 23px/1 'SF Mono',Menlo,Consolas,monospace;letter-spacing:-.02em}
.lab{font-size:12px;color:var(--mute)}
.chip{font-size:11.5px;font-weight:600;padding:2px 7px;border-radius:99px;background:var(--bg);white-space:nowrap}
.chip.g{color:var(--g);background:#f0fdf4} .chip.r{color:var(--r);background:#fef2f2} .chip.m{color:var(--mute)}
table.wk{width:100%;border-collapse:collapse;margin:0 0 16px}
table.wk th{text-align:left;font-weight:500;font-size:13px;padding:7px 8px 7px 0;border-bottom:1px solid var(--line)}
table.wk tr:first-child th{font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
 color:var(--mute);border-bottom:none;padding-bottom:2px}
table.wk tr.sh th{font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--mute)}
td{padding:7px 0 7px 8px;border-bottom:1px solid var(--line);font-size:13.5px}
.n{text-align:right;font-family:'SF Mono',Menlo,Consolas,monospace;font-variant-numeric:tabular-nums}
th.n{font-family:inherit}
.sep{border-left:1px solid var(--line);padding-left:14px!important}
.ly{color:var(--mute)} .m{color:var(--mute)} .g{color:var(--g)} .r{color:var(--r)}
tr.tot th,tr.tot td{font-weight:650;background:var(--bg);border-bottom:none}
.tiles{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.tile{background:var(--bg);border-radius:6px;padding:10px 12px}
.tl{font-size:10.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--mute);margin:0 0 5px;line-height:1.3}
.tv{font:650 18px/1 'SF Mono',Menlo,Consolas,monospace;margin:0 0 5px}
.tf{margin:0;font-size:11.5px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.iso{margin:5px 0 0;font-size:10.5px;line-height:1.35;color:var(--mute)}
footer{margin-top:28px;color:var(--mute);font-size:11px;border-top:1px solid var(--line);padding-top:12px}
footer a{color:var(--blue);text-decoration:none}
@media(max-width:860px){.tiles{grid-template-columns:repeat(2,1fr)}}
@media(max-width:560px){.tiles{grid-template-columns:1fr}body{padding:20px 14px 40px}
 table.wk{font-size:12px} .sep{padding-left:8px!important}}"""


def N(n):
    return f"{n:,}"


def delta(ty, ly, inv=False, money=None, pp=False, nc=False, dp=0):
    """Returns (ly_text, chg_text, class). Both sides missing gives two empty strings."""
    if ty is None and ly is None:
        return ("", "", "m")
    def fmt(v):
        if v is None:
            return "n/a"
        if money:
            return f"{money}{v:,.{dp}f}"
        if pp:
            return f"{v:.2f}%"
        return N(v)
    if ly is None:
        return ("n/c", "n/c", "m")
    if nc:
        return (fmt(ly), "n/c", "m")
    if ly == 0:
        return (fmt(ly), "new", "g" if (ty or 0) > 0 else "m")
    x = ty - ly
    good = (x < 0) if inv else (x > 0)
    if pp:
        s = f"{x:+.2f}pp"
    elif money:
        s = ("+" if x > 0 else "&minus;") + f"{money}{abs(x):,.{dp}f}"
    else:
        s = ("+" if x > 0 else "&minus;") + N(abs(x))
    return (fmt(ly), s, "m" if x == 0 else ("g" if good else "r"))


def tile(label, value, ly_text, chg, cls, sub=""):
    sub = f'<p class="iso">{sub}</p>' if sub else ""
    foot = ""
    if ly_text or chg:
        foot = (f'<p class="tf"><span class="ly">{ly_text}</span> '
                f'<span class="chip {cls}">{chg}</span></p>')
    return (f'<div class="tile"><p class="tl">{label}</p><p class="tv">{value}</p>'
            f'{foot}{sub}</div>')


def brand_labels(venues):
    """Brand Demand Index isolation: each venue against the median of the OTHER venues."""
    ok = [v for v in venues
          if not v.get("not_comparable") and v["brand"][0] is not None and v["brand"][1]]
    if len(ok) < 3:
        return {}
    chg = {v["name"]: (v["brand"][0] - v["brand"][1]) / v["brand"][1] * 100 for v in ok}
    out = {}
    for name in chg:
        others = [c for n, c in chg.items() if n != name]
        iso = chg[name] - st.median(others)
        out[name] = ("in line with the estate" if abs(iso) < 5
                     else f'{abs(iso):.0f}pp {"better" if iso > 0 else "worse"} than the estate')
    return out


def venue_card(v, ccy, iso_labels):
    nc = bool(v.get("not_comparable"))
    tn = v.get("tile_notes", {})
    rows = ""
    for w in list(v["windows"]) + [dict(v["total"], label="Total created")]:
        bly, bchg, bcls = delta(w["b_ty"], w["b_ly"], nc=nc)
        cly, cchg, ccls = delta(w["c_ty"], w["c_ly"], nc=nc)
        cls = ' class="tot"' if w["label"] == "Total created" else ""
        rows += (f'<tr{cls}><th>{html.escape(w["label"])}</th>'
                 f'<td class="n">{N(w["b_ty"])}</td><td class="n ly">{bly}</td><td class="n {bcls}">{bchg}</td>'
                 f'<td class="n sep">{N(w["c_ty"])}</td><td class="n ly">{cly}</td><td class="n {ccls}">{cchg}</td></tr>')

    t = v["total"]
    _, hb, kb = delta(t["b_ty"], t["b_ly"], nc=nc)
    _, hc, kc = delta(t["c_ty"], t["c_ly"], nc=nc)

    sp_ty, sp_ly = v["spend"]
    cpa_ty = sp_ty / t["b_ty"] if sp_ty is not None and t["b_ty"] else None
    cpa_ly = sp_ly / t["b_ly"] if sp_ly is not None and t.get("b_ly") else None
    se_ty, se_ly = v["sessions"]
    wb_ty, wb_ly = v["web_bookings"]
    cv_ty = 100 * wb_ty / se_ty if wb_ty is not None and se_ty else None
    cv_ly = 100 * wb_ly / se_ly if wb_ly is not None and se_ly else None
    br_ty, br_ly = v["brand"]

    tiles = ""
    ly, chg, cls = delta(sp_ty, sp_ly, inv=True, money=ccy, nc=nc, dp=0)
    tiles += tile("Digital spend", f"{ccy}{sp_ty:,.0f}" if sp_ty is not None else "n/a", ly, chg, cls, tn.get("spend", ""))
    ly, chg, cls = delta(cpa_ty, cpa_ly, inv=True, money=ccy, nc=nc, dp=2)
    tiles += tile("Blended CPA", f"{ccy}{cpa_ty:,.2f}" if cpa_ty is not None else "n/a", ly, chg, cls, tn.get("cpa", ""))
    ly, chg, cls = delta(se_ty, se_ly, nc=nc)
    tiles += tile("Sessions", N(se_ty) if se_ty is not None else "n/a", ly, chg, cls, tn.get("sessions", ""))
    ly, chg, cls = delta(cv_ty, cv_ly, pp=True, nc=nc)
    tiles += tile("Website conv rate", f"{cv_ty:.2f}%" if cv_ty is not None else "n/a", ly, chg, cls, tn.get("conv", ""))
    ly, chg, cls = delta(br_ty, br_ly, nc=nc)
    sub = tn.get("brand", "") or iso_labels.get(v["name"], "")
    tiles += tile("Brand searches", N(br_ty) if br_ty is not None else "n/a", ly, chg, cls, sub)

    return f'''<section class="card">
<header><h2>{html.escape(v["name"])}</h2>
<div class="stats">
<div class="st"><span class="big">{N(t["b_ty"])}</span><span class="lab">bookings</span><span class="chip {kb}">{hb}</span></div>
<div class="st"><span class="big">{N(t["c_ty"])}</span><span class="lab">covers</span><span class="chip {kc}">{hc}</span></div>
</div></header>
<table class="wk">
<tr><th></th><th class="n" colspan="3">Bookings</th><th class="n sep" colspan="3">Covers</th></tr>
<tr class="sh"><th>By the week they are for</th>
<th class="n">2026</th><th class="n">2025</th><th class="n">Chg</th>
<th class="n sep">2026</th><th class="n">2025</th><th class="n">Chg</th></tr>
{rows}</table>
<div class="tiles">{tiles}</div>
</section>'''


def main(payload_path, out_path):
    p = json.load(open(payload_path))
    w = p["week"]
    iso_labels = brand_labels(p["venues"])
    cards = "".join(venue_card(v, p["ccy"], iso_labels) for v in p["venues"])
    parts = []
    for s, n in p["nav"]:
        on = ' class="on"' if s == p["slug"] else ''
        parts.append('<a href="/pipeline/%s/"%s>%s</a>' % (s, on, html.escape(n)))
    nav = "".join(parts)
    doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua {html.escape(p["market"])} booking pipeline</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap">
<p class="kicker">Booking pipeline &middot; ISO week {w["iso"]}</p>
<h1>{html.escape(p["market"])}</h1>
<p class="sub">Created {w["ty_label"]} against {w["ly_label"]} &middot; snapshot {w["snapshot"]}</p>
<nav class="nav">{nav}</nav>
{cards}
<footer>Bookings created, website and Google Reserve, confirmed reservations. Last year is the 364 day offset so
weekdays match. Generated {w["snapshot"]}. <a href="/pipeline/">All markets</a> &middot;
<a href="/{p["slug"]}/">{html.escape(p["market"])} report suite</a></footer>
</div></body></html>'''
    open(out_path, "w").write(doc)
    print(f"wrote {out_path} ({len(doc)} bytes, {len(p['venues'])} venues)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
