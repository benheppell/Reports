// Live data endpoint for the Aqua booking pipeline report.
// Calls public.booking_pipeline_payload(market) server-side so the DB key never reaches the
// browser. The table is written by the daily scheduled run; nothing is classified live, so the
// RPC is a plain read and cannot blow the PostgREST or Netlify timeouts.
// Requires Netlify env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// Endpoint: /.netlify/functions/booking-pipeline?m=london

const MARKETS = ["london", "hk", "usa", "dubai", "paris"];

export default async (req) => {
  const json = (obj, status) =>
    new Response(JSON.stringify(obj), {
      status,
      headers: {
        "content-type": "application/json",
        // The data changes once a morning.
        "cache-control": status === 200 ? "public, max-age=600, s-maxage=600" : "no-store",
      },
    });

  const m = new URL(req.url).searchParams.get("m");
  if (!m || !MARKETS.includes(m)) {
    return json({ error: `Bad m. Use one of ${MARKETS.join(", ")}.` }, 400);
  }

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    return json({ error: "Server not configured: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the Netlify site environment variables." }, 500);
  }

  try {
    const res = await fetch(`${url.replace(/\/$/, "")}/rest/v1/rpc/booking_pipeline_payload`, {
      method: "POST",
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ p_market: m }),
    });
    const text = await res.text();
    if (!res.ok) {
      return json({ error: `booking_pipeline_payload failed (${res.status}): ${text.slice(0, 300)}` }, 502);
    }
    const payload = JSON.parse(text);
    if (!payload || !Array.isArray(payload.rows)) {
      return json({ error: "booking_pipeline_payload returned no rows array." }, 502);
    }
    return json(payload, 200);
  } catch (e) {
    return json({ error: `Upstream error: ${String(e).slice(0, 300)}` }, 502);
  }
};
