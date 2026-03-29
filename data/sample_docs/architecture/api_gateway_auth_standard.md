# API Gateway authentication standard

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
