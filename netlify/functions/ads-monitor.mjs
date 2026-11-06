// Live data endpoint for the ads monitor pages (/ads/<market>/).
// Reads public.ads_monitor server-side so the database key never reaches the browser. The table
// is rewritten each morning by the GitHub daily job (aqua/jobs/ads_monitor.py); nothing is
// computed here.
// Requires Netlify env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// Endpoint: /.netlify/functions/ads-monitor?m=london

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
    const res = await fetch(
      `${url.replace(/\/$/, "")}/rest/v1/ads_monitor?market=eq.${m}&select=payload,updated_at`,
      { headers: { apikey: key, Authorization: `Bearer ${key}` } },
    );
    const text = await res.text();
    if (!res.ok) {
      return json({ error: `ads_monitor read failed (${res.status}): ${text.slice(0, 300)}` }, 502);
    }
    const rows = JSON.parse(text);
    if (!rows.length) {
      return json({ error: "No data yet for this market. It is written by the morning job." }, 404);
    }
    return json({ ...rows[0].payload, updated_at: rows[0].updated_at }, 200);
  } catch (e) {
    return json({ error: `Upstream error: ${String(e).slice(0, 300)}` }, 502);
  }
};
