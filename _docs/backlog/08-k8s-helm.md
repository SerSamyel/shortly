title: Helm chart and k3s on a VPS with dev and prod namespaces
labels: groomed,deploy
---
## Goal

The app runs on a single VPS in k3s, packaged as a Helm chart, with independent `dev` and `prod` environments reachable over HTTPS.

## Acceptance criteria

- [ ] `deploy/helm/shortly` chart with templates for the API, the consumer, a migration Job (Helm hook) and an Ingress
- [ ] Postgres, Redis and Redpanda run per namespace (subchart or plain manifests), with persistent volumes for Postgres and Redpanda
- [ ] `values-dev.yaml` and `values-prod.yaml` differ only in host names, replica counts, resources and secrets references
- [ ] Secrets (JWT secret, database password) are Kubernetes Secrets created outside the chart and referenced by name
- [ ] Liveness and readiness probes use `/health`; the consumer has no HTTP probe
- [ ] `helm lint` passes and `helm template` renders without errors in CI
- [ ] Both environments answer over HTTPS (cert-manager + Let's Encrypt, or a documented alternative) at the URLs listed in README
- [ ] `_docs/deploy.md` lists every manual step to prepare the VPS (k3s install, cert-manager, namespaces, secrets)

## Out of scope

- Automated deploys (CD issue)
- Managed databases and backups (documented as next steps)

## Constraints

- VPS: at least 4 vCPU / 8 GB RAM
- Image from GHCR; the chart takes the tag as a value
