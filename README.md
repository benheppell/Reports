# Aqua Hong Kong — Performance Reports

Static HTML reports (no build step). `index.html` links each week's reports.

## Structure
- `index.html` — landing page
- `hk/w18/dashboard.html` — SLT weekly dashboard
- `hk/w18/deep-dive.html` — venue deep dive (Performance + Weekly Trends tabs)
- `netlify.toml` — tells Netlify to publish the folder as-is

## Add a new week
Copy `hk/w18` to `hk/w19`, drop in the new reports, and add two links to `index.html`.
