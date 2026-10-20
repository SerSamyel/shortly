title: Alerts on user impact: failing redirects and a stalled click pipeline
labels: groomed,observability
---
## Goal

The team is notified when visitors cannot follow links or clicks stop reaching analytics, not when CPU is busy.

## Acceptance criteria

- [ ] Grafana alert `RedirectErrorsHigh`: more than 5% of redirects end with status `error` over 5 minutes, evaluated only when there were at least 20 redirects
- [ ] Grafana alert `ClickPipelineStalled`: consumer lag p95 above 120 seconds for 10 minutes, or click events published but none applied for 10 minutes
- [ ] Each alert carries labels/annotations: service, environment, version, owner, summary and a dashboard link
- [ ] Alerts are provisioned from files in `observability/`
- [ ] Alerts send to a webhook contact point whose URL comes from configuration (the on-call agent will listen there)
- [ ] `_docs/runbook.md` explains what each alert means and the first three things to check
- [ ] A documented manual test (stop the consumer for 10 minutes) fires `ClickPipelineStalled` and the alert resolves after restart

## Out of scope

- The on-call agent itself (next issue)
- Paging people (email, Telegram)

## Constraints

- Thresholds live in one place and are explained in the runbook
