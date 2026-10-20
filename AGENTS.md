# Shortly

URL shortener with click analytics. Owners create short links; visitors get redirected;
owners see clicks per day, referrers, countries and unique visitors.
Full specification: `_docs/plan.md`.

## Layout

- `backend/` - FastAPI API and click consumer (Python 3.14, uv)
- `frontend/` - React + Vite + TypeScript SPA
- `openapi.yaml` - the API contract between frontend and backend; it wins every disagreement
- `compose.yaml` - full local stack (app, consumer, Postgres, Redis, Redpanda)
- `_docs/` - process, roles and guidelines

## Commands

- `make up` - run the full stack in Docker Compose (http://localhost:8000)
- `make test` - backend + frontend unit tests
- `make test-integration` - backend integration tests (needs Postgres and Redis, see `make deps-up`)
- `make test-all` - everything above
- `cd backend && uv sync` - install backend dependencies
- `cd backend && uv run pytest tests/test_links.py` - one test file
- `cd frontend && npm ci && npm test` - frontend tests

## Rules

- Python dependencies are managed with uv only: `uv add <pkg>`, never pip or requirements.txt
- Do not add a dependency (Python or npm) without asking
- Any API change starts with `openapi.yaml`, then backend, then `frontend/src/services`
- Schema changes go through an Alembic migration
- Never put IP addresses, target URLs, emails, passwords or tokens into logs, metrics or traces
- Commit after every meaningful step; documentation and code comments in English

## Documents

- `_docs/process.md` - how work is organized, the agent team and the task lifecycle. Read before starting any task
- `_docs/task-template.md` - the template every groomed issue follows
- Before writing tests, read `_docs/testing-guidelines.md`
- Roles: `_docs/team/pm.md`, `_docs/team/software-engineer.md`, `_docs/team/qa-engineer.md`
