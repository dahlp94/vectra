# Incident INC-1042 — API Gateway timeouts affecting Billing reads

**Severity:** SEV-2  
**Status:** Resolved  
**Opened:** 2026-03-10 14:08 UTC  
**Closed:** 2026-03-10 18:42 UTC  
**Commander:** Platform SRE  
**Participants:** Platform, Billing, Security (observer)  

## Summary

A configuration change to upstream timeout budgets on the **Vectra API Gateway** caused synchronous reads to the **Billing Service** to exceed the gateway’s client-facing timeout. Customers saw intermittent **503** responses and slow invoice views. No data loss occurred; Postgres and Billing batch jobs remained healthy.

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
