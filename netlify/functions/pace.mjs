// Live data endpoint for the London Covers Pace Tracker.
// Calls the Supabase RPCs public.pace_tracker() (live pace) and
// public.pace_ly_final_reference() (pinned 2025 finals) server-side so the DB key never reaches the browser.
// Requires Netlify env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
// Endpoint: /.netlify/functions/pace

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

  const callRpc = async (rpc) => {
    const r = await fetch(`${url.replace(/\/$/, "")}/rest/v1/rpc/${rpc}`, {
      method: "POST",
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "content-type": "application/json",
      },
      body: "{}",
    });
    const text = await r.text();
    if (!r.ok) throw new Error(`${rpc} failed (${r.status}): ${text.slice(0, 300)}`);
    return JSON.parse(text);
  };

  try {
    // Reference is optional; never let it fail the main pace payload.
    const [rows, reference] = await Promise.all([
      callRpc("pace_tracker"),
      callRpc("pace_ly_final_reference").catch(() => []),
    ]);
    return json({ generated_at: new Date().toISOString(), rows, reference }, 200);
  } catch (e) {
    return json({ error: "Supabase RPC failed", detail: String(e) }, 502);
  }
};
