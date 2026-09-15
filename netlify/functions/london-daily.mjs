// Live data endpoint for the Aqua London Daily Covers & Bookings report.
// Calls public.london_daily(reporting_day, days) server-side so the DB key never reaches
// the browser. The RPC reads a pg_cron-refreshed matview, never classifying reservations
// live, because live classification blows both the PostgREST and Netlify timeouts.
// Requires Netlify env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// Endpoint: /.netlify/functions/london-daily            -> yesterday, Europe/London
//           /.netlify/functions/london-daily?d=2026-09-14

export default async (req) => {
  const json = (obj, status) =>
    new Response(JSON.stringify(obj), {
      status,
      headers: {
        "content-type": "application/json",
        // Short cache: the matview refreshes four times an hour.
        "cache-control": status === 200 ? "public, max-age=300, s-maxage=300" : "no-store",
      },
    });

  const params = new URL(req.url).searchParams;
  const d = params.get("d");
  const days = params.get("days");

  if (d && !/^\d{4}-\d{2}-\d{2}$/.test(d)) {
    return json({ error: "Bad d. Use YYYY-MM-DD." }, 400);
  }
  const nDays = days ? Number(days) : 35;
  if (!Number.isInteger(nDays) || nDays < 8 || nDays > 120) {
    return json({ error: "Bad days. Use an integer from 8 to 120." }, 400);
  }

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    return json({ error: "Server not configured: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the Netlify site environment variables." }, 500);
  }

  try {
    const res = await fetch(`${url.replace(/\/$/, "")}/rest/v1/rpc/london_daily`, {
      method: "POST",
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ p_reporting_day: d || null, p_days: nDays }),
    });
    const text = await res.text();
    if (!res.ok) {
      return json({ error: `london_daily failed (${res.status}): ${text.slice(0, 300)}` }, 502);
    }
    const payload = JSON.parse(text);
    if (!payload || !Array.isArray(payload.venues) || payload.venues.length === 0) {
      return json({ error: "london_daily returned no venues." }, 502);
    }
    return json(payload, 200);
  } catch (e) {
    return json({ error: `Upstream error: ${String(e).slice(0, 300)}` }, 502);
  }
};
