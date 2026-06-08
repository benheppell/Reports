# Aqua — Global Performance Reports

Static HTML reports (no build step), one repo, deployable as a global hub and/or per-market sites.

## Structure
- `index.html` — global hub (market tabs; weekly + monthly lists). Built by `build_hub.py`.
- `<market>/index.html` — per-market landing (e.g. `hk/`, `london/`, `usa/`). Built by `build_hub.py`.
- `<market>/<week>/` — weekly reports, e.g. `hk/w18/dashboard.html`, `hk/w18/deep-dive.html`.
- `<market>/m<YYYY-MM>/` — monthly reports, e.g. `hk/m2026-05/dashboard.html`.
- `manifest.json` — the list of markets and their available weeks/months. Hubs are generated from this.
- `netlify.toml` — publishes the folder as-is.

Report back-links point to `../index.html` (the market landing), so they work whether the site root is the whole repo or a single market folder.

## Deploying

### Global site (SLT — all markets)
Netlify → Add new site → Import → this repo. Publish directory = `.` (repo root). This serves `index.html`.

### Per-market sites (location-only access)
Create one additional Netlify site per market, all from the same repo, each with a different **base/publish directory**:
- Hong Kong site → publish directory `hk`
- London site → publish directory `london`
- USA site → publish directory `usa`

Each becomes its own URL (e.g. `aqua-reports-hk.netlify.app`) serving only that market. Set a different **password** on each (Netlify → Site settings → Access control → Password protection; requires Netlify Pro) and share each link only with the relevant team. The global site gets its own password for SLT.

## Adding a new week or month
1. Drop the new report folder in under the market (e.g. `hk/w19/`, `hk/m2026-06/`).
2. Add an entry to `manifest.json` under that market's `weekly` or `monthly` list (newest first).
3. Run `python3 build_hub.py` to regenerate the hub and landing pages.
The Monday scheduled task does all of this automatically.
