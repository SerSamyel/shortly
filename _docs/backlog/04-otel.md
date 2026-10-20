title: Instrument the redirect journey with OpenTelemetry (traces, metrics, logs with trace ids)
labels: groomed,observability
---
## Goal

A single click can be followed from the redirect request through Redpanda to the consumer's database write as one trace, with metrics and logs that share its trace id.

## Acceptance criteria

- [ ] API and consumer use the OpenTelemetry SDK and export over OTLP to `OTEL_EXPORTER_OTLP_ENDPOINT`; with the variable unset, the app runs and exports nothing
- [ ] Resource attributes on all signals: `service.name` (`shortly-api` / `shortly-consumer`), `deployment.environment`, `service.version`
- [ ] FastAPI, SQLAlchemy and Redis calls produce spans automatically
- [ ] The click event carries W3C trace context in Kafka message headers; the consumer continues that trace, so redirect and aggregation spans share one trace id
- [ ] Every JSON log line written while handling a request or a message has `trace_id` and `span_id`
- [ ] Metrics from `_docs/plan.md` section 10 exist: `redirects_total{status}`, `redirect_duration_seconds`, `redirect_cache_total{result}`, `click_events_published_total{result}`, `click_consumer_lag_seconds`, `links_created_total{result}`
- [ ] A unit test asserts that no span attribute, metric label or log field contains an IP address, a target URL, an email or a token (checked against a request with known values)
- [ ] Unit and integration tests still pass

## Out of scope

- Running Prometheus, Loki, Tempo and Grafana (next issue)
- Alerts

## Constraints

- Links are referenced only by `link_id` in telemetry
- Disable span attributes that record full URLs or client addresses (`http.url`, `client.address`, `net.peer.ip` and equivalents)
