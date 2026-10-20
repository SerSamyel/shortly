title: On-call agent: wake up on an alert, find the bug and open a fix PR
labels: groomed,observability,agents
---
## Goal

When an alert fires, a headless coding agent investigates with logs, traces and the code, reproduces the failure with a test and opens a pull request with the smallest fix.

## Acceptance criteria

- [ ] `on-call-agent/` contains a small webhook service that receives Grafana alert notifications and ignores `resolved` ones
- [ ] For a firing alert it starts one agent run (Claude Code headless) with the alert payload, `_docs/runbook.md` and read access to the repository, Loki and Tempo
- [ ] The agent's instructions live in `.claude/agents/on-call.md`: reproduce with a failing test, make the smallest fix, run unit tests, open a PR referencing the alert; for a false positive, comment on a tracking issue instead
- [ ] The agent can never push to `main`, deploy, or touch production data; its GitHub token can only create branches and PRs
- [ ] Only one run per alert fingerprint at a time; repeated notifications for the same alert do not start new runs
- [ ] Each run's transcript is saved under `on-call-agent/runs/` (git-ignored)
- [ ] Demo, documented in README: a deliberate bug (redirect fails for aliases containing `-`) is deployed to dev, `RedirectErrorsHigh` fires, and the agent opens a PR that fixes it with a regression test

## Out of scope

- Escalation to a human and paging
- Running the agent in Kubernetes Jobs (can follow later)

## Constraints

- API keys and the GitHub token come from environment variables or secrets, never from the repository
