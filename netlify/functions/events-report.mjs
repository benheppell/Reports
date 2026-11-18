// Live data endpoint for the monthly London events report (Tripleseat).
// Calls public.events_report_payload(p_month) server-side so the DB key never reaches the browser.
// Requires Netlify env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// Endpoints: /.netlify/functions/events-report?month=2026-10
//            /.netlify/functions/events-report?week=2026-11-09   (any date in the ISO week)
// Team-level figures are never served here; they only go in the emailed report.

export default async (req) => {
  const json = (obj, status) =>
    new Response(JSON.stringify(obj), {
      status,
      headers: {
        "content-type": "application/json",
        "cache-control": status === 200 ? "public, max-age=600, s-maxage=600" : "no-store",
      },
    });

  const q = new URL(req.url).searchParams;
  const month = q.get("month") || "", week = q.get("week") || "";
  let rpc, body;
  if (/^20\d\d-(0[1-9]|1[0-2])$/.test(month)) {
    rpc = "events_report_payload"; body = { p_month: `${month}-01` };
  } else if (/^20\d\d-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/.test(week)) {
    rpc = "events_report_week_payload"; body = { p_week: week };
  } else {
    return json({ error: "Use month=YYYY-MM or week=YYYY-MM-DD." }, 400);
  }
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    return json({ error: "Server not configured: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY." }, 500);
  }
  try {
    const res = await fetch(`${url.replace(/\/$/, "")}/rest/v1/rpc/${rpc}`, {
      method: "POST",
      headers: { apikey: key, Authorization: `Bearer ${key}`, "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    const text = await res.text();
    if (!res.ok) return json({ error: `${rpc} failed (${res.status}): ${text.slice(0, 300)}` }, 502);
    return json(JSON.parse(text), 200);
  } catch (e) {
    return json({ error: `Upstream error: ${String(e).slice(0, 300)}` }, 502);
  }
};
