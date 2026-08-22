# API Reference

Base URL: `/api/v1` (Vite proxies it in dev; `VITE_API_URL` overrides it).
Interactive docs: `/docs` (Swagger UI), `/openapi.json`.

## Authentication

Token-based auth with JWT access + refresh tokens.

| Endpoint | Method | Description |
| --- | --- | --- |
| `/auth/register` | POST | Create account (`full_name`, `email`, `password` ≥ 8 chars) → 201 with tokens |
| `/auth/login` | POST | `email` + `password` → 200 with tokens |
| `/auth/refresh` | POST | `refresh_token` → new token pair |
| `/auth/me` | GET | Current user profile |

All other endpoints require `Authorization: Bearer <access_token>`.
Access tokens live 30 minutes; refresh tokens 7 days. The frontend refreshes
automatically on a 401 and retries the request once.

## Error envelope

Every error uses a consistent shape; stack traces are never exposed:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": { "errors": [ { "type": "string_too_short", "loc": ["body", "name"], "msg": "…" } ] }
  }
}
```

| Code | HTTP | Meaning |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | Malformed body, bad query params, or app-level validation |
| `UNAUTHENTICATED` | 401 | Missing/invalid/expired token |
| `FORBIDDEN` | 403 | Authenticated but not allowed |
| `NOT_FOUND` | 404 | Resource missing or owned by another user |
| `CONFLICT` | 409 | Duplicate resource (e.g. duplicate email or normalized URL) |
| `RATE_LIMITED` | 429 | Too many requests (scan creation: 10/min per IP) |
| `UNAVAILABLE` | 503 | Scan queue unavailable (worker/Redis offline) |
| `INTERNAL_ERROR` | 500 | Unexpected failure (never leaks internals) |

Ownership rule: every resource (website, scan, finding, recommendation,
architecture, report) is scoped to the authenticated user; cross-user access
returns 404.

## Users

| Endpoint | Method | Response |
| --- | --- | --- |
| `/users/me` | GET | `UserResponse` |
| `/users/me/stats` | GET | `{websites_count, scans_count, user_id}` |

## Websites

| Endpoint | Method | Description |
| --- | --- | --- |
| `/websites` | GET | List own websites (array, newest first) |
| `/websites` | POST | Create — body `{name, url, website_type, industry?, target_audience?, description?}`; URL is normalized |
| `/websites/{id}` | GET | Website detail |
| `/websites/{id}` | DELETE | Delete website + all scans/findings (200 or 204) |
| `/websites/{id}/monitoring?enabled=bool` | POST | Toggle change monitoring |
| `/websites/{id}/competitors` | GET | List competitors |
| `/websites/{id}/competitors` | POST | Add competitor `{name, url}` |

`WebsiteResponse` includes `normalized_url` — the canonical form used for
scanning and duplicate detection.

## Scans

| Endpoint | Method | Description |
| --- | --- | --- |
| `/scans/websites/{website_id}` | POST | Queue a scan. Body `{crawl_depth: 1–5, page_limit: 1–200}` → 201 `ScanResponse`. Fails with `UNAVAILABLE` if the worker is offline |
| `/scans/{scan_id}` | GET | Scan detail (status, stage, scores, `analyzer_status`) |
| `/scans/{scan_id}/progress` | GET | Poll-friendly progress (status, stage, percent, pages) |
| `/scans/{scan_id}/cancel` | POST | Cancel a running scan (200; 409 if no longer cancellable) |
| `/scans/website/{website_id}/list` | GET | `{items, total}` of a website's scans |

Scan statuses: `QUEUED → CRAWLING → ANALYZING → AI_PROCESSING → COMPLETED`,
or `FAILED` / `CANCELLED`.

## Findings

| Endpoint | Method | Description |
| --- | --- | --- |
| `/findings/scan/{scan_id}` | GET | `{items, total}`; filters `category`, `severity`, `status` |
| `/findings/{id}` | GET | Finding with evidence |
| `/findings/{id}` | PATCH | `{status}` — one of `OPEN, ACKNOWLEDGED, IN_PROGRESS, FIXED, VERIFIED, DISMISSED` |

Each finding carries `severity` (CRITICAL/HIGH/MEDIUM/LOW/INFO),
`confidence` (0–1), `impact`, `effort`, `affected_url`, and `evidence`
(items of `{evidence_type, source, value, metadata, confidence}`) so every
conclusion can be audited.

## Recommendations

| Endpoint | Method | Description |
| --- | --- | --- |
| `/recommendations/scan/{scan_id}` | GET | `{items, total}`; filters `category`, `priority` |
| `/recommendations/{id}` | PATCH | `{status}` |

Recommendations are ranked by `priority_score` and bucketed into
`P0`–`P3`. Each includes `root_cause`, `implementation_guidance`,
`finding_ids`, and a `priority_explanation` of the scoring factors.

## Architecture

| Endpoint | Method | Description |
| --- | --- | --- |
| `/architecture/scan/{scan_id}` | GET | `{nodes, edges}` — detected technologies/platforms/resources and their relationships |

## Comparisons

| Endpoint | Method | Description |
| --- | --- | --- |
| `/comparisons` | POST | `{website_id, competitor_ids: []}` → `{sites, ai_explanation, gaps}`. Each competitor's scores come from the user's own website whose URL matches the competitor (exact URL first, then www-agnostic hostname); competitors with no matching scanned website show no scores |

## Monitoring

| Endpoint | Method | Description |
| --- | --- | --- |
| `/websites/{id}/changes` | GET | List prior comparisons (newest first) |
| `/websites/{id}/changes` | POST | `{base_scan_id, compare_scan_id}` → diff + AI summary |

## Reports

| Endpoint | Method | Description |
| --- | --- | --- |
| `/reports/scan/{id}/executive` | GET | Executive report: overall + category scores, AI summary (headline, executive_summary, top_risks, biggest_opportunities, roadmap), top risks and recommendations |
| `/reports/scan/{id}/developer` | GET | Developer report: full findings with evidence, detected technologies, crawl metrics |

## Health

`GET /health` → `{status: "ok", app, environment}` (unauthenticated).
