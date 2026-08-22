# Deployment

## Environment variables

See `.env.example` for the full list. The important ones:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | postgres URL (localhost) | SQLAlchemy engine URL; `sqlite:///./local.db` works for local dev |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | localhost:6379 DBs 0/1/2 | Redis connections |
| `CELERY_TASK_ALWAYS_EAGER` | `false` | `true` runs scans inline (no worker) — dev/test only |
| `JWT_SECRET` | dev default (warns) | **must** be set in production |
| `AI_PROVIDER` | `mock` | `openai` \| `anthropic` \| `mock` |
| `AI_API_KEY` | empty | provider key; missing key falls back to mock |
| `FRONTEND_URL` | http://localhost:5173 | CORS allow-list |
| `SEED_DEMO` | `false` | seed `demo@wiseweb-ai.local` on startup |
| `BROWSER_ENABLED` | `false` | Playwright-based analysis (heavy; off by default) |

## Running locally

```bash
# backend (from backend/)
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# worker (only if CELERY_TASK_ALWAYS_EAGER is false)
celery -A app.workers.celery_app worker --loglevel=info

# frontend (from frontend/)
npm install
npm run dev            # dev server proxies /api to :8000
```

## Migrations

Run `alembic upgrade head` manually after pulling new migrations:

```bash
cd backend && python -m alembic upgrade head
```

## Frontend build & API base URL

- `npm run build` typechecks and bundles to `frontend/dist`.
- The SPA reads the API base from `VITE_API_URL` (or `VITE_API_BASE_URL`),
  defaulting to the relative `/api/v1` (used by the dev proxy).

## Production checklist

1. Set a strong, random `JWT_SECRET`; never commit `.env`.
2. Use Postgres, not SQLite.
3. Decide the AI provider: `mock` (no external calls) or a real provider
   with a key managed via secrets, not env files in the image.
4. Run behind a reverse proxy (Caddy/Nginx) with TLS; configure
   `X-Forwarded-For` so the rate limiter sees real client IPs.
5. Confirm `FRONTEND_URL` matches the deployed origin (CORS).
6. Keep `SEED_DEMO=false` unless you want the demo account.
7. Consider swapping the in-process rate limiter for a Redis-backed one
   (see `app/security/rate_limit.py`).

## Known local-development notes

- Windows PowerShell: set env vars with `$env:NAME = "value"` before
  starting uvicorn; the settings are read at import time.
- If scan creation returns `503 UNAVAILABLE`, the Celery worker/Redis isn't
  reachable — either start them, or run with
  `CELERY_TASK_ALWAYS_EAGER=true` (dev).
- The demo flow: `python -m scripts.serve_demo` (port 8001), then
  `python -m scripts.seed_demo --scan` — see docs/architecture.md.
