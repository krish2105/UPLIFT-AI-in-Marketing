# Deploying the web app

Vercel's Next.js defaults would build this correctly with no configuration at
all, and it was deployed that way. `../vercel.json` exists anyway, for the same
reason `render.yaml` does: **a deployment that lives only in a dashboard is a
deployment that cannot be restored from a zip of this repository.** Someone
rebuilding this in a year should not have to infer the root directory, the
region, or the framework from a screenshot.

Three things in it are decisions rather than defaults:

**Root directory.** This is a monorepo: the Next app is `apps/web`, and Vercel's
project settings must point there. That single field is NOT expressible in
`vercel.json` — it is a project setting in the dashboard, and it is the one
piece of this deployment that genuinely cannot be committed. `docs/REDEPLOY_RUNBOOK.md`
names it as a manual step for exactly that reason.

**Region `sin1`.** Singapore, matching the API on Render. The pair talks to each
other on almost every page, and putting them on opposite sides of the planet
adds a round trip to every request for no benefit to a Dubai audience.

**Three response headers.** `nosniff`, a referrer policy, and `DENY` on framing.
The application shows a compliance verdict; it should not be embeddable in a
page that surrounds it with someone else's branding.

`NEXT_PUBLIC_API_BASE` is not set here. `next.config.ts` falls back to the
production API URL when `VERCEL` is present, so a fresh clone deploys working
rather than rendering its honest "API unreachable" state because someone forgot
a dashboard field.
