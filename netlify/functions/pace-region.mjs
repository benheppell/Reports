// Live data endpoint for the HK & USA Covers Pace Trackers.
// Calls the Supabase RPC public.pace_tracker_hk() / public.pace_tracker_usa() server-side
// so the DB key never reaches the browser. Region chosen via ?r=hk|usa.
// Requires Netlify env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// Endpoint: /.netlify/functions/pace-region?r=hk

const RPCS = { hk: "pace_tracker_hk", usa: "pace_tracker_usa" };

export default async (req) => {
  const json = (obj, status) =>
    new Response(JSON.stringify(obj), {
      status,
      headers: {
        "content-type": "application/json",
        "cache-control": status === 200 ? "public, max-age=300, s-maxage=300" : "no-store",
      },
    });

  const r = new URL(req.url).searchParams.get("r");
  const rpc = RPCS[r];
  if (!rpc) return json({ error: "Unknown region. Use ?r=hk or ?r=usa." }, 400);

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    return json({ error: "Server not configured: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the Netlify site environment variables." }, 500);
  }

  try {
    const res = await fetch(`${url.replace(/\/$/, "")}/rest/v1/rpc/${rpc}`, {
      method: "POST",
      headers: { apikey: key, Authorization: `Bearer ${key}`, "content-type": "application/json" },
      body: "{}",
    });
    const text = await res.text();
    if (!res.ok) return json({ error: "Supabase RPC failed", status: res.status, detail: text.slice(0, 500) }, 502);
    return json({ generated_at: new Date().toISOString(), rows: JSON.parse(text) }, 200);
  } catch (e) {
    return json({ error: "Function error", detail: String(e) }, 500);
  }
};
