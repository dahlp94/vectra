#!/usr/bin/env python3
"""
Create sample document directories and files under data/sample_docs/.

Run from repository root:
    python scripts/seed_sample_docs.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ROOT = ROOT / "data" / "sample_docs"

# Deterministic contents; mirrors the committed sample_docs files.
DOCUMENTS: dict[str, str] = {
    "architecture/api_gateway_auth_standard.md": """# API Gateway authentication standard

**Status:** Approved  
**Owner:** Platform Engineering  
**Reviewers:** Security, SRE  
**Last updated:** 2026-03-15  

## Purpose

This document defines how the Vectra API Gateway authenticates and authorizes traffic for customer-facing and internal APIs. All services behind the gateway MUST comply with these rules unless explicitly exempted by Security.

## Scope

Applies to:

- Public REST APIs (`api.vectra.example`)
- Partner BFF routes
- Internal admin APIs exposed via the gateway (not direct VPC calls)

Does not apply to batch jobs or control-plane workers that do not traverse the gateway.

## Identity and tokens

### Customer traffic

- **Protocol:** OAuth 2.0 Authorization Code with PKCE for interactive clients; client credentials for trusted backends.
- **Token format:** JWT signed with the Vectra IdP (`kid` rotated per `docs/security/jwks_rotation.md`).
- **Validation:** API Gateway validates `iss`, `aud`, `exp`, and `nbf`. Clock skew tolerance is **60 seconds**.
- **User context:** Downstream services receive `X-Vectra-Subject`, `X-Vectra-Tenant-Id`, and `X-Vectra-Scopes` headers injected by the gateway after successful validation.

### Service-to-service

- **Preferred:** mTLS between mesh sidecars for east-west traffic.
- **Gateway path:** If a service must call through the gateway, use **OAuth2 client credentials** with audience restricted to the target API resource identifier (e.g., `billing-api`).

## Rate limiting and abuse controls

- Per-tenant token bucket limits are enforced at the edge (default documented in the **Edge configuration runbook**).
- Anonymous routes (health, JWKS) are on a separate rate-limit class with stricter IP-based throttling.
- Security may enable temporary geo blocks during incidents; Platform coordinates with Comms.

## Error handling

- **401:** Missing or invalid token. Clients MUST NOT retry without refreshing credentials.
- **403:** Valid token but insufficient scope. Logged with `request_id` for Billing and Platform dashboards.

## Compliance and audit

- Access logs are shipped to the central SIEM with **90-day** retention for gateway decisions.
- Changes to authentication policies require a **Security** review and a deployment window per `policies/deployment_policy_v2.md`.

## References

- Billing Service API contract: `architecture/billing_public_api_overview.md` (pending)
- Incident INC-1042 postmortem: `incidents/incident_inc_1042.md`
""",
    "runbooks/billing_service_runbook.md": """# Billing Service — operations runbook

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
""",
    "incidents/incident_inc_1042.md": """# Incident INC-1042 — API Gateway timeouts affecting Billing reads

**Severity:** SEV-2  
**Status:** Resolved  
**Opened:** 2026-03-10 14:08 UTC  
**Closed:** 2026-03-10 18:42 UTC  
**Commander:** Platform SRE  
**Participants:** Platform, Billing, Security (observer)  

## Summary

A configuration change to upstream timeout budgets on the **Vectra API Gateway** caused synchronous reads to the **Billing Service** to exceed the gateway\u2019s client-facing timeout. Customers saw intermittent **503** responses and slow invoice views. No data loss occurred; Postgres and Billing batch jobs remained healthy.

## Customer impact

- **~12%** of Billing API requests failed or retried during the window.
- Peak error rate **09:00–11:00 US/Eastern** aligned with billing dashboard traffic.

## Timeline (UTC)

| Time | Event |
|------|--------|
| 14:08 | Automated canary on gateway pool `gw-prod-us-east-1b` reports elevated latency |
| 14:22 | Billing on-call notices spike in `billing.read` 503s |
| 14:35 | Incident declared; traffic shifted away from affected pool |
| 15:10 | Root cause identified: reduced `upstream_connect_timeout` vs Billing P99 |
| 16:05 | Hotfix: timeout aligned with `architecture/api_gateway_auth_standard.md` budgets + Billing SLO |
| 18:42 | Monitoring green for **45 minutes**; incident closed |

## Root cause

A deployment intended to harden connection behavior lowered the upstream connect timeout below the latency profile of Billing under load (DB contention during month-end reconciliation). The **API Gateway** closed connections before Billing responded, surfacing as **503** to clients.

## Mitigation

- Rolled back the aggressive timeout; restored previous values per approved change.
- Added a **dashboard alert** when Billing P99 within the gateway path exceeds **80%** of the configured upstream timeout.

## Follow-up actions

| Action | Owner | Due |
|--------|--------|-----|
| Document gateway timeout floor vs service SLOs | Platform | 2026-03-24 |
| Billing: reduce tail latency on `/v1/invoices` hot path | Billing | 2026-04-05 |
| Run joint failure drill (gateway + Billing) | SRE | Q2 |

## Lessons learned

- Treat gateway and critical-path services (**Billing**, Auth) as a **single blast radius** for timeout changes.
- **Security** review was not required for this parameter, but Platform will add a checklist item for any edge timing change affecting authenticated routes.
""",
    "policies/deployment_policy_v2.md": """# Deployment policy (v2)

**Applies to:** Production and staging systems for the Vectra SaaS platform  
**Owners:** Platform Engineering + SRE  
**Effective:** 2026-03-01  

## Objectives

- Minimize customer-facing risk during releases.
- Ensure **Security** and dependent teams have visibility for sensitive changes.
- Keep rollback paths clear and testable.

## Change classes

| Class | Examples | Approval |
|-------|-----------|----------|
| **Standard** | Bugfix, feature behind flag, doc-only | Team lead + automated checks |
| **Elevated** | API Gateway routing, auth config, Billing pricing paths | Platform + peer review + change window |
| **Emergency** | Active incident mitigation | Incident commander may waive window; post-review within 24h |

## Windows

- **Default:** Tuesday–Thursday, **10:00–16:00** tenant-local \u201clow traffic\u201d window for the affected region (see SRE calendar).
- **Blackout:** Month-end close for **Billing**-adjacent services unless exec-approved.

## Requirements

1. **Roll-forward plan** and **rollback plan** documented in the change ticket.
2. Feature flags preferred over long-lived branches; flag state must be observable in dashboards.
3. Database migrations: backward-compatible deploys only; expand/contract pattern for breaking schema changes.
4. **API Gateway** changes that touch authentication MUST follow `architecture/api_gateway_auth_standard.md` and include **Security** sign-off.

## Verification

- Smoke tests for critical paths: login, Billing read-only summary, core data API sample query.
- Canary or progressive rollout mandatory for **Elevated** changes.

## Exceptions

Emergency fixes during incidents are logged in the incident record (e.g., **INC-1042**). Permanent policy changes still require an update to this document.

## References

- Billing operations: `runbooks/billing_service_runbook.md`
- Gateway incident example: `incidents/incident_inc_1042.md`
""",
}


def main() -> None:
    for relative, content in DOCUMENTS.items():
        path = SAMPLE_ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
