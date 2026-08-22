# Security Model

Wiseweb-AI analyzes other people's websites, so safety is the top design
priority. This document covers both **the product's security posture** (how
we keep scanned targets safe) and **the platform's own security** (how we
protect users and data).

## 1. Protecting scanned targets (SSRF defense in depth)

The crawler and comparison scanner can be pointed at any URL a user
supplies. The system prevents requests to non-public targets at every layer:

### URL validation (`app/security/ssrf.py`)
- Only `http`/`https` schemes are accepted; URLs with embedded credentials
  are rejected.
- Hostnames are checked against dangerous names: `localhost`, single-label
  hostnames (`db`, `admin`, `intranet`…), and suffixes `.internal`,
  `.local`, `.lan`, `.corp`.
- Cloud metadata address ranges (e.g. `169.254.169.254`) are always
  blocked.

### DNS + IP validation
- Every hostname is resolved and every resolved IP is checked against
  private, loopback, link-local, and reserved ranges (IPv4 and IPv6) via
  `ipaddress` and dnspython. Any hit is rejected before a request is made.

### Redirect guard
- A custom httpx transport (`RedirectGuardTransport`) intercepts **every
  redirect hop** — sync and async — and re-runs the same checks on each new
  target. A redirect that escapes the policy is refused (the fetch fails
  closed).

### Defense in depth
- Validations run at: `WebsiteService` create (normalized URL), scan start,
  every page fetch, every resource probe, and every redirect hop.
- Limits: page cap (200 max), depth cap (5 max), body size cap (5 MB),
  concurrency and delay bounds — an accidental misconfiguration cannot cause
  a runaway.

### Demo exception (explicitly fenced)
- Scanning `localhost:8001` (the bundled demo site) is only possible from
  `backend/scripts/seed_demo.py`, which constructs the orchestrator with
  `allow_internal=True` and logs a loud **DEMO MODE** warning.
- The API layer never sets `allow_internal` — it is not an API field. Even
  with `allow_internal`, `file://` and non-http schemes are still rejected.

## 2. Platform security

### Authentication
- Passwords hashed with **bcrypt** (never stored in plaintext, never logged).
- JWT access tokens (30 min) + refresh tokens (7 days), HS256 with a
  configurable secret; the dev-default secret triggers a startup warning.
- All resource queries are user-scoped; cross-user access returns 404.

### Rate limiting
- In-process token bucket on scan creation (10/min per IP) since scans are
  expensive. The interface is designed to be swapped for a Redis-backed
  limiter in production.

### Error handling
- One consistent error envelope; the generic handler returns
  `INTERNAL_ERROR` without stack traces or internals.

### CORS
- Hardcoded allow-list of frontend origins (`FRONTEND_URL`, localhost:5173).
  No wildcard with credentials.

### Output safety
- HTML captured from targets is **never re-served** to the UI; reports and
  findings show extracted text/values only. `app/security/sanitization.py`
  strips/escapes untrusted strings.

## 3. Product posture: passive-only

- No exploitation, no credential attacks, no brute force, no form
  submission, no private-endpoint probing.
- `robots.txt` is honored.
- User agent identifies the crawler (`WisewebAI-Bot/1.0`) with a contact URL.
- Findings must be backed by stored evidence — the AI cannot add findings,
  only interpret real ones.

## 4. Operational checklist (production)

- Set a strong `JWT_SECRET` (and rotate it on compromise).
- Keep `AI_PROVIDER` at `mock` or supply a real key — never ship keys in
  code or images; use secrets management.
- Replace the in-process rate limiter with a Redis-backed one if needed.
- Run behind a reverse proxy that sets `X-Forwarded-For` correctly (the
  limiter trusts it).
- Pin dependency versions; build images from `requirements.txt` with
  lockfiles where possible.
- Postgres is the intended production DB; SQLite is for dev/tests only.
