title: Observability stack and dashboard: Collector, Prometheus, Loki, Tempo, Grafana
labels: groomed,observability
---
## Goal

Telemetry from the app is collected, stored and viewable in Grafana, with a dashboard for the redirect journey and a jump from a log line to its trace.

## Acceptance criteria

- [ ] `observability/compose.yaml` runs OTel Collector, Prometheus, Loki, Tempo and Grafana as a separate Compose project; `make obs-up` starts it
- [ ] With both stacks running, the app exports to the collector and data appears in all three stores
- [ ] Grafana is provisioned from files (datasources and dashboards), no manual clicking
- [ ] Dashboard "Shortly / Redirects" shows: redirects per minute by status, redirect p95 latency, cache hit ratio, click events published vs failed, consumer lag p95, links created; filterable by `environment` and `version`
- [ ] Clicking a trace id in a Loki log line opens the trace in Tempo
- [ ] README has a screenshot of the dashboard and the steps to open it

## Out of scope

- Alert rules (next issue)
- Deploying the stack to the server

## Constraints

- Grafana admin password comes from an environment variable, not from the repository
- Pin image versions
