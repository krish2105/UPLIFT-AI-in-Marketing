# Deploying MAWSIM

Two free services. Nothing here costs money, and nothing here is done
automatically — the steps that need an account are yours to take.

## What you need to click

### 1. GitHub

```bash
gh repo create krish2105/UPLIFT-AI-in-Marketing --public --source=. --push
```

The repository name in the master plan is `krish2105/UPLIFT-AI-in-Marketing`.
CI (`.github/workflows/check.yml`) runs on the first push: one job for the green
bar, one for Playwright.

### 2. Render — the API

New → Blueprint → point it at the repository. `render.yaml` describes the whole
service, so nothing needs configuring by hand except the secrets.

**Set in the Render dashboard, never committed:**

| Variable | Value |
|---|---|
| `GEMINI_API_KEY` | optional — free tier. Without it the deployed instance runs on the deterministic stub, which is a supported state. |
| `GROQ_API_KEY` | optional — free tier |
| `CORS_ORIGINS` | the Vercel URL, once step 3 gives you one |

`ANTHROPIC_API_KEY` is declared and deliberately unused: the provider chain
refuses to select it even when set, and a test asserts that.

**Expect the first build to take several minutes.** The build command runs all
four pipelines, and the weather ETL fetches 24 months of hourly history. That is
deliberate — Render's free tier has no persistent disk, so the database is baked
into the image rather than attached, which is sound here because the API is
read-only and the database is a cache of the pipelines rather than a system of
record.

### 3. Vercel — the web app

Import the repository. **Set the root directory to `apps/web`.**

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE` | the Render URL from step 2, e.g. `https://mawsim-api.onrender.com` |

### 4. Close the loop

Go back to Render and set `CORS_ORIGINS` to the Vercel URL. Without it the web
app renders its honest "API unreachable" state, which looks like a design
decision rather than a misconfiguration — which is exactly why the live smoke
test checks for it specifically.

### 5. Verify

```bash
LIVE_API_URL=https://mawsim-api.onrender.com \
LIVE_WEB_URL=https://uplift-ai-in-marketing.vercel.app \
make smoke-live
```

Five checks: the API answers, no dataset is empty, the page carries the
disclaimer, the web app can reach the API across origins, and all fifteen tabs
are present.

## What to expect from the free tier

The Render instance **sleeps after 15 minutes idle**, so the first request after
a quiet period takes about 50 seconds. The README says so. For a live demo, open
the API's `/healthz` a minute before you start.

## What is deliberately not automated

Deployment is not triggered from this repository beyond CI. Publishing anything
— a campaign, a creative, a report — is a human action taken outside the
application, and no agent in the crew has a tool that reaches the outside world.

## Enabling Admin on a deployed instance

An instance with no signing secret has no Admin role. That is the safe default
for a public URL — the capability is absent rather than open — and
`/admin/roles` reports which state a given instance is in rather than leaving a
document to go stale about it.

Enabling it takes one generated value and one dashboard field, and neither puts
the secret in this repository.

Generate one — 64 hex characters from the OS CSPRNG, printed once and stored
nowhere by this project:

```bash
uv run python scripts/mint_token.py --new-secret
```

Set it as `UPLIFT_SIGNING_SECRET` in the Render dashboard (Environment → Add
Environment Variable), which restarts the service.

**Paste it; do not pipe it through anything that keeps a transcript.** A chat
log, a CI log and a shell history are all durable copies you did not choose to
make. The value belongs in exactly two places: the dashboard, and wherever you
keep credentials.

Then mint a token locally with the *same* secret exported, and use it:

```bash
export UPLIFT_SIGNING_SECRET=<the value you just set on Render>
uv run python scripts/mint_token.py --role admin --hours 8 --subject you@laptop
```

```bash
curl -H "Authorization: Bearer $TOKEN" "https://mawsim-api.onrender.com/admin/roles"
```

Three things worth knowing before you do it:

**The secret is the whole of the access control.** There is no account to
compromise and no password to reset, so anyone holding it can mint any role.
Treat it the way you would an SSH key.

**Tokens are bearer credentials.** Whoever holds one can use it until it
expires, which is why the default lifetime is eight hours rather than a year. If
one leaks, mint a fresh one and refuse the old id:

```bash
curl -H "Authorization: Bearer $NEW" "$API/admin/tokens/revoke?jti=<id>"
```

**Revocations clear on restart**, because they live in process memory — the same
semantics as the kill switch, and for the same reason: a free instance has no
durable store worth adding for this. The short lifetime is the control that
survives a restart; revocation is the fast one.
