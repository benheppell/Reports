// Live data endpoint for the USA Covers Pace Tracker.
// Calls the Supabase RPC public.usa_pace_tracker() server-side so the DB key never reaches the browser.
// Requires Netlify env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// Endpoint: /.netlify/functions/usa-pace

export default async () => {
  const json = (obj, status) =>
    new Response(JSON.stringify(obj), {
      status,
      headers: {
        "content-type": "application/json",
        "cache-control": status === 200 ? "public, max-age=300, s-maxage=300" : "no-store",
      },
    });

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    return json(
      { error: "Server not configured: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the Netlify site environment variables." },
      500
    );
  }

  try {
    const r = await fetch(`${url.replace(/\/$/, "")}/rest/v1/rpc/usa_pace_tracker`, {
      method: "POST",
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "content-type": "application/json",
      },
      body: "{}",
    });
    const text = await r.text();
    if (!r.ok) {
      return json({ error: "Supabase RPC failed", status: r.status, detail: text.slice(0, 500) }, 502);
    }
    const rows = JSON.parse(text);
    return json({ generated_at: new Date().toISOString(), rows }, 200);
  } catch (e) {
    return json({ error: "Function error", detail: String(e) }, 500);
  }
};
