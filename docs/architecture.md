# Architecture

## System overview

Wiseweb-AI is a decoupled web application with three runtime pieces plus a
frontend:

```
+--------------------------------+      +---------------------------------+
|  frontend (React SPA)          |      |  Vite dev server (5173)         |
|  src/pages/*                   |<-----|  proxies /api                   |
+---------------+----------------+      |  or `serve -s dist` for the    |
                |                       |  built bundle                   |
                |                       +---------------------------------+
                |  HTTP/JSON + JWT (access + refresh tokens)
                v
+---------------+------------------------------------+--------------------+
|  FastAPI backend (8000)                             |  app/api/routes/*  |
|  auth, websites, scans,                             v  app/services/*    |
|  findings, recommendations,             app/repositories/*  (data)      |
|  architecture, comparisons,                                               |
|  monitoring, reports                                                      |
+-------+-----------------------------+----------------+-------------------+
        |                             |                |
        v                             v                v
+-------+------+          +-----------+-----+        (Celery broker)
| PostgreSQL   |          | Redis            |              |
| (data)       |          | (queue)          |              v
+-------+------+          +---+-------------+    +-------+---------------+
        |                     |                 | Celery worker           |
        +---------------------+---------------->| app/workers/tasks/      |
                                                | runs ScanOrchestrator   |
                                                | per scan                |
                                                +-------------------------+
```

### Why a worker?

Scans are long-running (seconds to minutes). The API only creates the scan
record and enqueues the job; the Celery worker runs the orchestrator and
updates progress in the database, which the frontend polls
(`GET /scans/{id}/progress`). In development or CI, `CELERY_TASK_ALWAYS_EAGER=true`
runs scans inline so no Redis/worker is needed.

## Backend layout

```
app/
+-- api/               FastAPI routers (one per resource)
+-- ai/                AI pipeline: provider abstraction, evidence context,
|                      recommendation engine, Pydantic output schemas
+-- analyzers/         Per-category analyzers + shared base + registry
+-- config/            Pydantic-settings config + logging
+-- core/              DB engine, exceptions, dependencies (auth)
+-- crawler/           URL validation, fetch, parse, robots, browser
+-- models/            SQLAlchemy ORM models
+-- repositories/      Data-access layer used by services
+-- schemas/           Pydantic request/response models
+-- scoring/           Health scores, severity points, priority engine
+-- security/          SSRF guard, rate limiting, sanitization
+-- services/          Business logic (scan, website, findings, reports)
+-- utils/             URL/date/text helpers
+-- workers/           Celery app, task definitions, ScanOrchestrator
```

Dependencies flow downward only: `routes -> services -> repositories ->
models`, with `crawler`, `analyzers`, `ai`, and `scoring` invoked by the
orchestrator. This keeps each layer testable in isolation.

## Scan lifecycle

`ScanOrchestrator.run()` (in `app/workers/orchestrator.py`) is the heart of
a scan. Stages and their progress weights:

| Stage | % | Work |
| --- | --- | --- |
| `INITIALIZING` | 5 | Load scan + website, validate target |
| `CRAWLING` | 20 | Crawl site (SSRF-guarded), persist pages/resources/technologies |
| `ANALYZING_ARCHITECTURE` | 35 | Technology + architecture graph detection |
| `ANALYZING_SECURITY` | 42 | Headers, cookies, TLS, exposure |
| `ANALYZING_PERFORMANCE` | 49 | Page size, resources, scripts, images |
| `ANALYZING_ACCESSIBILITY` | 56 | HTML rules (+ optional Axe via Playwright) |
| `ANALYZING_PRIVACY` | 63 | Third-party requests, trackers, storage |
| `ANALYZING_SEO` | 70 | Metadata, links, structured data |
| `ANALYZING_CONTENT` | 77 | Quality, similarity, duplication |
| `ANALYZING_UX` | 84 | Signals and UX heuristics |
| `AI_CORRELATION` | 88 | Root-cause analysis |
| `AI_RECOMMENDATIONS` | 92 | Recommendations ranked P0-P3 |
| `AI_SUMMARY` | 96 | Executive summary |
| `FINALIZING` | 98 | Persist final state |
| `COMPLETED` | 100 | Mark scan complete |

Key properties:

- **Resilience:** a failing analyzer marks only its own category as `FAILED`
  in `analyzer_status`; the rest of the scan continues.
- **Idempotent rescans:** crawl data from a previous scan of the same site
  is cleared before persisting new data.
- **AI is optional:** the mock provider produces deterministic output from
  real evidence; the pipeline never invents findings.
- **No findings -> no score:** categories with zero findings are recorded as
  `null` (unmeasured), not `100`.

## Frontend layout

```
src/
+-- lib/            api client (typed fetch wrapper), shared types, helpers
+-- store/          auth provider (tokens, session bootstrap)
+-- components/ui/  minimal UI kit (button, card, table, dialog)
+-- components/scan/  score gauges, category scores, status badges
+-- components/layout/  app shell with sidebar
+-- pages/          one module per route
```

The SPA talks to the API via `src/lib/api.ts`, which mirrors every backend
route and implements automatic token refresh on 401. Routes are declared in
`src/App.tsx`; protected routes render inside the app shell, which redirects
to `/login` when no valid session exists.

## Adding a new analyzer

1. Create `app/analyzers/<category>/analyzer.py` implementing the
   `Analyzer` protocol from `app/analyzers/base.py`.
2. Register it in `app/analyzers/registry.py` with its category and stage.
3. Add a `_STAGE_WEIGHTS` entry in the orchestrator and a
   `_CATEGORY_STAGES` mapping if the category is new.
4. Add a score column to `Scan` + a migration, then surface it in
   `ScanResponse` and the frontend `CategoryScores` component.
5. Write tests in `backend/tests/analyzers/`.