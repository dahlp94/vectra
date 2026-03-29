# Billing Service — operations runbook

**Service:** `billing-service`  
**Tier:** Revenue-critical  
**Primary owner:** Billing Engineering  
**Escalation:** Billing on-call → Platform on-call → VP Engineering  

## Overview

The Billing Service calculates usage, applies entitlements, and emits invoices for Vectra tenants. It depends on **Postgres** (primary store), **Kafka** (usage events), and the **API Gateway** for synchronous reads. It does **not** process card data; payments go through the separate Payments Adapter.

## Health checks

| Check | Endpoint | Expected |
|-------|-----------|----------|
| Liveness | `GET /internal/health/live` | 200, body `{"status":"ok"}` |
| Readiness | `GET /internal/health/ready` | 200 only when DB + Kafka consumers are connected |

If readiness fails for **> 5 minutes**, page Billing on-call and open a bridge if customer impact is suspected.

## Key dashboards

- **Billing — revenue pipeline:** event lag, invoice job duration, error rate by tenant.
- **API Gateway — 5xx to billing routes:** correlate with gateway incidents (see INC-1042).
- **Postgres — billing shard:** replication lag, connection saturation.

## Common issues

### High Kafka consumer lag

1. Confirm no upstream producer outage (Usage Ingest team).
2. Check for poison messages in `billing.usage.v1` — use the **dead-letter replay** procedure (Billing wiki).
3. Scale consumer replicas only after confirming DB can handle write load; coordinate with Platform.

### Elevated 503 from API Gateway to Billing

- Often upstream **timeout** at gateway when Billing is slow. Check P99 latency and DB locks.
- If gateway shows widespread 503s across services, treat as **platform incident**, not Billing-only.

### Incorrect invoice amounts

1. Freeze manual adjustments; capture `tenant_id`, `invoice_id`, and `request_id`.
2. Compare against raw usage in the audit table (Billing tools — restricted).
3. Escalate to Billing + **Security** if fraud is suspected.

## Deployment and rollback

- Follow `policies/deployment_policy_v2.md` for change windows and approvals.
- Rollback: revert to previous Helm revision; run DB migration compatibility check before roll-forward again.

## Contacts

- **#billing-ops** — day-to-day questions  
- **#platform-incidents** — gateway or mesh-wide issues  
- **Security** — auth anomalies, scope changes affecting Billing routes  
