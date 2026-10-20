# Testing guidelines

## Layers

| Layer | Where | Runs against | Command |
| --- | --- | --- | --- |
| Backend unit | `backend/tests/` | In-memory SQLite, fake cache and fake publisher | `make test-backend` |
| Frontend unit | `frontend/src/**/*.test.tsx` | Mock services layer | `make test-frontend` |
| Integration | `backend/tests_integration/` | Real Postgres and Redis, in-process click consumer | `make test-integration` |
| End to end | `e2e/` | The full Docker Compose stack | `make e2e` |

## Rules

- Every acceptance criterion maps to at least one test; name tests after the behaviour
  (`test_expired_link_returns_410`), not after the function
- Unit tests never touch the network or a real database server
- Integration tests create their own data and do not depend on test order
- Test both the happy path and the error the user sees (status code and message)
- Do not mock what you are testing: fakes are for the boundaries (cache, broker, clock)
- A bug fix starts with a failing test that reproduces it
