# Booking pipeline backfill sources

These two files are the one-off backfill that loaded ISO weeks 37 to 41 of 2026 into
`public.booking_pipeline` on 18 October 2026. They are kept as the archive of that load.

- `sr_raw.py` SevenRooms rows per venue per created week, from Supabase, pulled 16 Oct 2026.
  `[wg1n,wg1c,wg2n,wg2c,wg3n,wg3c, ot1n..ot3c, rs1n..rs3c, webn, late]` per venue per week per year.
- `metrics.json` Meta, Google, GA4 and Search Console per venue per week per year.

**They are not read by anything.** The live pages read `public.booking_pipeline` through
`/.netlify/functions/booking-pipeline`, and the daily scheduled task rewrites that table from
source every morning. Nothing here needs updating.
