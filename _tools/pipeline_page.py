#!/usr/bin/env python3
"""Writes the five live booking pipeline pages. Each one fetches
/.netlify/functions/booking-pipeline?m=<slug> and renders in the browser, so the data comes
from Supabase and nothing has to be pushed when the figures change.

Usage: python3 _tools/pipeline_page.py        (from the repo root)
"""
import os, json

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAV = [("london", "London"), ("hk", "Hong Kong"), ("usa", "USA"), ("dubai", "Dubai"), ("paris", "Paris")]
CCY = {"london": "£", "hk": "HK$", "usa": "$", "dubai": "AED ", "paris": "€"}

CSS = """:root{--ink:#111827;--mute:#6b7280;--line:#e5e7eb;--g:#15803d;--r:#b91c1c;--bg:#f9fafb;--blue:#2563eb}
*{box-sizing:border-box}
body{margin:0;padding:30px 20px 48px;background:#fff;color:var(--ink);
 font:15px/1.55 'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto}
.kicker{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin:0 0 6px}
h1{font-size:26px;font-weight:700;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--mute);font-size:13px;margin:0 0 16px}
.bar{display:flex;align-items:flex-end;gap:18px;flex-wrap:wrap;border-bottom:1px solid var(--line);margin:0 0 22px}
.nav{display:flex;gap:6px;flex-wrap:wrap;flex:1 1 auto}
.nav a{font-size:13px;font-weight:600;color:var(--mute);text-decoration:none;padding:9px 14px;
 border-bottom:2px solid transparent;margin-bottom:-1px}
.nav a:hover{color:var(--ink)}
.nav a.on{color:var(--ink);border-bottom-color:var(--blue)}
.wk{display:flex;align-items:center;gap:8px;padding:0 0 8px}
.wk label{font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--mute)}
.wk select{font-family:inherit;font-size:13px;font-weight:600;color:var(--ink);padding:7px 10px;
 border:1px solid #cbd5e1;border-radius:8px;background:#fff;cursor:pointer}
.wk select:hover{border-color:var(--blue)}
.card{border:1px solid var(--line);border-radius:8px;padding:18px 20px;margin:0 0 18px}
.card header{display:flex;flex-wrap:wrap;align-items:center;gap:16px;
 border-bottom:1px solid var(--line);padding-bottom:13px;margin-bottom:14px}
.vn{flex:1 1 180px}
h2{font-size:17px;font-weight:650;margin:0}
.ch{font-size:11px;color:var(--mute);margin:3px 0 0}
.stats{display:flex;gap:22px;flex-wrap:wrap}
.st{display:flex;align-items:baseline;gap:7px}
.big{font:650 23px/1 'SF Mono',Menlo,Consolas,monospace;letter-spacing:-.02em}
.lab{font-size:12px;color:var(--mute)}
.chip{font-size:11.5px;font-weight:600;padding:2px 7px;border-radius:99px;background:var(--bg);white-space:nowrap}
.chip.g{color:var(--g);background:#f0fdf4} .chip.r{color:var(--r);background:#fef2f2} .chip.m{color:var(--mute)}
table.t{width:100%;border-collapse:collapse;margin:0 0 16px}
table.t th{text-align:left;font-weight:500;font-size:13px;padding:7px 8px 7px 0;border-bottom:1px solid var(--line)}
table.t tr:first-child th{font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
 color:var(--mute);border-bottom:none;padding-bottom:2px}
table.t tr.sh th{font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--mute)}
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
.msg{border:1px solid var(--line);border-left:3px solid #d97706;background:#fffbeb;border-radius:0 6px 6px 0;
 padding:14px 16px;font-size:13.5px;line-height:1.6}
footer{margin-top:28px;color:var(--mute);font-size:11px;border-top:1px solid var(--line);padding-top:12px}
footer a{color:var(--blue);text-decoration:none}
@media(max-width:860px){.tiles{grid-template-columns:repeat(2,1fr)}}
@media(max-width:560px){.tiles{grid-template-columns:1fr}body{padding:20px 14px 40px}
 table.t{font-size:12px} .sep{padding-left:8px!important}}"""

JS = r"""
const SLUG = "__SLUG__", MARKET = "__MARKET__", CCY = "__CCY__";
const CHLABEL = {"wg":"Website and Google Reserve",
                 "wg+ot":"Website, Google Reserve and OpenTable",
                 "wg+ot+rs":"Website, Google Reserve, OpenTable and Resy"};
const MONTH = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const SHORT = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const N = n => Number(n).toLocaleString("en-GB");
const D = s => { const [y,m,d] = s.split("-").map(Number); return new Date(Date.UTC(y, m-1, d)); };
const plus = (dt,n) => new Date(dt.getTime() + n*86400000);
const longRange = (a,b) => a.getUTCMonth()===b.getUTCMonth()
  ? `${a.getUTCDate()} to ${b.getUTCDate()} ${MONTH[b.getUTCMonth()]} ${b.getUTCFullYear()}`
  : `${a.getUTCDate()} ${MONTH[a.getUTCMonth()]} to ${b.getUTCDate()} ${MONTH[b.getUTCMonth()]} ${b.getUTCFullYear()}`;
const shortRange = (a,b) => a.getUTCMonth()===b.getUTCMonth()
  ? `${a.getUTCDate()} to ${b.getUTCDate()} ${SHORT[b.getUTCMonth()]}`
  : `${a.getUTCDate()} ${SHORT[a.getUTCMonth()]} to ${b.getUTCDate()} ${SHORT[b.getUTCMonth()]}`;

// Returns [lyText, chgText, cssClass]. Both sides missing gives two empty strings, so the tile
// shows the value alone. Never renders a delta for a venue flagged not comparable.
function delta(ty, ly, o) {
  o = o || {};
  const dp = o.dp === undefined ? 0 : o.dp;
  const fmt = v => v === null || v === undefined ? "n/a"
    : o.money ? CCY + Number(v).toLocaleString("en-GB",{minimumFractionDigits:dp,maximumFractionDigits:dp})
    : o.pp ? Number(v).toFixed(2) + "%" : N(v);
  if ((ty === null || ty === undefined) && (ly === null || ly === undefined)) return ["","","m"];
  if (ly === null || ly === undefined) return ["n/c","n/c","m"];
  if (o.nc) return [fmt(ly),"n/c","m"];
  if (ty === null || ty === undefined) return [fmt(ly),"n/a","m"];
  if (Number(ly) === 0) return [fmt(ly), Number(ty) > 0 ? "new" : "", Number(ty) > 0 ? "g" : "m"];
  const x = Number(ty) - Number(ly);
  const good = o.inv ? x < 0 : x > 0;
  let s;
  if (o.pp) s = (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(2) + "pp";
  else if (o.money) s = (x >= 0 ? "+" : "−") + CCY + Math.abs(x).toLocaleString("en-GB",{minimumFractionDigits:dp,maximumFractionDigits:dp});
  else s = (x >= 0 ? "+" : "−") + N(Math.abs(x));
  return [fmt(ly), s, x === 0 ? "m" : (good ? "g" : "r")];
}

function tile(label, value, ly, chg, cls, sub) {
  const foot = (ly || chg)
    ? `<p class="tf"><span class="ly">${esc(ly)}</span> <span class="chip ${cls}">${chg}</span></p>` : "";
  return `<div class="tile"><p class="tl">${esc(label)}</p><p class="tv">${value}</p>${foot}`
    + (sub ? `<p class="iso">${esc(sub)}</p>` : "") + `</div>`;
}

// Brand Demand Index isolation: each venue against the median of the OTHER venues.
function brandLabels(rows) {
  const ok = rows.filter(r => !r.not_comparable && r.brand_ty !== null && r.brand_ly);
  if (ok.length < 3) return {};
  const chg = {};
  ok.forEach(r => { chg[r.venue] = (r.brand_ty - r.brand_ly) / r.brand_ly * 100; });
  const med = a => { const s = a.slice().sort((x,y)=>x-y), h = s.length>>1;
    return s.length % 2 ? s[h] : (s[h-1]+s[h])/2; };
  const out = {};
  Object.keys(chg).forEach(name => {
    const others = Object.keys(chg).filter(n => n !== name).map(n => chg[n]);
    const iso = chg[name] - med(others);
    out[name] = Math.abs(iso) < 5 ? "in line with the estate"
      : `${Math.abs(iso).toFixed(0)}pp ${iso > 0 ? "better" : "worse"} than the estate`;
  });
  return out;
}

function card(r, labels) {
  const nc = !!r.not_comparable, nt = r.notes || {};
  const mon = D(r.monday);
  const wins = [
    ["This week, " + shortRange(mon, plus(mon,6)), r.b1_ty, r.b1_ly, r.c1_ty, r.c1_ly],
    ["Next week, " + shortRange(plus(mon,7), plus(mon,13)), r.b2_ty, r.b2_ly, r.c2_ty, r.c2_ly],
    ["Beyond, " + plus(mon,14).getUTCDate() + " " + SHORT[plus(mon,14).getUTCMonth()] + " onwards",
      r.b3_ty, r.b3_ly, r.c3_ty, r.c3_ly]];
  const sum = (...v) => v.every(x => x === null || x === undefined) ? null
    : v.reduce((a,b) => a + (b || 0), 0);
  const anyNull = v => v.some(x => x === null || x === undefined);
  const tB_ty = sum(r.b1_ty, r.b2_ty, r.b3_ty), tC_ty = sum(r.c1_ty, r.c2_ty, r.c3_ty);
  const tB_ly = anyNull([r.b1_ly,r.b2_ly,r.b3_ly]) ? null : r.b1_ly + r.b2_ly + r.b3_ly;
  const tC_ly = anyNull([r.c1_ly,r.c2_ly,r.c3_ly]) ? null : r.c1_ly + r.c2_ly + r.c3_ly;
  wins.push(["Total created", tB_ty, tB_ly, tC_ty, tC_ly]);

  let rows = "";
  wins.forEach((w, i) => {
    const [bl, bc, bk] = delta(w[1], w[2], {nc});
    const [cl, cc, ck] = delta(w[3], w[4], {nc});
    rows += `<tr${i===3 ? ' class="tot"' : ''}><th>${esc(w[0])}</th>`
      + `<td class="n">${N(w[1])}</td><td class="n ly">${bl}</td><td class="n ${bk}">${bc}</td>`
      + `<td class="n sep">${N(w[3])}</td><td class="n ly">${cl}</td><td class="n ${ck}">${cc}</td></tr>`;
  });

  const [, hb, kb] = delta(tB_ty, tB_ly, {nc});
  const [, hc, kc] = delta(tC_ty, tC_ly, {nc});

  const cpa_ty = r.spend_ty !== null && r.wgb_ty ? r.spend_ty / r.wgb_ty : null;
  const cpa_ly = r.spend_ly !== null && r.wgb_ly ? r.spend_ly / r.wgb_ly : null;
  const cv_ty = r.web_ty !== null && r.sess_ty ? 100 * r.web_ty / r.sess_ty : null;
  const cv_ly = r.web_ly !== null && r.sess_ly ? 100 * r.web_ly / r.sess_ly : null;
  const money = v => v === null ? "n/a"
    : CCY + Number(v).toLocaleString("en-GB",{minimumFractionDigits:0,maximumFractionDigits:0});
  const money2 = v => v === null ? "n/a"
    : CCY + Number(v).toLocaleString("en-GB",{minimumFractionDigits:2,maximumFractionDigits:2});

  let tiles = "";
  let d = delta(r.spend_ty, r.spend_ly, {inv:true, money:true, nc, dp:0});
  tiles += tile("Digital spend", money(r.spend_ty), d[0], d[1], d[2], nt.spend);
  d = delta(cpa_ty, cpa_ly, {inv:true, money:true, nc, dp:2});
  tiles += tile("Blended CPA", money2(cpa_ty), d[0], d[1], d[2], nt.cpa);
  d = delta(r.sess_ty, r.sess_ly, {nc});
  tiles += tile("Sessions", r.sess_ty === null ? "n/a" : N(r.sess_ty), d[0], d[1], d[2], nt.sessions);
  d = delta(cv_ty, cv_ly, {pp:true, nc});
  tiles += tile("Website conv rate", cv_ty === null ? "n/a" : cv_ty.toFixed(2) + "%", d[0], d[1], d[2], nt.conv);
  d = delta(r.brand_ty, r.brand_ly, {nc});
  tiles += tile("Brand searches", r.brand_ty === null ? "n/a" : N(r.brand_ty), d[0], d[1], d[2],
                nt.brand || labels[r.venue]);

  return `<section class="card"><header><div class="vn"><h2>${esc(r.venue)}</h2>`
    + `<p class="ch">${esc(CHLABEL[r.channels] || r.channels)}</p></div><div class="stats">`
    + `<div class="st"><span class="big">${N(tB_ty)}</span><span class="lab">bookings</span><span class="chip ${kb}">${hb}</span></div>`
    + `<div class="st"><span class="big">${N(tC_ty)}</span><span class="lab">covers</span><span class="chip ${kc}">${hc}</span></div>`
    + `</div></header><table class="t">`
    + `<tr><th></th><th class="n" colspan="3">Bookings</th><th class="n sep" colspan="3">Covers</th></tr>`
    + `<tr class="sh"><th>By the week they are for</th>`
    + `<th class="n">2026</th><th class="n">2025</th><th class="n">Chg</th>`
    + `<th class="n sep">2026</th><th class="n">2025</th><th class="n">Chg</th></tr>`
    + rows + `</table><div class="tiles">${tiles}</div></section>`;
}

let PAYLOAD = null;

function render(weekKey) {
  const wk = PAYLOAD.weeks.find(w => w.key === weekKey) || PAYLOAD.weeks[0];
  const rows = PAYLOAD.rows.filter(r => r.week_key === wk.key)
                           .sort((a,b) => a.venue_order - b.venue_order);
  const mon = D(wk.monday), lymon = D(wk.ly_monday);
  document.getElementById("kicker").textContent = "Booking pipeline · ISO week " + wk.key.slice(1);
  const asof = PAYLOAD.updated
    ? new Date(PAYLOAD.updated).toLocaleDateString("en-GB", {day:"numeric", month:"long", year:"numeric"})
    : "unknown";
  document.getElementById("sub").textContent =
    "Created " + longRange(mon, plus(mon,6)) + " against " + longRange(lymon, plus(lymon,6))
    + " · data as at " + asof;
  const sel = document.getElementById("wsel");
  sel.innerHTML = PAYLOAD.weeks.map((w, i) => {
    const m = D(w.monday);
    return `<option value="${w.key}"${w.key===wk.key?" selected":""}>${w.key} · `
      + `${shortRange(m, plus(m,6))} ${m.getUTCFullYear()}${i===0?" (latest)":""}</option>`;
  }).join("");
  const labels = brandLabels(rows);
  document.getElementById("cards").innerHTML = rows.length
    ? rows.map(r => card(r, labels)).join("")
    : `<div class="msg">No venues for ${esc(wk.key)}.</div>`;
}

async function boot() {
  const cards = document.getElementById("cards");
  try {
    const res = await fetch("/.netlify/functions/booking-pipeline?m=" + SLUG, {cache: "no-store"});
    const p = await res.json();
    if (!res.ok || p.error) throw new Error(p.error || ("HTTP " + res.status));
    if (!p.rows.length) {
      cards.innerHTML = `<div class="msg"><strong>No data yet.</strong> The morning run has not written
        ${esc(MARKET)} figures to the database. Nothing is wrong with the page.</div>`;
      document.getElementById("sub").textContent = "Waiting for the first data load";
      return;
    }
    PAYLOAD = p;
    render(p.weeks[0].key);
    document.getElementById("wsel").addEventListener("change", e => render(e.target.value));
  } catch (e) {
    cards.innerHTML = `<div class="msg"><strong>Could not load the figures.</strong> `
      + esc(String(e.message || e)) + `</div>`;
    document.getElementById("sub").textContent = "Data unavailable";
  }
}
boot();
"""


HUB_EXTRA = """.row{display:flex;align-items:center;gap:16px;border:1px solid var(--line);border-radius:8px;
 padding:16px 18px;margin:0 0 10px;text-decoration:none;color:var(--ink)}
.row:hover{border-color:var(--blue)}
.nm{font-size:17px;font-weight:650;flex:1 1 auto}
.go{font-size:13px;font-weight:600;color:var(--blue)}"""


def hub():
    rows = "".join(
        f'<a class="row" href="/pipeline/{s}/"><span class="nm">{n}</span>'
        f'<span class="go">Open</span></a>' for s, n in NAV)
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua booking pipeline</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}
{HUB_EXTRA}</style></head><body><div class="wrap">
<p class="kicker">Booking pipeline</p>
<h1>Bookings created, by the week they are for</h1>
<p class="sub">Per venue, bookings and covers created in a week, split by the week they are for,
against the 364 day offset week last year. Five weeks of history in each market, refreshed every
morning. Pick a market, then a week.</p>
{rows}
<footer>Confirmed reservations. The channels counted are named on each venue. Bookings for a date
before the created week are left out and counted as late records.
<a href="/">Report suite</a></footer>
</div></body></html>'''


def page(slug, market):
    nav = "".join(
        '<a href="/pipeline/%s/"%s>%s</a>' % (s, ' class="on"' if s == slug else "", n)
        for s, n in NAV)
    js = JS.replace("__SLUG__", slug).replace("__MARKET__", market).replace("__CCY__", CCY[slug])
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua {market} booking pipeline</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap">
<p class="kicker" id="kicker">Booking pipeline</p>
<h1>{market}</h1>
<p class="sub" id="sub">Loading</p>
<div class="bar"><nav class="nav">{nav}</nav>
<div class="wk"><label for="wsel">Week</label><select id="wsel"></select></div></div>
<div id="cards"><div class="msg">Loading the figures.</div></div>
<footer>Bookings created, confirmed reservations, counted by the date the booking was made. Each
venue&rsquo;s channels are named under its name. Last year is the 364 day offset so weekdays match.
Bookings for a date before the created week are left out and counted as late records. This page
reads the database directly, so it is current as at the morning run.
<a href="/pipeline/">All markets</a> &middot; <a href="/{slug}/">{market} report suite</a></footer>
</div>
<script>{js}</script></body></html>'''


def main():
    for slug, market in NAV:
        d = os.path.join(HERE, "pipeline", slug)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w") as f:
            f.write(page(slug, market))
        print("wrote", f"pipeline/{slug}/index.html")
    with open(os.path.join(HERE, "pipeline", "index.html"), "w") as f:
        f.write(hub())
    print("wrote pipeline/index.html")


if __name__ == "__main__":
    main()
