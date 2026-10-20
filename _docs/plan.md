# Shortly — URL shortener with click analytics

Final project for AI Dev Tools Zoomcamp 2026.

## 1. Problem

People share long URLs in chats, slides and printed materials. Long links are hard to read and type,
and the person who shared them has no idea whether anyone opened them.

Shortly turns a long URL into a short one (`https://<host>/aB3x9Qk` or a custom alias like
`/my-talk`) and shows the owner how the link performs: total clicks, clicks per day, top referrers,
countries and unique visitors.

## 2. Users

| Role | What they do | Auth |
| --- | --- | --- |
| Owner | Registers, creates and manages links, views analytics | Email + password |
| Visitor | Opens a short link and gets redirected | None |

Only registered users can create links. Redirects are public.

## 3. Key user journey (the one we instrument and alert on)

**Visitor opens a short link → gets redirected to the target URL.**

This is the hot path. Its health is measured by:

- redirect success ratio (3xx for active links, correct 404/410 otherwise; 5xx = failure)
- redirect latency (p95 target: < 50 ms server-side with a warm cache)
- click pipeline lag (time from redirect to the click appearing in analytics; target: < 60 s)

Secondary journey: **owner creates a link** (success ratio, validation errors vs server errors).

## 4. Functional requirements

### 4.1 Accounts

- Sign up with email and password (password ≥ 8 chars, stored as a bcrypt/argon2 hash).
- Log in, receive a bearer token (JWT, 24 h lifetime). Log out on the client side.
- Duplicate email on sign-up → visible error, no second account.

### 4.2 Links

- Create a link from a target URL.
  - Only `http` and `https` URLs, max 2048 chars.
  - Links pointing to the service's own host are rejected (no redirect loops).
  - Without an alias, the service generates a random 7-char base62 code.
- Custom alias (optional).
  - 3–32 chars, `[a-z0-9-]`, case-insensitive, cannot start or end with `-`.
  - Must be unique across all links, including deleted ones.
  - Reserved words are rejected: `api`, `app`, `login`, `signup`, `health`, `metrics`, `static`, `assets`, `docs`.
- Expiration (optional): a date-time in the future. After it, the redirect returns **410 Gone**.
- Disable / enable: a disabled link returns **404**; analytics are kept; it can be re-enabled.
- Delete: the link disappears from the owner's list and returns **404**. Analytics are deleted.
  The code/alias is **never reused**, so old printed links cannot be hijacked.
- Owner sees a paginated list of their links: short URL, target, created, status
  (active / disabled / expired), total clicks.
- An owner can only see and change their own links (other users' links → 404).
- Rate limit: 30 link creations per user per minute → **429**.

### 4.3 Redirect

- `GET /{code}` → **302** to the target URL. 302 (not 301) so browsers don't cache the redirect
  and every click is counted.
- Lookup goes through Redis (cache-aside, TTL 1 h). Disable, delete and expiry invalidate the cache.
- If Redis is down, the redirect falls back to Postgres (slower, but works).
- Each successful redirect publishes a click event to Redpanda. Publishing is fire-and-forget:
  a broker failure must not break the redirect, but it is counted as a metric.

### 4.4 Analytics

Shown on a link's detail page:

- total clicks
- clicks per day for the last 30 days (chart)
- top 10 referrer domains (empty referer → "direct")
- top 10 countries (from IP via DB-IP Lite database; unknown → "unknown")
- unique visitors per day

**Privacy rule:** raw IP addresses are never stored or sent anywhere. In the redirect handler the
service derives:

- `country` from the IP (DB-IP Lite, local file)
- `visitor_hash = sha256(daily_salt + ip + user_agent)`; the salt rotates every UTC day and is never stored
  with the data, so hashes cannot be linked across days

Only `link_id`, `timestamp`, `referrer_domain`, `country`, `visitor_hash` go into the click event.

A separate **click consumer** reads events from Redpanda and updates daily aggregates in Postgres.
It must be idempotent (each event has an `event_id`; reprocessing does not double-count).

## 5. Non-functional requirements

- Runs locally with one command: `make up` (Docker Compose: frontend build + API + consumer + Postgres + Redis + Redpanda).
- Tests with one command: `make test` (unit) and `make test-integration`; `make test-all` runs both.
- Configuration through environment variables only (DB URL, Redis URL, broker URL, JWT secret, base URL).
- Database migrations with Alembic.
- Documentation (README, docs, task tracker) in English.

## 6. Architecture

```
Browser ── React SPA (served by API as static files)
   │
   ▼
FastAPI API ──► Postgres (users, links, daily aggregates)
   │   │
   │   └──► Redis (code → link cache, rate limit counters)
   │
   └──► Redpanda topic `clicks` ──► Click consumer (Python, aiokafka) ──► Postgres
```

- Backend: Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, aiokafka, redis-py, uv.
- Frontend: React + Vite + TypeScript. All backend calls in one `services/` layer with a mock
  implementation (frontend is built first against the mock).
- API contract: `openapi.yaml` at the repo root, derived from the frontend services layer.
- One container image for API + frontend static files; the consumer uses the same image with a different command.

## 7. Testing

- Backend unit tests (pytest): validation, code generation, alias rules, auth, cache logic with fakes.
- Frontend unit tests (Vitest + Testing Library) against the mock services.
- Integration tests (pytest) against the Docker Compose stack: sign up → create link → redirect →
  click appears in analytics; disable/expire/delete behaviour; cache invalidation; Redis-down fallback.
- E2E test (Playwright): owner creates a link in the UI, a second browser context opens it,
  the owner sees the click on the analytics page.

## 8. Deployment

- One VPS (4 vCPU / 8 GB RAM minimum) running **k3s**.
- App packaged as a **Helm chart** (`deploy/helm/shortly`).
- Two environments as two namespaces: `dev` and `prod`, each with its own Postgres, Redis and Redpanda.
- Ingress via Traefik (bundled with k3s) with TLS from cert-manager / Let's Encrypt.
- Images in GitHub Container Registry, tagged `YYYYMMDD-HHMMSS-<shortsha>`.

## 9. CI/CD (GitHub Actions)

1. On every PR and push: backend unit tests ‖ frontend tests (parallel).
2. Build the Compose stack, run integration and E2E tests.
3. On push to `main`: build the image once, push to GHCR, `helm upgrade` the `dev` namespace,
   check `/health`.
4. **Manual** workflow `promote-to-prod`: takes the tag currently deployed in dev and deploys it to prod.
5. **Rollback**: manual workflow input "tag" (or `helm rollback`) to redeploy a previous image in prod.

Cluster credentials live in GitHub environment secrets (`dev`, `prod`); `prod` requires approval.

## 10. Observability

- OpenTelemetry SDK in API and consumer: traces, metrics, structured JSON logs.
- Every log line carries `trace_id` and `span_id`; the trace continues through Redpanda
  (trace context in message headers), so one click is one trace from redirect to aggregate update.
- Resource attributes: `service.name`, `deployment.environment`, `service.version` (image tag).
- Stack (separate Helm release, namespace `observability`): OTel Collector → Prometheus (metrics),
  Loki (logs), Tempo (traces) → Grafana.
- **No customer data in telemetry**: no IPs, no target URLs, no emails, no tokens or passwords.
  Links are referenced by `link_id` only.

Application metrics:

- `redirects_total{status}` — redirects by outcome (ok, not_found, gone, error)
- `redirect_duration_seconds` — histogram
- `redirect_cache_total{result}` — hit / miss / error
- `click_events_published_total{result}` — ok / failed
- `click_consumer_lag_seconds` — event age when processed
- `links_created_total{result}` — ok / validation_error / error

Grafana dashboard filtered by environment and version.

## 11. Alerting

- **RedirectErrorsHigh**: share of 5xx redirects > 5% over 5 minutes (min. 20 requests) in prod.
- **ClickPipelineStalled**: consumer lag p95 > 120 s for 10 minutes.

Each alert includes service, environment, version, owner and a dashboard link.

## 12. On-call agent

- Grafana alert → webhook → `on-call-agent` service in the cluster.
- The service starts a Kubernetes Job with a headless coding agent (Claude Code), passing the alert payload.
- The agent investigates (logs, traces, metrics via Grafana API, the repository), reproduces the failure
  with a test, makes the smallest fix and **opens a pull request**. It never deploys and never touches prod data.
- If the alert is a false positive, it writes an explanation as a GitHub issue comment instead.
- The session log is saved as a Job artifact; the Job is cleaned up afterwards.
- Demo: a deliberately introduced bug (redirect fails for aliases containing `-`) → alert → agent PR.

## 13. Out of scope for MVP

- QR codes, link editing (target URL change), teams/shared links, custom domains
- OAuth login, email verification, password reset
- Bot filtering in analytics
- Multi-node cluster, managed databases, backups (documented as next steps)

## 14. Open questions

- VPS provider and domain (decided later; development starts locally).
