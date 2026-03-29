# Deployment policy (v2)

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

- **Default:** Tuesday–Thursday, **10:00–16:00** tenant-local “low traffic” window for the affected region (see SRE calendar).
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
