# Deploying InventoryIQ

Target architecture:

```
Browser ──► Vercel (React/Vite static build)
                 │  VITE_API_BASE_URL
                 ▼
            Render (FastAPI Docker) ──► Gemini API
```

Everything needed is in the repository:

| File | Purpose |
|---|---|
| `Dockerfile` | API image (Python 3.12 + LightGBM's OpenMP runtime) |
| `render.yaml` | Render Blueprint (Docker web service, `/health` check, env prompts) |
| `frontend/vercel.json` | Vite build settings + SPA rewrites for React Router |
| `.env.example` | Local configuration template |

> The Gemini key belongs in Render's secret environment variables. Never commit it.

## Prerequisites

- The repository on GitHub (`main` branch).
- A [Render](https://render.com) account.
- A [Vercel](https://vercel.com) account.
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

## 1. Deploy the API on Render

### Blueprint (recommended)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/mirabhakta/inventoryIQ)

1. Render Dashboard → **New** → **Blueprint** (the button above starts the same flow).
2. Connect `mirabhakta/inventoryIQ`. Render reads `render.yaml`.
3. When prompted, set:
   - **`GEMINI_API_KEY`** — your key (secret).
   - **`ALLOWED_ORIGINS`** — start with `http://localhost:5173`. You will add the Vercel URL in step 3.
   - `GEMINI_MODEL` is already set to `gemini-3.8-flash`.
4. Apply and wait for the Docker build (the first build installs pandas/LightGBM and takes a few minutes).
5. Copy the service URL, e.g. `https://inventoryiq-api.onrender.com`.

Verify:

```bash
curl https://inventoryiq-api.onrender.com/health
# {"status":"ok","service":"inventoryiq","version":"1.1.0","ai_configured":true}
```

Then open `https://inventoryiq-api.onrender.com/docs`.

> Render free instances sleep after inactivity. The first request after a sleep takes roughly 30 seconds.

### Manual service (alternative)

Create a **Web Service** → Docker → `Dockerfile` at `./Dockerfile` → plan **Free** →
health check path `/health` → add the same environment variables.

## 2. Deploy the frontend on Vercel

1. Vercel → **Add New Project** → import the repository.
2. Set **Root Directory** to `frontend`.
3. Framework preset: **Vite** (build `npm run build`, output `dist`).
4. Add an environment variable:
   - **`VITE_API_BASE_URL`** = your Render URL, e.g. `https://inventoryiq-api.onrender.com` (no trailing slash).
5. Deploy. Copy the production URL, e.g. `https://inventoryiq.vercel.app`.

`frontend/vercel.json` rewrites all routes to `index.html`, so refreshing `/dashboard` works.

## 3. Close the CORS loop

The API only accepts origins listed in `ALLOWED_ORIGINS`. After Vercel gives you the
production URL:

1. Render → `inventoryiq-api` → **Environment**.
2. Set **`ALLOWED_ORIGINS`** to the Vercel URL:
   ```
   https://inventoryiq.vercel.app
   ```
   Multiple origins are comma-separated. Keep `http://localhost:5173` if you also
   develop locally:
   ```
   https://inventoryiq.vercel.app,http://localhost:5173
   ```
3. Save. Render redeploys automatically.
4. Open the Vercel URL and upload `data/sample_sales.csv`.

### Vercel preview deployments

Preview URLs are unique per deployment (`https://<project>-git-<branch>-<team>.vercel.app`).
The API uses an exact allowlist, so previews are blocked until you add each origin to
`ALLOWED_ORIGINS`. For a portfolio demo, add the production URL and test there; add
preview origins only while actively testing them.

## 4. Post-deploy verification

- [ ] `/health` returns 200 and `ai_configured: true`
- [ ] `/docs` loads
- [ ] Landing page loads over HTTPS
- [ ] `data/sample_sales.csv` uploads and the dashboard shows `$674K` total revenue
- [ ] The forecast panel says **90-day LightGBM forecast** and shows MAE
- [ ] A larger upload (e.g., 60,000 rows) also loads; the forecast panel shows the
      benchmark-skipped note instead of MAE
- [ ] The alert panel shows 7 alerts; opening it shows all 7
- [ ] A store filter changes the KPIs (`Store 1` → `$236K`)
- [ ] **AI Summary** returns a generated paragraph (requires the key)
- [ ] Refreshing `/dashboard` does not 404 (Vercel SPA rewrite)
- [ ] The browser console has no CORS or JavaScript errors

## 5. Rollback

| Platform | Steps |
|---|---|
| Render | Service → **Deploys** → previous deploy → **Redeploy** |
| Vercel | Project → **Deployments** → previous deployment → **Promote to Production** |

The API is stateless; there are no database migrations. Rolling back only changes
code and configuration.

## Free-tier limits and expectations

- **Memory:** 512 MB. The upload limit is 10 MB / 200,000 rows; very wide datasets can
  still be memory-heavy. Keep the demo dataset reasonably scoped.
- **Large uploads:** the dashboard forecasts the daily total and skips the
  four-model benchmark above 5,000 rows / 50 series; the UI shows a note instead
  of MAE. This keeps a 200k-row upload around a few seconds on one CPU.
- **Cold starts:** Free Render services sleep. Expect a slow first request.
- **No auth:** This is a public portfolio demo. Do not upload confidential data.
- **Caching:** Cleaned datasets and `/analyze` payloads are cached in process memory
  for 15 minutes. The cache resets on deploy or restart and is not shared across
  instances.
- **One worker:** The Docker `CMD` pins `--workers 1` so the in-process cache stays
  coherent and memory stays within the free tier.
