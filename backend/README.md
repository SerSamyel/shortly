# Shortly backend

FastAPI API and the click consumer. See the repository README for how to run everything.

```bash
uv sync
uv run uvicorn shortly.app:create_app --factory --reload  # API on http://localhost:8000 (SQLite by default)
uv run alembic upgrade head                     # apply migrations to DATABASE_URL
uv run shortly-consumer                         # click consumer (needs a Kafka/Redpanda broker)
uv run pytest                                   # unit tests
uv run pytest tests_integration                 # integration tests (needs Postgres and Redis)
```
