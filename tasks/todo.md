# Bharat ARP Task List

Tasks are ordered by dependency. Do not start implementation until the human
owner approves `SPEC.md`, `CAPABILITY-MAP.md`, and `tasks/plan.md`.

## Phase 0: Specification and Domain Foundation

- [x] Task 1: Approve the capability map and product specification
  - Acceptance: Human owner confirms ICP, scope, non-goals, success criteria,
    and side-effect boundaries in `SPEC.md`.
  - Verify: Review `CAPABILITY-MAP.md`, `SPEC.md`, and `tasks/plan.md` together.
  - Files: `CAPABILITY-MAP.md`, `SPEC.md`, `tasks/plan.md`

- [x] Task 2: Quarantine the unsafe phone-based policy and define
  Communication Eligibility
  - Acceptance: A phone number or email alone cannot produce a customer-contact
    proposal; unknown, denied, opted-out, stale, and eligible states have
    canonical behavior.
  - Verify: Regression tests cover each permission state.
  - Files: `bharat_arp/receivables.py`, `tests/test_receivables.py`,
    `docs/lifecycles.md`

- [x] Task 3: Replace the thin invoice vocabulary with the normalized entity
  contract
  - Acceptance: Domain terms are defined once; source facts are distinct from
    workflow facts and all required entities are listed.
  - Verify: Domain-model review finds no ambiguous use of “account”, “payment”,
    or “agent action”.
  - Files: `CONTEXT.md`, `docs/architecture.md`

- [x] Task 4: Approve the versioned CSV contract, balance formula, and golden
  fixtures
  - Acceptance: File set, identity, decimal/currency rules, allocation rules,
    corrections, and expected fixture balances are approved.
  - Verify: Review `docs/csv-contract.md` with paid, partial, credit,
    overpayment, duplicate, cancelled, and unresolved examples.
  - Files: `docs/csv-contract.md`, `SPEC.md`

- [x] Task 5: Define tenant, provenance, audit, retention, deletion, and
  data-classification invariants
  - Acceptance: Single-tenant validation mode and future hosted mode are
    explicit; audit redaction, legal hold, export, purge, and maintainer access
    rules are defined.
  - Verify: Security review maps every trust boundary and abuse case.
  - Files: `SPEC.md`, `docs/data-lifecycle.md`, `docs/authorization-matrix.md`

## Checkpoint: Foundation

- [x] Human approval recorded before implementation continues
- [x] Terminology and scope are internally consistent
- [x] No live external integration is required for Phase 1

## Phase 1: CSV-First Evidence Pipeline

- [x] Task 6: Implement validated CSV import with row-level errors and provenance
  - Acceptance: The seven-file contract is validated for encoding, headers,
    limits, common provenance, required fields, and redacted row errors.
  - Verify: Import clean, malformed, oversized, formula-bearing, duplicate,
    and mismatched-tenant fixtures without network access.
  - Files: `bharat_arp/importing.py`, `bharat_arp/contracts.py`,
    `tests/test_importing.py`

- [x] Task 7: Implement idempotent normalization of customers, invoices,
  payments, payment allocations, credit notes, contacts, and disputes
  - Acceptance: The documented identity key, corrected source versions,
    explicit voids, and partial batch acceptance rules are enforced.
  - Verify: Replay identical batches, corrected rows, overlapping batches, and
    failed retries; assert no duplicate financial facts.
  - Files: `bharat_arp/normalization.py`, `bharat_arp/models.py`,
    `tests/test_normalization.py`

- [x] Task 8: Implement unresolved-balance and data-quality exception reporting
  - Acceptance: INR decimal arithmetic calculates gross due, valid allocations,
    outstanding balance, overpayment, and unresolved states without guessing.
  - Verify: Golden fixtures cover paid, partial, credit note, overpayment,
    cancellation, duplicate, stale, ambiguous, and unsupported records.
  - Files: `bharat_arp/reconciliation.py`, `tests/test_reconciliation.py`,
    `tests/fixtures/`

## Checkpoint: Evidence

- [x] Clean, duplicate, ambiguous, partial-payment, credit-note, stale, and
  already-paid fixtures pass
- [x] Re-import is idempotent
- [x] No unresolved balance enters decisioning

## Phase 2: Collections Decisioning

- [x] Task 9: Implement Customer Account aggregation and ageing cohorts
  - Acceptance: Eligible invoices aggregate by Customer Account and produce
    30+, 60+, and 90+ day cohorts as of a supplied Asia/Kolkata date.
  - Verify: Test multiple invoices, partial payments, one customer with several
    cases, and ineligible accounts.
  - Files: `bharat_arp/collections.py`, `tests/test_collections.py`

- [x] Task 10: Implement versioned, explainable priority ranking with input
  availability and freshness
  - Acceptance: Ranking is deterministic, stores Policy Version, exposes each
    input/value/availability state, and excludes unresolved exposure.
  - Verify: Same inputs produce the same order; changed policy versions produce
    distinct evidence; stale and missing inputs are visible.
  - Files: `bharat_arp/decisioning.py`, `tests/test_decisioning.py`

- [x] Task 11: Implement bounded Collection Proposals and evidence views
  - Acceptance: Proposals contain source references, risk flags, expected
    outcome, suggested owner, and no executable side effect.
  - Verify: Open disputes and unknown/stale/denied Communication Eligibility
    produce review-only proposals; eligible contact data produces draft-only
    proposals.
  - Files: `bharat_arp/proposals.py`, `bharat_arp/receivables.py`,
    `tests/test_proposals.py`

## Checkpoint: Decisioning

- [x] Top cases are explainable and deterministic
- [x] Disputes and unknown Communication Eligibility prevent unsafe proposals
- [x] Proposal policy versions are immutable

## Phase 3: Human Workflow and Outcomes

- [x] Task 12: Implement validation-mode approval, rejection, edit, and case
  state changes
  - Acceptance: The lifecycle transitions in `docs/lifecycles.md` are enforced
    and every mutation records the configured operator and audit event.
  - Verify: Invalid transitions, duplicate decisions, and stale proposals fail
    without mutation.
  - Files: `bharat_arp/workflow.py`, `bharat_arp/audit.py`,
    `tests/test_workflow.py`

- [x] Task 13: Implement Promise-to-Pay lifecycle and contact outcome recording
  - Acceptance: Promise states, amount/date/source, partial fulfillment, broken
    promises, and cancellation reasons follow the lifecycle contract.
  - Verify: Test early payment, partial payment, late payment, cancellation,
    rejection, and payment without a proposal.
  - Files: `bharat_arp/promises.py`, `bharat_arp/outcomes.py`,
    `tests/test_promises.py`

- [x] Task 14: Implement payment outcome linkage and pilot metrics
  - Acceptance: Metrics follow `docs/measurement-protocol.md` and distinguish
    observed-after from causal claims, with account and INR coverage reported.
  - Verify: Fixture reports cover baseline, priority/non-priority cohorts,
    in-flight payments, ageing, action latency, and broken promises.
  - Files: `bharat_arp/metrics.py`, `tests/test_metrics.py`,
    `docs/measurement-protocol.md`

- [x] Task 15: Implement CLI/report interface, export, and tenant purge
  - Acceptance: Import, queue, case inspection, decision, promise, outcome,
    metrics, export, and purge capabilities work for one fixture tenant.
  - Verify: Run the documented pilot commands end to end; assert exports are
    complete, formula-neutralized, and purge follows retention/legal-hold rules.
  - Files: `bharat_arp/cli.py`, `bharat_arp/reports.py`,
    `tests/test_cli.py`, `tests/test_lifecycle.py`

## Checkpoint: Pilot Readiness

- [x] Full fixture flow passes from import through payment outcome
- [x] Audit trail and guardrail metrics are visible
- [x] No external side effect is possible without an approved contract

## Offline MVP Follow-ups Before Pilot Use

- [x] Extend metrics from persisted source/workflow facts to full weekly
  baseline, priority/non-priority cohort, ageing, and payment-attribution
  snapshots.
- [x] Implement retention-policy enforcement, legal holds, purge tombstones,
  and complete derived-record export semantics.
- [x] Add remaining lifecycle operations for assignment, proposal edits,
  rejection reasons, and partial Promise-to-Pay fulfilment.

## Phase 4: Validation and Integration Gate

- [ ] Task 16: Run a manual workflow with three qualified pilot candidates
  - Acceptance: Three candidates meet the ICP, pay the pilot fee, provide the
    agreed baseline, and complete the local import workflow.
  - Verify: Signed pilot checklist and recorded baseline data for each tenant.
  - Files: `docs/pilot-interface.md`, `docs/measurement-protocol.md`

- [ ] Task 17: Compare baseline and pilot outcome cohorts
  - Acceptance: Each pilot has weekly snapshots, priority/non-priority cohorts,
    in-flight payment handling, and an exit decision against the thresholds.
  - Verify: Review reports with the customer and record renewal/no-go evidence.
  - Files: `docs/measurement-protocol.md`, `docs/pilot-results-template.md`

- [ ] Task 18: Decide whether to build an ERPNext connector, hosted API, and
  multi-user authorization
  - Acceptance: A written go/no-go decision cites paid pilots, outcome metrics,
    data-quality coverage, partner evidence, and unresolved risks.
  - Verify: No connector or hosted auth work begins without a positive decision
    and updated `SPEC.md`.
  - Files: `SPEC.md`, `tasks/plan.md`, `docs/adr/`

## Checkpoint: Go / No-Go

- [ ] Paid pilot and usage criteria from `SPEC.md` are evaluated
- [ ] Any changed hypothesis is written back into `SPEC.md`
- [ ] Integration work is not started without a positive gate decision
