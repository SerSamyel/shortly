# Shortly

A URL shortener with click analytics, built as the final project of
[AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp) with a team of coding agents.

## Problem

People share long URLs in chats, slides and printed materials. Long links are hard to read and type,
and whoever shares them never learns whether anyone opened them.

Shortly turns a long URL into a short one (`http://<host>/k3x9qab`, or a custom alias like `/my-talk`)
and shows the owner how the link performs: clicks per day, unique visitors, top referrers and countries.

## What it does

| Area | Behaviour |
| --- | --- |
| Accounts | Sign up and log in with email and password (argon2 hashes, JWT bearer tokens) |
| Links | Create from an `http(s)` URL; optional custom alias (3-32 chars, `a-z 0-9 -`, reserved words blocked) and expiration; disable, enable, delete |
| Redirect | `GET /{code}` returns **302** to the target; disabled, deleted or unknown links return **404**, expired links **410** |
| Codes | Never reused: a deleted link's code stays taken, so old printed links can't be hijacked |
| Analytics | Total clicks, clicks and unique visitors per day (30 days), top 10 referrer domains, top 10 countries |
| Privacy | Raw IPs are never stored or logged. The redirect turns an IP into a country and a daily-salted visitor hash |
| Limits | 30 new links per user per minute (429 above that) |

The full specification is in [`_docs/plan.md`](_docs/plan.md) and the API contract in [`openapi.yaml`](openapi.yaml).

## Architecture

```
Browser ── React SPA (built into the API image, served as static files)
   │
   ▼
FastAPI API ──► Postgres  (users, links, daily aggregates)
   │   │
   │   └──────► Redis     (code → link cache, rate limits, daily visitor salt)
   │
   └──► Redpanda topic "clicks" ──► click consumer ──► Postgres
```

- **Hot path:** the redirect reads the link from Redis (falls back to Postgres if Redis is down),
  answers 302 immediately and publishes a click event without waiting for the broker.
- **Click pipeline:** the consumer applies events to daily aggregate tables in one transaction per batch
  and commits offsets afterwards. Every event has an id, so redelivered events are counted once.

| Layer | Technology |
| --- | --- |
| Backend | Python 3.14, FastAPI, SQLAlchemy 2 (async), Alembic, aiokafka, redis-py, uv |
| Frontend | React 19, Vite, TypeScript, React Router; charts in plain SVG |
| Storage | Postgres 17 (SQLite for unit tests), Redis 8 |
| Events | Redpanda (Kafka API) |
| Packaging | One Docker image for API + frontend; Docker Compose for the full stack |

## Run it

Requirements: Docker with Compose. For development without Docker: [uv](https://docs.astral.sh/uv/) and Node.js 22+.

```bash
docker compose up --build
```

Open <http://localhost:8000>, sign up, create a link, open it in another browser window
and watch the click appear on the link's page within a few seconds.

Optional: country analytics need the free DB-IP Lite database
(`make geoip`, or `./scripts/download-geoip.ps1` on Windows). Without it, countries show as `unknown`.

### Development

| Task | macOS / Linux / Git Bash | Windows PowerShell |
| --- | --- | --- |
| Install dependencies | `make install` | `cd backend; uv sync; cd ..\frontend; npm install` |
| Start Postgres, Redis, Redpanda | `make deps-up` | `docker compose up -d --wait postgres redis redpanda` |
| API with reload | `make dev-backend` | see below |
| SPA on :5173 (proxies /api) | `make dev-frontend` | `cd frontend; npm run dev` |
| SPA with the mock backend | `make dev-mock` | `cd frontend; npm run dev:mock` (log in as `demo@example.com` / `demo-password`) |

API with reload in PowerShell:

```powershell
cd backend
$env:DATABASE_URL = "postgresql://shortly:shortly@localhost:5432/shortly"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:KAFKA_BOOTSTRAP = "localhost:19092"
uv run alembic upgrade head
uv run uvicorn shortly.app:create_app --factory --reload
```

Without any environment variables the API runs on a local SQLite file with an in-process cache and no broker.

## Tests

| Suite | What it covers | Command |
| --- | --- | --- |
| Backend unit | Validation, auth, links, redirect, cache and broker failures, aggregation (SQLite + fakes) | `make test-backend` / `cd backend; uv run pytest` |
| Frontend unit | Services mock, auth screens, create/list/disable/delete flows (Vitest + Testing Library) | `make test-frontend` / `cd frontend; npm test` |
| Integration | Real Postgres + Redis + Alembic migrations, full flows, cache invalidation, Redis outage, redelivery, real broker round trip | `make test-integration` (after `make deps-up`) |

`make test` runs both unit suites; `make test-all` runs everything.

Integration tests in PowerShell (after starting the deps):

```powershell
cd backend
$env:TEST_DATABASE_URL = "postgresql+asyncpg://shortly:shortly@localhost:5432/shortly_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"
$env:TEST_KAFKA_BOOTSTRAP = "localhost:19092"
uv run pytest tests_integration -v
```

## How this project is built: the agent team

The project follows a spec-first workflow with separate agents for specifying, building and verifying.

- [`AGENTS.md`](AGENTS.md) - project context every coding agent reads first (`CLAUDE.md` points to it)
- [`_docs/process.md`](_docs/process.md) - task lifecycle, orchestrator rules, parallel work in git worktrees
- [`_docs/team/`](_docs/team) - roles: product manager, software engineer, QA engineer
- [`.claude/agents/`](.claude/agents) - the same roles as Claude Code subagents
- [`_docs/task-template.md`](_docs/task-template.md) - every groomed issue: goal, acceptance criteria, out of scope, constraints
- [`_docs/testing-guidelines.md`](_docs/testing-guidelines.md) - test layers and rules
- Task tracker: GitHub Issues of this repository

## Project status

| Course criterion | Status |
| --- | --- |
| Problem description, spec, agent team, context docs | Done |
| Full-stack app (frontend, backend, database), single-command run | Done |
| Unit + integration tests | Done |
| Containerization (Docker Compose, including the database) | Done |
| Public task tracker with acceptance criteria | Next: GitHub Issues |
| Deployment (VPS, k3s, Helm), CI/CD with dev and manual prod promotion, rollback | Planned |
| Observability (OpenTelemetry, Prometheus, Loki, Tempo, Grafana), alerting, on-call agent | Planned |

## License

MIT. Country data: [DB-IP Lite](https://db-ip.com), CC BY 4.0.
