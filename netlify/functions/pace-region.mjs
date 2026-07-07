// Live data endpoint for the HK & USA Covers Pace Trackers.
// Calls the Supabase RPC public.pace_tracker_hk() / public.pace_tracker_usa() server-side
// so the DB key never reaches the browser. Region chosen via ?r=hk|usa.
// Optionally also returns the pinned 2025-finals reference (public.pace_ly_final_reference_<region>()).
// Requires Netlify env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// Endpoint: /.netlify/functions/pace-region?r=hk

const RPCS = { hk: "pace_tracker_hk", usa: "pace_tracker_usa" };
const REF_RPCS = { hk: "pace_ly_final_reference_hk" };

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
  const refRpc = REF_RPCS[r];

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    return json({ error: "Server not configured: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the Netlify site environment variables." }, 500);
  }

  const callRpc = async (name) => {
    const res = await fetch(`${url.replace(/\/$/, "")}/rest/v1/rpc/${name}`, {
      method: "POST",
      headers: { apikey: key, Authorization: `Bearer ${key}`, "content-type": "application/json" },
      body: "{}",
    });
    const text = await res.text();
    if (!res.ok) throw new Error(`${name} failed (${res.status}): ${text.slice(0, 300)}`);
    return JSON.parse(text);
  };

  try {
    // Reference is optional; never let it fail the main pace payload.
    const [rows, reference] = await Promise.all([
      callRpc(rpc),
      refRpc ? callRpc(refRpc).catch(() => []) : Promise.resolve([]),
    ]);
    return json({ generated_at: new Date().toISOString(), rows, reference }, 200);
  } catch (e) {
    return json({ error: "Supabase RPC failed", detail: String(e) }, 502);
  }
};
