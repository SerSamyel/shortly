title: Fix vulnerable frontend dependencies reported by npm audit
labels: groomed,security,frontend
---
## Goal

`npm audit` reports no high or critical vulnerabilities for the frontend, and the production image keeps shipping only built static files.

## Acceptance criteria

- [ ] `docker run --rm -v "${PWD}/frontend:/app" -w /app node:22-alpine sh -c "npm ci && npm audit --audit-level=high"` exits with code 0
- [ ] `npm test` passes (14 tests or more) and `npx tsc -b` reports no errors
- [ ] `npm run build` succeeds and the app at http://localhost:8000 still logs in, creates a link and shows analytics
- [ ] `frontend/package-lock.json` is committed and the Dockerfile still uses `npm ci`
- [ ] The issue comment lists each advisory that was fixed and the package version that fixed it

## Out of scope

- Adding an automated audit step to CI (part of the CI issue)
- Upgrading React or React Router to new major versions unless an advisory requires it

## Constraints

- Change only `frontend/package.json` and `frontend/package-lock.json`
- Do not use `npm audit fix --force` blindly: a major upgrade needs a note in the issue explaining why
