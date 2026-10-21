# Deployment

Nothing has been deployed as part of building this project — deployment
requires your own hosting accounts, and Section 3's collaboration rule
is explicit: explain the process before deploying anything. This
document is that explanation, plus the production configuration changes
already made to support it.

## Why no Docker, no Kubernetes, no separate infra

Section 64 explicitly excludes these for a project this size. Both
recommended platforms below auto-detect a Python app and a Node/Vite
app from the repo directly (a `requirements.txt` and a `package.json`
are all they need) — a Dockerfile would add a layer of complexity this
project doesn't need yet.

## Recommended platforms (beginner-friendly, free tiers)

| | Backend (FastAPI) | Frontend (static Vite build) |
|---|---|---|
| **Recommended** | [Render](https://render.com) | [Vercel](https://vercel.com) |
| Alternatives | Railway, Fly.io | Netlify, Cloudflare Pages, GitHub Pages |

Both recommended platforms: connect a GitHub repo, auto-detect the
project type, redeploy automatically on every push, and have a free
tier sufficient for a project this size.

## Backend (Render)

1. Push this repo to GitHub.
2. On Render: **New → Web Service**, connect the repo, root directory
   `backend`.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   (note: **no** `--reload` in production — that flag is a dev-only
   convenience that re-imports code on file changes and shouldn't run
   in a deployed process).
5. Environment variables (Render's dashboard, not committed to git):
   - `CORS_ORIGINS` — the frontend's exact deployed URL, e.g.
     `https://collegepath-ai.vercel.app`. Multiple origins are
     comma-separated. **This is the one setting most likely to be
     forgotten and cause a silent, confusing failure** — Phase 10 found
     exactly this class of bug locally (`localhost` vs `127.0.0.1`
     mismatch); in production the same mismatch happens between the
     placeholder default and your actual deployed frontend URL.
   - `SIMILARITY_THRESHOLD`, `TOP_K`, `MAX_QUERY_LENGTH` — optional,
     defaults from `config.py` are fine to start with.
6. Render provides the live URL once deployed (e.g.
   `https://collegepath-api.onrender.com`) — you'll need this for the
   frontend's `VITE_API_BASE_URL` (below).

## Frontend (Vercel)

1. On Vercel: **New Project**, connect the repo, root directory
   `frontend`.
2. Build command: `npm run build` (Vercel auto-detects this for a Vite
   project). Output directory: `dist`.
3. Environment variable: `VITE_API_BASE_URL` set to the backend's live
   URL from the Render step above (e.g.
   `https://collegepath-api.onrender.com`). **This must be set at build
   time**, not runtime — Vite bakes `VITE_*` env vars into the built
   JS bundle, so changing it later requires a rebuild, not just a
   restart. This is a real change made during Phase 13: before this,
   the frontend only ever called the relative path `/api/...`, which
   silently 404s once the frontend and backend are on different
   domains with no reverse proxy between them.
4. Deploy. Vercel provides the live frontend URL — go back and confirm
   it exactly matches what you set in the backend's `CORS_ORIGINS`.

## Same-origin alternative (skip the CORS/base-URL config entirely)

If you'd rather not manage two separate domains and CORS between them,
put both behind one reverse proxy (e.g. an nginx config or a platform
that supports it) that serves the frontend's static files and forwards
`/api/*` to the backend on the same domain. In that setup, the frontend
needs no `VITE_API_BASE_URL` (the default `/api` already works) and the
backend's `CORS_ORIGINS` becomes unnecessary, since same-origin requests
aren't subject to CORS at all. This is more setup work upfront but
removes an entire category of "forgot to update the URL/origin"
mistakes — worth it for anything beyond a quick demo deployment.

## Production checklist

- [ ] `CORS_ORIGINS` set to the frontend's real deployed origin(s), not
      the localhost defaults
- [ ] Backend started without `--reload`
- [ ] `VITE_API_BASE_URL` set at frontend build time if frontend and
      backend are on different domains
- [ ] `.env` files are not committed (already covered by `.gitignore`)
- [ ] No secrets to manage beyond the above — this app has no API keys,
      no database credentials, and no user authentication, so there is
      nothing else sensitive to configure
