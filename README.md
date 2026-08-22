# Wiseweb-AI

AI-powered website intelligence and improvement platform. Wiseweb-AI crawls
websites **passively** (public pages only), analyzes them across eight
categories, computes explainable health scores, correlates findings into
root causes, and produces prioritized, evidence-backed recommendations.

> **Disclaimer:** Wiseweb-AI is a passive analysis tool, not a penetration
> testing framework. It never probes private endpoints, never submits
> forms, never authenticates to third parties, and never performs
> exploitation. It reads public pages, headers, and metadata only.

## Features

- **Passive crawler** — respects `robots.txt`, rate-limits requests, enforces
  size caps, and never follows redirects off-site without validation.
- **8 analysis categories** — Security, Performance, Accessibility, Privacy,
  SEO, Content, UX, Architecture.
- **Explainable scoring** — every score is derived from concrete findings
  with severity × confidence deductions; no black-box numbers.
- **AI correlation** — root causes, prioritized recommendations (P0–P3), and
  an executive summary, all grounded in actual evidence. Works without an AI
  API key via a deterministic mock provider.
- **Comparisons & monitoring** — score your site against competitors and
  diff scans over time.
- **Reports** — executive and developer reports per scan.

## Architecture at a glance

```
frontend (React SPA, Vite)
   │  /api/v1 (REST + JWT)
   ▼
FastAPI (backend) ── PostgreSQL (SQLAlchemy + Alembic)
   │  scan jobs    ── Redis (Celery broker)
   ▼
Celery worker ── ScanOrchestrator ── crawler ── analyzers ── AI pipeline ── scoring
```

See [docs/architecture.md](docs/architecture.md) for the full picture.

## Repository layout

```
backend/            FastAPI app, crawler, analyzers, AI pipeline, worker, tests
frontend/           React + TypeScript + Vite SPA
demo-site/          Local demo website used by the seed script
docs/               Architecture, API, database, security, deployment docs
start-dev.ps1       Windows helper: starts backend + demo site + frontend
```

---

## Getting started (run on your own machine)

### 1. Prerequisites

- **Python 3.10 – 3.12** — [python.org](https://python.org) (verify: `python --version`)
- **Node.js 22+** — [nodejs.org](https://nodejs.org) (verify: `node --version`)
- **Git** — `git --version`

No database or Redis is required for the quick start (SQLite + inline scan
mode). PostgreSQL/Redis are only needed for the production-style setup.

### 2. Clone and install dependencies

```bash
git clone <your-repo-url> Wiseweb-AI
cd Wiseweb-AI
```

Create the virtual environment at the **repo root** (one venv, used by the
whole project) and install the backend packages into it:

```bash
python -m venv venv
```

| OS | Activate |
| --- | --- |
| Windows (PowerShell) | `venv\Scripts\Activate.ps1` |
| macOS / Linux | `source venv/bin/activate` |

With the venv active, install everything:

```bash
# Backend (from the repo root)
pip install -r backend/requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

> **Tip:** you can skip activation and call the venv interpreter directly:
> `venv\Scripts\python.exe` (Windows) or `venv/bin/python` (macOS/Linux).
> **Always use the venv interpreter, not system `python`** — system Python
> does not have the project's packages.

### 3. Quick start (SQLite + eager mode — no Postgres, no Redis, no worker)

Configure the backend to use a local SQLite file and run scan jobs inline.
Set these environment variables **in each terminal that runs the backend**
(or create `backend/.env` with the same values):

| OS | Command |
| --- | --- |
| PowerShell | `$env:DATABASE_URL = "sqlite:///./local.db"; $env:CELERY_TASK_ALWAYS_EAGER = "true"` |
| bash / zsh | `export DATABASE_URL="sqlite:///./local.db"` and `export CELERY_TASK_ALWAYS_EAGER="true"` |

Then open **three terminals** (each inherits nothing from the others, so set
the env vars again in the backend one):

**Terminal 1 — backend API (port 8000):**

```bash
cd backend
# (set DATABASE_URL / CELERY_TASK_ALWAYS_EAGER first, see above)
python -m alembic upgrade head   # create/migrate the database (first run only)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — demo website (port 8001):** serves the bundled demo site used
by the seed scan. Only needed to scan the demo website.

```bash
cd backend
python -m scripts.serve_demo
```

**Terminal 3 — frontend (port 5173):**

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** — Vite proxies `/api` to the backend on 8000.
API docs live at http://localhost:8000/docs.

### 4. Seed demo data (optional but recommended)

With the demo site already running (Terminal 2), run:

```bash
cd backend
python -m scripts.seed_demo --scan
```

This creates:

- **Login:** `demo@wiseweb-ai.local` / `demopass123`
- **Website:** "Acme Widgets (Demo)" with a completed scan and findings

> The demo scan runs against your local demo site with SSRF checks relaxed
> **for that script only** (a loud warning is printed). The API itself never
> accepts localhost/private targets unless the dev-only
> `ALLOW_LOCALHOST_SCANS=true` env var is set (see `.env.example`; also set
> automatically by `start-dev.ps1`), which lets you re-scan the demo site
> from the UI — never enable it in production.

### 5. Windows convenience helper

On Windows you can skip the three terminals with the included script:

```powershell
cd Wiseweb-AI
.\start-dev.ps1
```

It starts anything not already running (backend with logs in
`backend/uvicorn.log`, demo site, Vite) and prints the URLs and login.

### 6. Production-style setup (PostgreSQL + Redis + Celery worker)

Only if you want the full stack — the quick start above is enough for normal
use.

```bash
# 1. Copy the env template. IMPORTANT: put it where the backend runs.
#    If you launch uvicorn from backend/, the file must be backend/.env.
cp .env.example backend/.env
# edit backend/.env → DATABASE_URL, JWT_SECRET, etc.
```

You need PostgreSQL and Redis running locally.
Then:

```bash
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000   # API

# separate terminal: Celery worker (scans run here instead of inline)
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

With `CELERY_TASK_ALWAYS_EAGER=false` (default), scans are queued to Redis
and executed by the worker.

## Troubleshooting

| Symptom | Cause & fix |
| --- | --- |
| `No module named uvicorn` / `fastapi` | You used system `python`. Use the venv: activate it or call `venv\Scripts\python.exe` / `venv/bin/python` explicitly, then `pip install -r backend/requirements.txt` again. |
| `Could not open requirements file` | Wrong directory. Run pip from the repo root with `-r backend/requirements.txt`, or from `backend/` with `-r requirements.txt`. |
| Login fails / page shows network error | The backend is not running (check port 8000: `curl http://127.0.0.1:8000/api/v1/health`). Start it — Terminal 1 or `start-dev.ps1`. |
| Scan fails on real sites (e.g. Google) but works on the demo site | Older code had a gzip double-decode bug — make sure you pulled the latest code. |
| `sqlite3.OperationalError: no such table` | Run `python -m alembic upgrade head` from `backend/` first. |
| Port already in use (8000/5173/8001) | Something already runs there. Stop it or change the port. |
| Demo scan fails | The demo site (Terminal 2, port 8001) must be running **before** `seed_demo --scan`. |
| `.env` values ignored | The backend reads `.env` relative to its working directory. Launch uvicorn from `backend/` and keep the file at `backend/.env`. |
| `demo@wiseweb-ai.local` rejected | `.local` is a special-use domain. This project's email validator explicitly accepts it — make sure the backend is running the latest code (old builds reject it with a 422). |

## Testing

```bash
cd backend
python -m pytest
```

The suite (89 tests) covers SSRF guards, the crawler, analyzers, scoring,
the AI pipeline and the API. It uses a throwaway SQLite database and the
deterministic mock AI provider — no external services. Note: the scan API
tests crawl `https://example.com`, so internet access is required.

## Project documentation

| Topic | File |
| --- | --- |
| System architecture & scan lifecycle | [docs/architecture.md](docs/architecture.md) |
| REST API reference | [docs/api.md](docs/api.md) |
| Database schema & migrations | [docs/database.md](docs/database.md) |
| Crawler behavior & safety | [docs/crawler.md](docs/crawler.md) |
| AI pipeline & prompt contracts | [docs/ai-pipeline.md](docs/ai-pipeline.md) |
| Security model | [docs/security.md](docs/security.md) |
| Scoring & prioritization | [docs/scoring.md](docs/scoring.md) |
| Deployment & configuration | [docs/deployment.md](docs/deployment.md) |

## License

MIT — see [LICENSE](LICENSE).
