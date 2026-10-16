#!/usr/bin/env python3
"""Builds the booking pipeline section: one payload and one page per market per ISO week.

Reads pipeline/_sources/sr_raw.py (SevenRooms, from Supabase) and
pipeline/_sources/metrics.json (Meta, Google, GA4, Search Console), writes
pipeline/<slug>/w<monday>_payload.json, the matching page, index.html for the latest week,
pipeline/index.html and pipeline/_weeks.json. Run from the repo root:  python3 _tools/pipeline_build.py
"""
import json, os, sys, datetime as dt, importlib.util
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import pipeline_gen

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "pipeline", "_sources")
spec = importlib.util.spec_from_file_location("sr_raw", os.path.join(SRC, "sr_raw.py"))
sr = importlib.util.module_from_spec(spec); spec.loader.exec_module(sr)
MET = json.load(open(os.path.join(SRC, "metrics.json")))

SNAPSHOT = "16 October 2026"
# ISO week -> Monday of the created week, this year and the 364 day offset last year
WEEKS = {
    "W37": ("2026-09-07", "2025-09-08"),
    "W38": ("2026-09-14", "2025-09-15"),
    "W39": ("2026-09-21", "2025-09-22"),
    "W40": ("2026-09-28", "2025-09-29"),
    "W41": ("2026-10-05", "2025-10-06"),
}
ORDER = ["W37", "W38", "W39", "W40", "W41"]          # oldest first
LATEST = ORDER[-1]
NAV = [["london", "London"], ["hk", "Hong Kong"], ["usa", "USA"], ["dubai", "Dubai"], ["paris", "Paris"]]
CCY = {"london": "£", "hk": "HK$", "usa": "$", "dubai": "AED ", "paris": "€"}
MARKET = {"london": "London", "hk": "Hong Kong", "usa": "USA", "dubai": "Dubai", "paris": "Paris"}
VORDER = {
    "london": ["Aqua Shard", "Hutong", "DSL", "Regent St", "Shiro Sushi", "Azzurra"],
    "hk": ["Aqua HK", "Hutong HK", "The Chinese Library", "Cantina", "Dim Sum Library",
           "Shiro Pacific Place", "Shiro Tai Kwun", "Vesu", "The Canton Library"],
    "usa": ["Aqua NYC", "Hutong NYC", "Hutong Miami"],
    "dubai": ["Hutong Dubai"],
    "paris": ["Aqua Kyoto Paris"],
}
# Channels counted in each venue's total. Ben, 16 Oct 2026: add OpenTable and Resy to the USA
# totals, and OpenTable to DSL, Azzurra, Shiro and Regent St in London. Everything else stays
# website plus Google Reserve.
CH = {
    ("london", "DSL"): ["wg", "ot"], ("london", "Azzurra"): ["wg", "ot"],
    ("london", "Shiro Sushi"): ["wg", "ot"], ("london", "Regent St"): ["wg", "ot"],
    ("usa", "Aqua NYC"): ["wg", "ot", "rs"], ("usa", "Hutong NYC"): ["wg", "ot", "rs"],
    ("usa", "Hutong Miami"): ["wg", "ot", "rs"],
}
CHLABEL = {
    ("wg",): "Website and Google Reserve",
    ("wg", "ot"): "Website, Google Reserve and OpenTable",
    ("wg", "ot", "rs"): "Website, Google Reserve, OpenTable and Resy",
}
NC = {("london", "DSL"), ("hk", "Shiro Tai Kwun"), ("hk", "Vesu"), ("hk", "The Canton Library")}

# Per venue tile notes. A key of None applies to every week; a week key applies to that week only.
NOTES = {
 ("london", "DSL"): {None: {"spend": "brand launched 2026, 2025 is the pre-rebrand site",
                            "brand": "2025 is the pre-rebrand Luci name, not this one"}},
 ("london", "Regent St"): {"W37": {"spend": "Google stepped down mid week, 10 Sep"}},
 ("hk", "Shiro Pacific Place"): {None: {
     "spend": "one account for both Shiro sites, not split",
     "cpa": "not split, shared account",
     "brand": "one Search Console domain for both sites"}},
 ("hk", "Shiro Tai Kwun"): {None: {"spend": "shared with Pacific Place",
                                   "cpa": "shared account", "brand": "shared domain"}},
 ("hk", "Vesu"): {None: {"spend": "reopened Sep 2026, 2025 is a different operating state"}},
 ("hk", "The Canton Library"): {None: {"spend": "Meta only, Google tracking still unverified",
                                       "cpa": "Meta spend only"},
                                "W37": {"brand": "no Search Console data before 20 Sep"},
                                "W38": {"brand": "no Search Console data before 20 Sep"}},
 ("hk", "Hutong HK"): {"W37": {"brand": "2025 carried a 13 to 15 Sep impression spike"},
                       "W38": {"brand": "2025 carried a 13 to 15 Sep impression spike"}},
 ("hk", "Cantina"): {"W38": {"brand": "2026 carried a 15 to 17 Sep impression spike at position 7 to 10"}},
 ("usa", "Hutong Miami"): {None: {"brand": "Search Console property not verified"}},
 ("usa", "Aqua NYC"): {"W39": {"brand": "2026 impressions tripled at a worse position, not name demand"},
                       "W40": {"brand": "2026 impressions tripled at a worse position, not name demand"}},
 ("dubai", "Hutong Dubai"): {"W39": {"spend": "2025 carried a 24 Sep to 2 Oct Meta burst"},
                             "W40": {"spend": "2025 carried a 24 Sep to 2 Oct Meta burst"},
                             "W41": {"spend": "2025 carried the tail of a Meta burst"}},
 ("paris", "Aqua Kyoto Paris"): {"W41": {"sessions": "2025 was the launch burst, 8 to 12 Oct",
                                         "brand": "2025 was the launch burst"}},
}


def D(s):
    return dt.date.fromisoformat(s)


def fmt_range(a, b):
    """5 to 11 October 2026, or 28 September to 4 October 2026."""
    if a.month == b.month:
        return f"{a.day} to {b.day} {b:%B %Y}"
    return f"{a.day} {a:%B} to {b.day} {b:%B %Y}"


def short(a, b):
    if a.month == b.month:
        return f"{a.day} to {b.day} {b:%b}"
    return f"{a.day} {a:%b} to {b.day} {b:%b}"


def window_labels(mon):
    m = D(mon)
    return [f"This week, {short(m, m + dt.timedelta(6))}",
            f"Next week, {short(m + dt.timedelta(7), m + dt.timedelta(13))}",
            f"Beyond, {(m + dt.timedelta(14)).day} {(m + dt.timedelta(14)):%b} onwards"]


def slice_row(row, chans):
    """row = [wg1n,wg1c,wg2n,wg2c,wg3n,wg3c, ot..., rs..., webn, late]"""
    off = {"wg": 0, "ot": 6, "rs": 12}
    out = []
    for i in range(3):
        n = sum(row[off[c] + i * 2] for c in chans)
        cv = sum(row[off[c] + i * 2 + 1] for c in chans)
        out.append((n, cv))
    return out


def notes_for(slug, name, wk):
    tbl = NOTES.get((slug, name), {})
    out = dict(tbl.get(None, {}))
    out.update(tbl.get(wk, {}))
    return out


def build_payload(slug, wk):
    mon_ty, mon_ly = WEEKS[wk]
    labels = window_labels(mon_ty)
    weeks_meta = []
    for k in reversed(ORDER):
        m = D(WEEKS[k][0])
        weeks_meta.append({"key": k, "file": "index.html" if k == LATEST else f"w{WEEKS[k][0]}.html",
                           "label": f"{k} · {short(m, m + dt.timedelta(6))} {m.year}"
                                    + (" (latest)" if k == LATEST else "")})
    venues = []
    for name in VORDER[slug]:
        chans = CH.get((slug, name), ["wg"])
        raw = sr.SR[slug][name]
        ty = raw["ty"].get(wk)
        ly = raw["ly"].get(wk)
        if ty is None:
            continue
        wty = slice_row(ty, chans)
        wly = slice_row(ly, chans) if ly else None
        windows = []
        for i in range(3):
            windows.append({"label": labels[i], "b_ty": wty[i][0], "c_ty": wty[i][1],
                            "b_ly": wly[i][0] if wly else None,
                            "c_ly": wly[i][1] if wly else None})
        total = {"b_ty": sum(x[0] for x in wty), "c_ty": sum(x[1] for x in wty),
                 "b_ly": sum(x[0] for x in wly) if wly else None,
                 "c_ly": sum(x[1] for x in wly) if wly else None}
        for key, idx in (("b_ty", 0), ("c_ty", 1)):
            assert total[key] == sum(x[idx] for x in wty)
        wg_ty = sum(ty[i] for i in (0, 2, 4))
        wg_ly = sum(ly[i] for i in (0, 2, 4)) if ly else None
        m = MET[slug]["venues"][name]
        venues.append({
            "name": name,
            "channels_label": CHLABEL[tuple(chans)],
            "windows": windows, "total": total,
            "wg_bookings": [wg_ty, wg_ly],
            "spend": [m["spend"]["ty"][wk], m["spend"]["ly"][wk]],
            "sessions": [m["sessions"]["ty"][wk], m["sessions"]["ly"][wk]],
            "web_bookings": [ty[18], ly[18] if ly else None],
            "brand": [m["brand"]["ty"][wk], m["brand"]["ly"][wk]],
            "not_comparable": (slug, name) in NC,
            "tile_notes": notes_for(slug, name, wk),
        })
    a, b = D(mon_ty), D(mon_ty) + dt.timedelta(6)
    c, d = D(mon_ly), D(mon_ly) + dt.timedelta(6)
    return {"market": MARKET[slug], "slug": slug, "ccy": CCY[slug],
            "week": {"key": wk, "iso": int(wk[1:]), "ty_label": fmt_range(a, b),
                     "ly_label": fmt_range(c, d), "snapshot": SNAPSHOT},
            "nav": NAV, "weeks": weeks_meta, "venues": venues}


def hub():
    extra = """.row{display:flex;align-items:center;gap:16px;border:1px solid var(--line);border-radius:8px;
 padding:16px 18px;margin:0 0 10px;text-decoration:none;color:var(--ink)}
.row:hover{border-color:var(--blue)}
.nm{font-size:17px;font-weight:650;flex:1 1 auto}
.mt{font-size:12px;color:var(--mute)}
.go{font-size:13px;font-weight:600;color:var(--blue)}"""
    rows = ""
    for slug, nm in NAV:
        n = len(VORDER[slug])
        rows += (f'<a class="row" href="/pipeline/{slug}/"><span class="nm">{nm}</span>'
                 f'<span class="mt">{n} venue{"s" if n > 1 else ""} &middot; {CCY[slug].strip()}</span>'
                 f'<span class="go">Open</span></a>')
    m = D(WEEKS[LATEST][0])
    doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aqua booking pipeline</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{pipeline_gen.CSS}
{extra}</style></head><body><div class="wrap">
<p class="kicker">Booking pipeline &middot; ISO week {LATEST[1:]}</p>
<h1>Bookings created, by the week they are for</h1>
<p class="sub">Latest week created {fmt_range(m, m + dt.timedelta(6))} &middot;
{len(ORDER)} weeks of history in each market &middot; snapshot {SNAPSHOT}</p>
{rows}
<footer>Per venue, bookings and covers created in the week, confirmed reservations, with the
channels counted named on each venue. Last year is the 364 day offset so weekdays match.
<a href="/">Report suite</a></footer>
</div></body></html>'''
    open(os.path.join(HERE, "pipeline", "index.html"), "w").write(doc)
    return len(doc)


def main():
    built = []
    for slug, _ in NAV:
        d = os.path.join(HERE, "pipeline", slug)
        os.makedirs(d, exist_ok=True)
        for wk in ORDER:
            p = build_payload(slug, wk)
            pj = os.path.join(d, f"w{WEEKS[wk][0]}_payload.json")
            json.dump(p, open(pj, "w"), indent=1)
            out = os.path.join(d, "index.html" if wk == LATEST else f"w{WEEKS[wk][0]}.html")
            pipeline_gen.main(pj, out)
            built.append(out)
    json.dump({"snapshot": SNAPSHOT, "latest": LATEST,
               "weeks": [{"key": k, "monday": WEEKS[k][0], "ly_monday": WEEKS[k][1]} for k in ORDER]},
              open(os.path.join(HERE, "pipeline", "_weeks.json"), "w"), indent=1)
    hub()
    print(f"built {len(built)} pages plus hub and _weeks.json")


if __name__ == "__main__":
    main()
