"""Reconstruct a facts file from a published week's payloads, for offline tests.

Not every source figure survives into a payload, so this is approximate: it exists to prove the
builders produce payloads the generators render, and that the regenerated pages track the
published ones. Usage: python tests/fixture_from_published.py london 2026-10-26 OUT.json
"""
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from aqua.dates import Week  # noqa: E402


def main(slug, monday, out):
    w = Week(__import__("datetime").date.fromisoformat(monday))
    d = ROOT / slug / w.folder
    load = lambda f: json.loads((d / f).read_text()) if (d / f).exists() else None
    dash, dd, ads, tr, cov, cr = (load(f) for f in ("_dashboard_payload.json", "_deepdive_payload.json",
                                                    "_ads_payload.json", "_trends_payload.json",
                                                    "_covers_payload.json", "_covers_raw.json"))
    cfg = tomllib.loads((ROOT / "aqua/config/markets.toml").read_text())
    market = next(m for m in cfg["market"] if m["slug"] == slug)
    w8, w4 = w.back(8), w.back(4)
    facts = {"market": slug, "week": w.monday.isoformat(), "venues": {}, "errors": [], "shared_owner": {}}
    for v in market["venue"]:
        n = v["name"]
        a = ads["data"].get(n, {})
        f = {"errors": [], "ga4_book": {}, "web": {}, "meta": {}, "google": {}}
        ser = (dd or {}).get("series", {}).get("venues", {}).get(n)
        trow = {r[0]: r for r in tr["data"].get(n, [])}
        for i, x in enumerate(w8):
            f["ga4_book"][x.folder] = ser["bookings"][i] if ser else None
        for i, x in enumerate(w4):
            f["ga4_book"][x.folder] = trow["GA4 bookings"][1][i]
            f["ga4_book"][x.yoy.folder] = trow["GA4 bookings"][2][i]
            for plat, lab in (("meta", "Meta bookings"), ("google", "Google bookings")):
                f[plat][x.folder] = {"spend": 0, "bookings": trow[lab][1][i] or 0, "impr": 0, "clicks": 0,
                                     "cpb_spend": 0, "local": trow["Google walk-in signals"][1][i] or 0}
                f[plat][x.yoy.folder] = {"spend": 0, "bookings": trow[lab][2][i] or 0, "impr": 0, "clicks": 0,
                                         "cpb_spend": 0, "local": trow["Google walk-in signals"][2][i] or 0}
        for lab, x in (("cur", w), ("prior", w.prior), ("yoy", w.yoy)):
            wb = a["web"][lab]
            f["ga4_book"][x.folder] = wb["bookings"]
            f["web"][x.folder] = {"users": wb["users"], "sessions": wb["sessions"], "spv": wb["pps"] * wb["sessions"],
                                  "new": wb["newpct"] / 100 * wb["users"], "asd": wb["avgsec"], "bounce": 0.4,
                                  "eng": wb["engrate"] / 100}
            for plat in ("meta", "google"):
                b = a["ads"][plat][lab] or {}
                f[plat][x.folder] = {"spend": b.get("spend") or 0, "bookings": b.get("bookings") or 0,
                                     "impr": b.get("impr") or 0, "clicks": b.get("clicks") or 0,
                                     "cpb_spend": b.get("spend") or 0,
                                     "local": f[plat].get(x.folder, {}).get("local", 0)}
        for x in w8:  # fill the 8-week ad trend from the ads payload
            i = w8.index(x)
            f["meta"].setdefault(x.folder, {"spend": a["trend"]["spend"][i], "bookings": a["trend"]["bookings"][i],
                                            "impr": 0, "clicks": 0, "cpb_spend": a["trend"]["spend"][i], "local": 0})
            f["google"].setdefault(x.folder, {"spend": 0, "bookings": 0, "impr": 0, "clicks": 0, "cpb_spend": 0, "local": 0})
        drow = next((r for r in dash["venues"] + dash.get("outside", []) if r["name"] == n), {}) if dash else {}
        f["ytd_book"] = drow.get("ytd")
        f["channels"] = {lab: {c["name"]: {"s": c["s"][i], "b": c["b"][i]} for c in a["channels"]}
                         for i, lab in enumerate(("cur", "prior", "yoy"))}
        f["devices"] = {k.lower(): {"s": p, "b": 0} for k, p in a["devices"].items()}
        f["landing"] = {l["path"]: {"s": l["s"], "b": l["b"]} for l in a["landing"]}
        f["meta_campaigns"] = {"cur": [dict(c, id=c["name"], bookings=c["bookings"] or 0) for c in a["campaigns"] if c["platform"] == "Meta"], "prior": []}
        f["google_campaigns"] = {"cur": [dict(c, id=c["name"], bookings=c["bookings"] or 0) for c in a["campaigns"] if c["platform"] == "Google"], "prior": []}
        facts["venues"][n] = f
        if v.get("shared_ads"):
            facts["shared_owner"].setdefault(v["shared_ads"], n)
    if cov:
        ty, ly = {}, {}
        for r in cov["venues"] + cov.get("outside", []):
            ty[r["name"]] = {w.folder: {k: x["c"] for k, x in r["ch"].items()} | {"_late": 0},
                             w.prior.folder: {k: x["p"] for k, x in r["ch"].items()} | {"_late": 0}}
            ly[r["name"]] = {w.yoy.folder: {k: x["y"] or 0 for k, x in r["ch"].items()}}
        for i, x in enumerate(w8[:-2]):  # older weeks: put the published trend total on the first venue
            first = cov["venues"][0]["name"]
            ty[first][x.folder] = {"web": cov["trend"]["total"][i] - cov["trend"]["ot"][i], "ot": cov["trend"]["ot"][i], "_late": 0}
        facts["covers"] = {"ty": ty, "ly": ly}
        diag = ((cr or {}).get("diagnostic") or {})
        facts["web_rows"] = None
    Path(out).write_text(json.dumps(facts, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
