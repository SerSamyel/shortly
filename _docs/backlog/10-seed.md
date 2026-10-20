title: Seed command with a demo user, links and clicks
labels: groomed,backend
---
## Goal

Reviewers and developers can fill an empty database with realistic demo data in one command.

## Acceptance criteria

- [ ] `uv run shortly-seed` creates user `demo@example.com` with password from `SEED_PASSWORD` (default `demo-password` only when `ENVIRONMENT=local`)
- [ ] It creates 3 links (one with an alias, one expiring in 7 days, one disabled) and 30 days of synthetic clicks with several referrers and countries
- [ ] Running it twice does not create duplicates or double the clicks
- [ ] It refuses to run when `ENVIRONMENT=prod`
- [ ] `docker compose run --rm app shortly-seed` works, and README mentions it
- [ ] A unit test covers idempotency and the prod guard

## Out of scope

- Seeding through the public API

## Constraints

- Reuse `shortly.aggregation.apply_click` so seeded clicks follow the same path as real ones
