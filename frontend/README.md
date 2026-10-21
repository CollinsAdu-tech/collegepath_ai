# CollegePath AI — Frontend

React + Vite chat interface for CollegePath AI. Requires the backend
running on :8000 (see `../backend/README.md`) — `/api/*` calls are
proxied there during development (`vite.config.js`).

## Setup

```bash
cd frontend
npm install
```

## Run

```bash
npm run dev
```

Visit http://localhost:5173.

## Build

```bash
npm run build
```

For a production deployment where the backend lives on a different
domain, set `VITE_API_BASE_URL` at build time (see `.env.example` and
`../docs/deployment.md`) — it defaults to the relative `/api`, which
only works for local dev or a same-origin reverse-proxy setup.

See `../docs/manual-qa-checklist.md` for the browser-based checks that
aren't automated (keyboard nav, focus states, responsive layout).
