# Aqua: Global Performance Reports

Live site: https://aquareports.netlify.app. Static pages plus four Netlify functions that read Supabase.

## How the reports get made

Nothing runs on a laptop.

| Job | Where | When | What it does |
|---|---|---|---|
| Weekly reports | GitHub Actions, `.github/workflows/weekly-reports.yml` | Mondays 07:17 UTC | Pulls the week, builds every payload and page, updates `manifest.json` and the hubs, checks the pages render, commits. Netlify deploys the commit. On the first Monday of a month it also builds last month's monthlies. |
| London daily, booking pipeline | Existing cloud scheduled tasks | Every morning | Write Supabase tables; the live pages read them through the functions. Unchanged. |

To rerun a week (after fixing a target or an override): GitHub > Actions > Weekly reports >
Run workflow, and enter the Monday. Leave it blank for the last completed week.

## Where things live

```
aqua/config/markets.toml    every market, venue, account id and venue rule (one place)
aqua/config/targets.toml    monthly GA4 booking targets, from the portfolio workbook
aqua/config/overrides.toml  judgement calls: withheld figures, a note for one week, capture baselines
aqua/sources/               GoMarble (GA4, Meta, Google Ads), BigQuery (Google Ads), Supabase (SevenRooms)
aqua/collect.py             pulls everything a market needs into <market>/w<date>/_facts.json
aqua/builders/              facts -> the payload each page template reads
aqua/run.py                 the Monday run, end to end
aqua/check.py               headless render check of every new page
aqua/publish.py             Netlify build: copies pages only into dist/
_tools/*_gen.py             page templates (unchanged output for every published week)
```

All three config files can be edited on GitHub in the browser.

## Definitions

Written once in code, not re-derived each week:

- **GA4 bookings**: `sevenrooms_booking_complete`, create path only (modify, manage and
  prearrival page paths excluded, `PARTIAL_REGEXP`). `aqua/sources/ga4.py`
- **Meta bookings**: `schedule_total`; Aqua Kyoto Paris uses `offsite_conversion.fb_pixel_custom`. `aqua/sources/meta.py`
- **Google bookings**: actions containing "booking" and "complete" and not "ga4"; per-venue
  exceptions in `markets.toml`. Dubai cost x 4.90 to AED, once. `aqua/sources/google_ads.py`
- **Covers**: SevenRooms by created date in market time, net of cancellations, bar and staff
  bookings excluded, late records dropped. Channel rules per market in `aqua/sources/sevenrooms.py`.
- **Weeks**: Monday to Sunday; YoY is minus 364 days; FY W1 is the first Monday on or after
  1 Feb (HK, London, Paris) or 1 Jan (USA, Dubai). `aqua/dates.py`
- **Weekly targets**: month x 7/30 inside a month; prorated by days across a month boundary.
- **Missing data** reads n/a, never 0. A market whose GA4 pull fails is not written at all.

## Secrets

GitHub repository secrets: `GOMARBLE_API_KEY`, `SUPABASE_DB_URL`, and `GCP_SA_KEY` once Google Ads
moves to BigQuery (set the variables `GOOGLE_ADS_SOURCE=bigquery`, `GOOGLE_ADS_BQ_PROJECT`,
`GOOGLE_ADS_BQ_DATASET`). Netlify keeps `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` for the
functions.

## What is published

Only pages. Payloads, raw pulls and facts files stay in the repo for audit and re-rendering but
are not served (`aqua/publish.py`). The archive of past weeks is kept as published HTML.
