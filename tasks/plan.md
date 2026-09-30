# Implementation Plan: Bharat ARP Validation MVP

## Overview

Build a CSV-first, deterministic collections control tower that can prove or
disprove the narrow ICP and value proposition before live integrations or AI.
The plan follows the capability map in `CAPABILITY-MAP.md` and the behavioral
contract in `SPEC.md`.

## Architecture Decisions

- Keep ERPNext or the imported source as the system of record; Bharat ARP owns
  only decision and workflow state.
- Use source provenance and idempotent imports before any decisioning.
- Rank Customer Accounts, not isolated invoices.
- Make every proposal explainable, versioned, and non-mutating.
- Treat communication eligibility as a domain fact, not a phone-number check.
- Keep the validation product offline-capable and provider-independent.
- Defer FastAPI, PostgreSQL, Temporal, LangGraph, vector search, GST, UPI,
  banking, ONDC, and messaging SDKs until a later gate justifies them.

## Dependency Graph

```text
tenant-audit
    |
source-ingestion
    |
receivables-model
    |
collections-decisioning ---- promise-to-pay
             |                    |
             +-------- approval-actions
                              |
                       outcome-measurement
                              |
                           connectors
```

## Task List

Tasks 1-15 have an executable offline slice. The core import, decisioning,
workflow, persistence, queue report, and synthetic demo paths are verified;
the full measurement-protocol and legal-hold retention extensions remain
explicit follow-up work. Tasks 16-18 are the business validation and
integration gate; they require real pilot evidence and must not be replaced by
more prototype integrations.

### Phase 0: Specification and Domain Foundation

- [x] Task 1: Approve the capability map and product specification
- [x] Task 2: Quarantine the existing phone-based policy prototype and replace its
  unsafe channel assumption with explicit Communication Eligibility states
- [x] Task 3: Replace the thin invoice vocabulary with the domain glossary and
  normalized entity contract
- [x] Task 4: Approve the versioned CSV contract, balance formula, and golden
  fixtures
- [x] Task 5: Define tenant, provenance, audit, retention, deletion, and
  data-classification invariants

### Checkpoint: Foundation

- The spec, capability map, and glossary agree on terminology.
- No implementation task has an unresolved side-effect or compliance boundary.
- A human owner approves the documents before Phase 1 implementation.

### Phase 1: CSV-First Evidence Pipeline

- [x] Task 6: Implement validated CSV import with row-level errors and provenance
- [x] Task 7: Implement idempotent normalization of customers, invoices, payments,
  allocations, credit notes, contacts, and disputes
- [x] Task 8: Implement unresolved-balance and data-quality exception reporting

### Checkpoint: Evidence

- Re-importing a fixture produces no duplicate financial facts.
- Paid, partially paid, credited, duplicate, ambiguous, and stale records are
  handled by tests.
- No account reaches the decision queue with an unresolved balance.

### Phase 2: Collections Decisioning

- [x] Task 9: Implement Customer Account aggregation and ageing cohorts
- [x] Task 10: Implement versioned, explainable priority ranking with explicit input
  availability and freshness
- [x] Task 11: Implement bounded Collection Proposals and evidence views

### Checkpoint: Decisioning

- A finance lead can inspect why the top cases are ranked.
- Identical input and policy version produce deterministic proposals.
- Disputes, unknown contact eligibility, and broken promises block unsafe
  communication proposals.

### Phase 3: Human Workflow and Outcomes

- [x] Task 12: Implement validation-mode approval, rejection, edit, and case state
  changes
- [x] Task 13: Implement Promise-to-Pay lifecycle and contact outcome recording
- [x] Task 14: Implement payment outcome linkage and pilot metrics using the
  measurement protocol
- [x] Task 15: Implement CLI/report interface, export, and tenant purge

  The current offline slice includes CLI commands, deterministic text/CSV/HTML
  queue reports, formula-safe audit export, and tenant purge. Full
  retention-policy enforcement, legal holds, tombstones, and metrics derived
  from weekly pilot snapshots remain follow-up work before production use.

### Checkpoint: Pilot Readiness

- A complete fixture can be imported, ranked, reviewed, approved/rejected,
  updated with a promise, and reconciled to a later payment.
- The audit trail explains who changed what, when, and under which policy.
- Guardrail metrics are visible.

### Phase 4: Validation and Integration Gate

- Task 16: Run a manual workflow with three qualified pilot candidates
- Task 17: Compare baseline and pilot outcome cohorts
- Task 18: Decide whether to build an ERPNext connector, hosted API, and
  multi-user authorization

### Checkpoint: Go / No-Go

- Go only if the success criteria in `SPEC.md` are met or a written reason
  justifies a revised hypothesis.
- No live messaging, payment, tax, or LLM integration is added merely because
  the core prototype works.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Existing ERP reminders are good enough | High | Sell prioritization and outcome closure; test paid pilots early |
| Source data is too dirty | High | Make exceptions first-class; do not silently infer balances; measure INR-weighted eligibility |
| Product creates an approval inbox | High | Measure action latency, batch review, and time saved |
| Wrong contact or unsafe channel | High | Explicit Communication Eligibility and human review |
| Cross-tenant leakage | Critical | Tenant-scoped identity at every repository/query boundary and tests |
| Duplicate future side effects | Critical | Approval state machine plus idempotency keys before connectors |
| Compliance scope expands uncontrollably | High | Defer GST, banking, AA, legal filing, and payment initiation |
| Provider terms change | Medium | Provider-neutral contracts and official-doc verification before adapter work |
| Open source does not convert to revenue | Medium | Paid founder-led pilots and ERPNext-partner validation |
| Attribution is overstated | High | Cohorts/baselines; avoid causal claims without experiment design |

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
python -m build
```

`python -m build` becomes mandatory after build tooling is added. Until then,
the package install and test command in `README.md` are the baseline checks.

## Resolved Phase-0 Constraints

- The first pilot contract is `docs/csv-contract.md`.
- One validation deployment maps to one Legal Entity and supports INR only.
- The validation interface is CLI plus generated CSV/HTML reports.
- The configured pilot operator is the only approval actor in validation mode;
  hosted role authorization is a later gate.

## Open Questions for Pilot Agreements

- What customer-specific retention or legal hold overrides apply?
- Which channel, if any, has documented customer permission in the pilot?
- Which ERPNext export mapping is needed to conform to the versioned contract?
