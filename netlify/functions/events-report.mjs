// Live data endpoint for the monthly London events report (Tripleseat).
// Calls public.events_report_payload(p_month) server-side so the DB key never reaches the browser.
// Requires Netlify env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// Endpoint: /.netlify/functions/events-report?month=2026-10

export default async (req) => {
  const json = (obj, status) =>
    new Response(JSON.stringify(obj), {
      status,
      headers: {
        "content-type": "application/json",
        "cache-control": status === 200 ? "public, max-age=600, s-maxage=600" : "no-store",
      },
    });

  const month = new URL(req.url).searchParams.get("month") || "";
  if (!/^20\d\d-(0[1-9]|1[0-2])$/.test(month)) {
    return json({ error: "Bad month. Use YYYY-MM, e.g. 2026-10." }, 400);
  }
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    return json({ error: "Server not configured: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY." }, 500);
  }
  try {
    const res = await fetch(`${url.replace(/\/$/, "")}/rest/v1/rpc/events_report_payload`, {
      method: "POST",
      headers: { apikey: key, Authorization: `Bearer ${key}`, "content-type": "application/json" },
      body: JSON.stringify({ p_month: `${month}-01` }),
    });
    const text = await res.text();
    if (!res.ok) return json({ error: `events_report_payload failed (${res.status}): ${text.slice(0, 300)}` }, 502);
    return json(JSON.parse(text), 200);
  } catch (e) {
    return json({ error: `Upstream error: ${String(e).slice(0, 300)}` }, 502);
  }
};
