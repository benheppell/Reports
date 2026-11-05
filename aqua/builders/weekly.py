"""Weekly payload builders. Each returns a dict with exactly the keys its _tools generator reads,
so the existing page templates render the new payloads unchanged.

Commentary is written by rules from the figures, never by hand: what moved, by how much, and
which venues' GA4 counts are floors. Free text from overrides.toml is placed first.
"""
from __future__ import annotations

from ..dates import EN_DASH, fy_label, long_date, range_label
from .common import (Ctx, direction, fmt_int, fmt_pct, md, no_dashes, num, pct, words)

PAID_CHANNELS = ("Paid Search", "Paid Social")


# ============================================================================ shared pieces
def page_dates(c: Ctx) -> dict:
    return {"week": c.w.label(), "wow": c.w.prior.label(), "yoy": c.w.yoy.label(),
            "generated": long_date(c.generated)}


def capture(c: Ctx) -> dict[str, dict]:
    """GA4 create-path bookings / SevenRooms gross website rows, against each venue's baseline."""
    rows = c.f.get("web_rows") or {}
    base = c.ov.get("capture_baseline", {}).get(c.m["slug"], {})
    out = {}
    for v in c.venues:
        n = v["name"]
        sr = (rows.get(n) or {}).get(c.w.folder)
        g = c.ga4(n, c.w)
        if not sr or g is None:
            continue
        b = base.get(n, base.get("default"))
        r = g / sr
        status = "green"
        if b:
            rel = r / b
            status = "red" if rel < 0.8 else "amber" if rel < 0.9 else "green"
        out[n] = {"ratio": r, "baseline": b, "status": status, "ga4": g, "sr": sr}
    return out


def capture_sentence(c: Ctx, cap: dict) -> str:
    bad = [(n, x) for n, x in cap.items() if x["status"] != "green"]
    if not cap:
        return ""
    if not bad:
        return ("GA4 collection is sound at every venue: create-path bookings track SevenRooms website "
                "bookings within 10 per cent of each venue's normal ratio.")
    names = ", ".join(f"{n} {x['ratio']:.2f} (normal {x['baseline']:.2f})" for n, x in bad)
    return (f"<b>{len(bad)} of {len(cap)} venues are under recording, so their GA4 figures are floors, not "
            f"readings</b>: {names}. The test is GA4 create-path bookings divided by SevenRooms website "
            f"booking rows for the same days, which nothing on our own site can affect.")


def sum_opt(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) if xs else None


# ============================================================================ dashboard
def dashboard(c: Ctx) -> dict:
    w = c.w
    rows, outside = [], []
    for v in c.venues:
        n = v["name"]
        shared_copy = c.is_shared(n)
        r = {"name": n, "act": num(c.ga4(n, w)), "tgt": None if v.get("tgt_label") else c.tgt(n),
             "wow": num(c.ga4(n, w.prior)), "yoy": num(c.ga4(n, w.yoy)), "ytd": num(c.vf(n).get("ytd_book")),
             "ytdt": None if v.get("tgt_label") else c.ytd_tgt(n),
             "meta_s": 0 if shared_copy else num(c.spend(n, "meta", w), 2),
             "goog_s": 0 if shared_copy else num(c.spend(n, "google", w), 2),
             "nc": bool(v.get("not_comparable"))}
        if v.get("shared_ads"):
            r["shared_ads"] = True
        if v.get("tgt_label"):
            r["tgt_label"] = v["tgt_label"]
        if v.get("no_ly"):
            r["noyoy"] = True
        if v.get("pill"):
            r["pill"] = v["pill"]
        cpb = cpb_spend(c, n)
        if cpb is not None:
            r["cpb_spend"] = num(cpb, 2)
        (outside if v.get("outside") else rows).append(r)

    p = {"market": c.m["name"], "ccy": c.m["ccy"], "sym": c.m["sym"],
         "ytd_label": "FY from Feb" if c.m["fy_start_month"] == 2 else "calendar year from Jan",
         "venues": rows, **page_dates(c)}
    groups = []
    for g in c.m.get("group", []):
        owner = c.f.get("shared_owner", {}).get(c.venue(g["members"][0]).get("shared_ads"), g["members"][0])
        groups.append({"name": g["name"], "label": g["label"], "members": g["members"],
                       "tgt": c.tgt(g["target_key"]), "ytdt": c.ytd_tgt(g["target_key"]),
                       "meta_s": num(c.spend(owner, "meta", w), 2), "goog_s": num(c.spend(owner, "google", w), 2)})
    if groups:
        p["groups"] = groups
    if outside:
        p["outside"] = outside
        p["outside_label"] = c.m.get("outside_label", "Outside the portfolio: not in any total")
    p["note"] = dashboard_note(c, rows, groups)
    p["foot_extra"] = foot_extra(c)
    return p


def cpb_spend(c: Ctx, n: str):
    """Spend used for cost per booking when it differs from total spend: awareness campaigns and
    unverified Google accounts are left out."""
    v = c.venue(n)
    if not (v.get("meta_campaigns") or v.get("meta_objective") or v.get("google_excluded")):
        return None
    m = c.meta(n, c.w)
    g = 0 if v.get("google_excluded") else (c.spend(n, "google", c.w) or 0)
    return (m["cpb_spend"] if m else 0) + g


def dashboard_note(c: Ctx, rows, groups) -> str:
    w = c.w
    act = sum_opt(r["act"] for r in rows)
    prior = sum_opt(r["wow"] for r in rows)
    yoy = sum_opt(r["yoy"] for r in rows)
    parts = c.week_notes()
    head = (f"{c.m['name']} recorded <b>{fmt_int(act)}</b> create-path GA4 bookings, "
            f"<b>{words(pct(act, prior))}</b> week on week and <b>{words(pct(act, yoy))}</b> year on year.")
    nc = [r for r in rows if r["nc"]]
    if nc and yoy:
        ex_a = sum_opt(r["act"] for r in rows if not r["nc"])
        ex_y = sum_opt(r["yoy"] for r in rows if not r["nc"])
        head += f" Excluding {', '.join(r['name'] for r in nc)}, which is not comparable, the year-on-year figure is <b>{words(pct(ex_a, ex_y))}</b>."
    parts.append(head)
    if c.m.get("targets_mode") == "target":
        tgts = [r["tgt"] for r in rows if r["tgt"] is not None] + [g["tgt"] for g in groups if g["tgt"] is not None]
        if tgts:
            t = sum(tgts)
            parts.append(f"Against a weekly target of <b>{fmt_int(t)}</b> that is <b>{fmt_pct(pct(act, t))}</b>. "
                         + _target_basis(c))
        else:
            parts.append("No targets are loaded for this week, so the target columns read as a dash.")
    elif c.m.get("targets_mode") == "reference":
        parts.append(f"{c.m['name']} is framed week on week and year on year; target columns are carried for reference only.")
    cs = capture_sentence(c, capture(c))
    if cs:
        parts.append(cs)
    parts.append("GA4 bookings are the <b>create path</b> only: <code>sevenrooms_booking_complete</code> with the "
                 "modify, manage and pre-arrival page paths excluded. Current, prior, year-ago and year to date are all on this basis.")
    return no_dashes(" ".join(parts))


def _target_basis(c: Ctx) -> str:
    from ..dates import week_basis_note
    return week_basis_note(c.w)


def foot_extra(c: Ctx) -> str:
    bits = []
    for v in c.venues:
        r = c.withheld(v["name"], "google_bookings", c.w)
        if r:
            bits.append(f"{v['name']} Google bookings are published as a gap: {md(r)}")
    for g in c.m.get("group", []):
        bits.append(f"{g['label']}: the shared ad accounts are shown once on this row and never split.")
    return (" <br>" + " ".join(bits)) if bits else ""


# ============================================================================ deep dive
def deepdive(c: Ctx) -> dict:
    w = c.w
    excl = set(c.m.get("deepdive_exclude", []))
    names = [v["name"] for v in c.portfolio() if v["name"] not in excl]
    venues, series = [], {}
    for n in names:
        web = c.web(n, w) or {}
        m, m0 = c.meta(n, w) or {}, c.meta(n, w.prior) or {}
        g, g0 = c.google(n, w) or {}, c.google(n, w.prior) or {}
        shared = c.is_shared_copy(n)
        venues.append({"name": n, "act": num(c.ga4(n, w)), "tgt": c.tgt(n) if not c.venue(n).get("tgt_label") else None,
                       "wow_b": num(c.ga4(n, w.prior)), "yoy_b": num(c.ga4(n, w.yoy)),
                       "users": web.get("users"), "sessions": web.get("sessions"),
                       "asd": num(web.get("asd"), 1), "bounce": num(web.get("bounce"), 4),
                       "meta_s": 0 if shared else num(m.get("spend"), 2),
                       "meta_sch": c.meta_bookings(n, w), "meta_sch_prior": c.meta_bookings(n, w.prior),
                       "goog_s": 0 if shared else num(g.get("spend"), 2),
                       "goog_c": num(c.google_bookings(n, w), 2), "goog_c_prior": num(c.google_bookings(n, w.prior), 2),
                       "shared": shared or bool(c.venue(n).get("shared_ads"))})
        series[n] = {"bookings": [num(c.ga4(n, x)) for x in c.weeks8],
                     "users": [(c.web(n, x) or {}).get("users") for x in c.weeks8]}
    cap = capture(c)
    bad = [n for n in names if cap.get(n, {}).get("status") == "red"]
    badge = ("GA4 BOOKING TAG UNDER RECORDING" if bad else "GA4 COLLECTION SOUND") if cap else "GA4 BOOKINGS"
    return {"market": c.m["name"], "ccy": c.m["ccy"], "sym": c.m["sym"], **page_dates(c), "badge": badge,
            "venues": venues, "cpa": c.m.get("cpa", {}),
            "series": {"labels": [f"W{c.wk_no(x)}" for x in c.weeks8], "venues": series},
            "obs": deepdive_obs(c, venues, cap)}


def deepdive_obs(c: Ctx, venues, cap) -> dict:
    sym, cpa = c.m["sym"], c.m.get("cpa", {})
    notes = c.week_notes()

    def cpa_line(plat, s_key, b_key, good, poor):
        items = [(v["name"], v[s_key] / v[b_key]) for v in venues if v[s_key] and v[b_key]]
        if not items:
            return []
        items.sort(key=lambda t: t[1])
        txt = ", ".join(f"{n} {sym}{x:,.0f}" for n, x in items)
        g = sum(1 for _, x in items if x <= cpa.get(good, 0))
        p = sum(1 for _, x in items if x >= cpa.get(poor, 1e9))
        return [f"{plat} CPAs: {txt}. {g} inside the {sym}{cpa.get(good)} good band, {p} at or above {sym}{cpa.get(poor)}."]

    def spend_line(plat, s_key, b_key, b0_key):
        s = sum_opt(v[s_key] for v in venues)
        b, b0 = sum_opt(v[b_key] for v in venues), sum_opt(v[b0_key] for v in venues)
        if s is None:
            return []
        return [f"{plat} spend {sym}{s:,.0f}; booking conversions {fmt_int(b)}, {words(pct(b, b0))} on last week."]

    ga4 = []
    for v in venues:
        x = cap.get(v["name"])
        if x and x["status"] != "green":
            ga4.append(f"<b>{v['name']}</b>: GA4 captures {x['ratio']:.2f} of SevenRooms website bookings against a normal "
                       f"{x['baseline']:.2f}, so its count is a floor.")
    tot, tot0 = sum_opt(v["act"] for v in venues), sum_opt(v["wow_b"] for v in venues)
    ga4.insert(0, f"Deep-dive venues booked {fmt_int(tot)} create-path GA4 bookings, {words(pct(tot, tot0))} week on week.")
    return {"meta": notes + spend_line("Meta", "meta_s", "meta_sch", "meta_sch_prior")
            + cpa_line("Meta", "meta_s", "meta_sch", "meta_good", "meta_poor"),
            "google": spend_line("Google", "goog_s", "goog_c", "goog_c_prior")
            + cpa_line("Google", "goog_s", "goog_c", "goog_good", "goog_poor"),
            "ga4": [no_dashes(x) for x in ga4]}


# ============================================================================ ads snapshot
def _web_block(c: Ctx, names, w) -> dict:
    rows = [c.web(n, w) for n in names]
    rows = [r for r in rows if r]
    if not rows:
        return None
    s = sum(r["sessions"] for r in rows)
    users = sum(r["users"] for r in rows)
    return {"bookings": num(sum_opt(c.ga4(n, w) for n in names)), "users": users, "sessions": s,
            "avgsec": num(sum(r["asd"] * r["sessions"] for r in rows) / s, 1),
            "engrate": num(sum(r["eng"] * r["sessions"] for r in rows) / s * 100, 1),
            "pps": num(sum(r["spv"] for r in rows) / s, 2),
            "newpct": num(sum(r["new"] for r in rows) / users * 100 if users else None, 1)}


def _plat_block(c: Ctx, names, plat, w) -> dict | None:
    """Spend, bookings, impressions and clicks, shared accounts counted once."""
    tot = {"spend": 0.0, "bookings": 0.0, "impr": 0.0, "clicks": 0.0}
    any_row, book_ok = False, True
    for n in names:
        if c.is_shared_copy(n) and len(names) > 1:
            continue
        a = c.meta(n, w) if plat == "meta" else c.google(n, w)
        if a is None:
            continue
        any_row = True
        if plat == "google" and c.venue(n).get("google_excluded"):
            continue  # unverified account: out of ad-driven bookings, CPA and the funnel
        b = c.meta_bookings(n, w) if plat == "meta" else c.google_bookings(n, w)
        tot["spend"] += a["spend"]
        tot["impr"] += a["impr"]
        tot["clicks"] += a["clicks"]
        if b is None:
            book_ok = False
        else:
            tot["bookings"] += b
    if not any_row:
        return None
    return {"spend": num(tot["spend"]), "bookings": num(tot["bookings"], 2) if book_ok else None,
            "impr": num(tot["impr"]), "clicks": num(tot["clicks"])}


def _channels(c: Ctx, names) -> list[dict]:
    acc = {}
    for i, lab in enumerate(("cur", "prior", "yoy")):
        for n in names:
            ch = (c.vf(n).get("channels") or {}).get(lab) or {}
            for k, x in ch.items():
                a = acc.setdefault(k, {"name": k, "s": [0, 0, 0], "b": [0, 0, 0]})
                a["s"][i] += round(x["s"])
                a["b"][i] += round(x["b"])
    return sorted(acc.values(), key=lambda a: -a["s"][0])


def _devices(c: Ctx, names) -> dict:
    acc = {}
    for n in names:
        for k, x in (c.vf(n).get("devices") or {}).items():
            acc[k.capitalize()] = acc.get(k.capitalize(), 0) + x["s"]
    t = sum(acc.values()) or 1
    return {k: round(acc.get(k, 0) / t * 100, 1) for k in ("Mobile", "Desktop", "Tablet")}


def _landing(c: Ctx, names) -> list[dict]:
    acc = {}
    for n in names:
        for k, x in (c.vf(n).get("landing") or {}).items():
            a = acc.setdefault(k, {"path": k, "s": 0, "b": 0})
            a["s"] += round(x["s"])
            a["b"] += round(x["b"])
    return sorted(acc.values(), key=lambda a: -a["s"])[:5]


def _campaigns(c: Ctx, names, top) -> list[dict]:
    rows, prior = [], {}
    for n in names:
        if c.is_shared_copy(n) and len(names) > 1:
            continue
        for key, plat in (("meta_campaigns", "meta"), ("google_campaigns", "google")):
            cc = c.vf(n).get(key) or {}
            for r in cc.get("prior", []):
                prior[(plat, r["id"])] = r["spend"]
            for r in cc.get("cur", []):
                withheld = (plat == "google" and (c.google_bookings(n, c.w) is None)) or \
                           (plat == "meta" and c.meta_bookings(n, c.w) is None)
                rows.append({"name": r["name"], "platform": r["platform"], "spend": round(r["spend"], 2),
                             "bookings": None if withheld else round(r["bookings"]),
                             "wow": direction(pct(r["spend"], prior.get((plat, r["id"]))))})
    return sorted(rows, key=lambda r: -r["spend"])[:top]


def _ads_venue(c: Ctx, names: list[str]) -> dict:
    w = c.w
    weeks = {"cur": w, "prior": w.prior, "yoy": w.yoy}
    web = {k: _web_block(c, names, x) for k, x in weeks.items()}
    meta = {k: _plat_block(c, names, "meta", x) for k, x in weeks.items()}
    goog = {k: _plat_block(c, names, "google", x) for k, x in weeks.items()}
    ads = {"meta": meta, "google": goog}
    notes = []
    for n in names:
        r = c.withheld(n, "google_bookings", w)
        if r:
            goog["na"] = True
            notes.append(f"{n}: Google bookings are published as a gap. {md(r)}")
        if c.venue(n).get("google_excluded"):
            goog["na"] = True
    if len(names) == 1:
        cpb = cpb_spend(c, names[0])
        if cpb is not None:
            meta["cpa_spend"] = num(c.meta(names[0], w)["cpb_spend"]) if c.meta(names[0], w) else None
    chans = _channels(c, names)
    trend_spend, trend_book = [], []
    for x in c.weeks8:
        mb, gb = _plat_block(c, names, "meta", x), _plat_block(c, names, "google", x)
        trend_spend.append(num((mb or {}).get("spend", 0) + (gb or {}).get("spend", 0)))
        trend_book.append(num(((mb or {}).get("bookings") or 0) + ((gb or {}).get("bookings") or 0)))
    paid = sum(ch["s"][0] for ch in chans if ch["name"] in PAID_CHANNELS)
    mc, gc = meta["cur"] or {}, goog["cur"] or {}
    out = {"web": web, "ads": ads, "channels": chans, "devices": _devices(c, names), "landing": _landing(c, names),
           "trend": {"labels": [f"W{c.wk_no(x)}" for x in c.weeks8], "spend": trend_spend, "bookings": trend_book},
           "funnel": {"impr": (mc.get("impr") or 0) + (gc.get("impr") or 0),
                      "clicks": (mc.get("clicks") or 0) + (gc.get("clicks") or 0),
                      "bookings": num((mc.get("bookings") or 0) + (gc.get("bookings") or 0)), "landing": paid},
           "campaigns": _campaigns(c, names, c.m.get("top_campaigns", 6)),
           "notes": c.week_notes() + notes}
    if len(names) == 1 and c.venue(names[0]).get("no_ly"):
        out["noyoy"] = True
    if len(names) == 1 and c.is_shared(names[0]):
        out["shared"] = "Ad accounts are shared across both Shiro sites, so paid share is not split by site."
    return out


def ads(c: Ctx) -> dict:
    names = [v["name"] for v in c.venues]
    data = {n: _ads_venue(c, [n]) for n in names}
    order = list(names)
    if len(names) > 1:
        data["All"] = _ads_venue(c, [v["name"] for v in c.portfolio()])
        order = ["All", *names] if c.m.get("ads_all_position", "first") == "first" else [*names, "All"]
    return {"market": c.m["name"], "sym": c.m["sym"], "week": c.w.label(),
            "fy": f"W{c.wk_no(c.w)} &middot; {fy_label(c.w.monday, c.m['fy_start_month'])}",
            "ext": True, "venues": order, "data": data,
            "foot_extra": no_dashes(capture_sentence(c, capture(c)))}


# ============================================================================ trends
def trends(c: Ctx) -> dict:
    w4 = c.w.back(4)
    venues = [v["name"] for v in c.venues]
    data, narr, alert = {}, {}, {}
    cap = capture(c)
    for n in venues:
        v = c.venue(n)

        def series(fn):
            return [fn(x) for x in w4], [fn(x.yoy) for x in w4]

        def users(x):
            return (c.web(n, x) or {}).get("users")

        def cvr(x):
            u, b = users(x), c.ga4(n, x)
            return None if not u or b is None else round(b / u * 100, 2)

        def gcpa(x):
            b, s = c.google_bookings(n, x), c.spend(n, "google", x)
            return None if not b or s is None else round(s / b, 1)

        def mcpa(x):
            a = c.meta(n, x)
            b = c.meta_bookings(n, x)
            return None if not a or not b else round(a["cpb_spend"] / b, 1)

        def local(x):
            if v.get("no_local_actions"):
                return None
            a = c.google(n, x)
            return None if a is None else round(a["local"], 1)

        def r1(fn):
            return lambda x: (lambda y: None if y is None else round(y, 1))(fn(x))

        panels = [("Website users", users, False, "n"), ("Conversion rate", cvr, False, "%"),
                  ("GA4 bookings", lambda x: c.ga4(n, x), False, "n"),
                  ("Meta bookings", r1(lambda x: c.meta_bookings(n, x)), False, "n"),
                  ("Google bookings", r1(lambda x: c.google_bookings(n, x)), False, "n"),
                  ("Google CPA", gcpa, True, "$"), ("Meta CPA", mcpa, True, "$"),
                  ("Google walk-in signals", local, False, "n")]
        rows = []
        for label, fn, inv, fmt in panels:
            ty, ly = series(fn)
            row = [label, ty, ly, inv, fmt]
            if c.is_shared(n) and label.startswith(("Meta", "Google")) and label != "Google walk-in signals":
                row.append("shared")
            rows.append(row)
        data[n] = rows
        u, u_ly = users(c.w), users(c.w.yoy)
        b, b_ly = c.ga4(n, c.w), c.ga4(n, c.w.yoy)
        narr[n] = no_dashes(
            f"W{c.wk_no(c.w)} users {fmt_int(u)} ({words(pct(u, u_ly))} on last year) with {fmt_int(b)} create-path GA4 "
            f"bookings ({words(pct(b, b_ly))}); conversion rate {cvr(c.w) or 'n/a'} per cent against "
            f"{cvr(c.w.yoy) or 'n/a'} per cent last year.")
        x = cap.get(n)
        if x and x["status"] != "green":
            alert[n] = [x["status"], "GA4 tag under recording",
                        f"Captures {x['ratio']:.2f} of SevenRooms website bookings, normal {x['baseline']:.2f}"]
            narr[n] += f" <b>Collection is short</b>: GA4 captures {x['ratio']:.2f} of SevenRooms website bookings, so read bookings and conversion as floors."
        elif c.withheld(n, "google_bookings", c.w):
            alert[n] = ["amber", "Google bookings withheld", c.withheld(n, "google_bookings", c.w)]
        elif x:
            alert[n] = ["green", "Collection sound", f"Captures {x['ratio']:.2f} of SevenRooms website bookings"]
        else:  # the page needs a chip for every venue
            alert[n] = ["blue", "Collection not checked", "No SevenRooms comparison was available this run"]
    sharednote = {n: "Meta and Google figures are the shared account across both sites, shown in full on each."
                  for n in venues if c.is_shared(n)}
    wk = [c.wk_no(x) for x in w4]
    return {"venues": venues, "labels": [""] * 4, "weekno": [f"W{k}" for k in wk],
            "dateTY": [range_label(x.monday, x.sunday, False) for x in w4],
            "dateLY": [range_label(x.yoy.monday, x.yoy.sunday, False) for x in w4],
            "fyrange": f"{fy_label(c.w.monday, c.m['fy_start_month'])} weeks {wk[0]}{EN_DASH}{wk[-1]}",
            "sym": c.m["sym"], "gaps": True, "data": data, "narr": narr, "alert": alert, "sharednote": sharednote}


# ============================================================================ covers
COVERS_CH = ["web", "gr", "ot", "walk", "recep", "ota", "tp"]


def covers(c: Ctx) -> dict:
    cov = c.f.get("covers")
    if not cov:
        raise RuntimeError("covers facts missing")
    ty, ly = cov["ty"], cov["ly"]
    w = c.w

    def row(v):
        n = v["name"]
        cell = lambda d, x: (d.get(n) or {}).get(x.folder) or {}
        ch = {k: {"c": cell(ty, w).get(k, 0), "p": cell(ty, w.prior).get(k, 0),
                  # a venue that did not exist last year had no covers then: a true zero, tagged below
                  "y": 0 if v.get("no_ly") else cell(ly, w.yoy).get(k, 0)} for k in COVERS_CH + ["other"]}
        r = {"name": n, "ga4": num(c.ga4(n, w)), "ch": ch}
        if v.get("pill") or v.get("no_ly"):
            r["pill"] = v.get("pill") or "new in 2026"
        return r

    port = [row(v) for v in c.portfolio()]
    out_rows = [row(v) for v in c.outside()]
    tot = lambda rows, k: sum(sum(r["ch"][ch][k] or 0 for ch in COVERS_CH) for r in rows)
    cur, prior, yoy = tot(port, "c"), tot(port, "p"), tot(port, "y")
    trend_total, trend_ot = [], []
    for x in c.weeks8:
        trend_total.append(sum(sum(((ty.get(v["name"]) or {}).get(x.folder) or {}).get(ch, 0) for ch in COVERS_CH)
                               for v in c.portfolio()))
        trend_ot.append(sum(((ty.get(v["name"]) or {}).get(x.folder) or {}).get("ot", 0) for v in c.portfolio()))
    web = sum(r["ch"]["web"]["c"] for r in port)
    late = sum(((ty.get(v["name"]) or {}).get(w.folder) or {}).get("_late", 0) for v in c.venues)
    ga4_tot = sum_opt(r["ga4"] for r in port)
    ga4_ly = sum_opt(num(c.ga4(v["name"], w.yoy)) for v in c.portfolio())
    yoy_p = pct(ga4_tot, ga4_ly)
    arrow = "&#9650;" if (yoy_p or 0) >= 0 else "&#9660;"
    callout = c.week_notes() + [
        f"Covers created came in at <b>{cur:,}</b>, <b>{words(pct(cur, prior))}</b> week on week and "
        f"<b>{words(pct(cur, yoy))}</b> year on year. Website is <b>{web / cur * 100:.0f} per cent</b> of covers; "
        f"the other channels never reach the GA4 number." if cur else "No covers were recorded this week.",
    ]
    if late:
        callout.append(f"The late-record rule removed <b>{late:,}</b> covers whose service date fell before the week they were created in (platform history re-syncs, not demand).")
    platform = c.m.get("covers_platform", "Platform")
    combined = [v for v in c.venues if len(v["sr"]) > 1]
    p = {"market": c.m["name"], "platform": platform, "tz": c.m["tz"],
         "platform_foot": f"<b>{platform}</b> = the market's third-party booking platform",
         "combined_note": "".join(f"<b>{v['name']}</b> = {' + '.join(v['sr'])} combined. " for v in combined),
         **page_dates(c), "venues": port,
         "trend": {"labels": [f"W{c.wk_no(x)}" for x in c.weeks8], "total": trend_total, "ot": trend_ot},
         "ga4_meta": f"Portfolio {fmt_int(ga4_tot)} create-path &middot; YoY {arrow}{abs(yoy_p or 0):.1f}%",
         "ga4_yoy": f"{arrow}{abs(yoy_p or 0):.1f}% YoY", "callout": no_dashes(" ".join(callout))}
    if out_rows:
        p["outside"] = out_rows
        p["outside_label"] = "Outside the portfolio: not in the totals above or in the 8-week trend"
    return p
