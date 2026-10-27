# Spec: Bharat ARP Collections Control Tower

**Status:** Approved for implementation on 2026-09-30. Implementation must
follow the capability map and task gates in `tasks/plan.md` and `tasks/todo.md`.

## Objective

Bharat ARP helps Indian B2B distributors and light manufacturers using
ERPNext recover overdue cash without replacing their ERP or requiring a new
accounting system.

The first product is a collections control tower. It groups receivables by
Customer Account, calculates verified Outstanding Balance, ranks accounts that
deserve attention, explains the evidence, prepares an approval-ready next
action, records Promises to Pay, and measures whether the action led to payment.

### Initial Ideal Customer Profile

- Indian B2B distributor or light manufacturer
- ERPNext is the primary source system, with CSV export as a fallback
- 20-200 active credit Customer Accounts
- At least INR 25 lakh of outstanding receivables in the pilot scope
- One owner, finance manager, or credit controller reviews collections weekly
- Meaningful 15-90 day payment terms and recurring partial payments, disputes,
  or broken Promises to Pay

### Validation Product Mode

The validation MVP is a single-tenant, single-operator local deployment. One
deployment maps to one Legal Entity, requires an explicit configured operator,
and has no hosted authentication or external side effects. This is a deliberate
pilot constraint, not the production authorization model. The hosted multi-user
roles and authorization matrix are specified in
`docs/authorization-matrix.md` and are a post-validation gate.

### Core Job To Be Done

> Every week, tell the finance lead which overdue Customer Accounts are most
> worth pursuing now, why, what evidence supports that recommendation, and
> whether the promised payment arrived.

## Product Positioning

### Buyer-facing statement

> Bharat ARP helps ERPNext-based Indian distributors and manufacturers collect
> overdue B2B cash. It ranks the accounts most worth pursuing, explains the
> reason, prepares approval-ready follow-up actions, records Promises to Pay,
> and shows which actions resulted in payment.

### What it is not

- Not an ERP or accounting ledger
- Not a GST, tax, or legal-advice product
- Not a debt-collection agency
- Not a payment initiator
- Not an Account Aggregator
- Not an autonomous agent with authority to change financial records

## Phase 1 Product Scope: Validation MVP

The validation MVP is local/self-hosted and CSV-first. It proves the workflow
and economic value before live provider integrations.

### In scope

1. Import customers, contacts, invoices, payments, payment allocations, credit
   notes, disputes, and known contact metadata from the versioned contract in
   `docs/csv-contract.md`.
2. Preserve source identifiers, observed-at timestamps, import batch identity,
   and row-level validation errors.
3. Calculate Outstanding Balance and flag duplicate, stale, incomplete, and
   inconsistent records instead of silently guessing.
4. Aggregate exposure by Customer Account rather than treating invoices in
   isolation.
5. Create explainable Collection Cases for overdue exposure.
6. Rank cases using a transparent, versioned heuristic with configurable
   weights and hard disqualifiers.
7. Propose one of a small set of bounded actions:
   - review payment allocation;
   - request missing evidence or resolve a dispute;
   - prepare an approved customer follow-up;
   - record or review a Promise to Pay;
   - escalate internally for credit review.
8. Record approval, rejection, edit, and reason for every proposal.
9. Record contact outcome and Promise-to-Pay status without requiring a live
   messaging provider.
10. Link later imported payments to cases and report recovered cash, ageing,
    broken promises, and data-quality exceptions.

### Out of scope

- Live ERPNext writes or direct ERPNext database access
- GSTN, e-invoice, e-waybill, UPI, bank, ONDC, or Account Aggregator APIs
- Automatic outbound WhatsApp, SMS, or email
- Payment initiation or credit-limit changes
- Legal notices, interest calculations for claims, or MSMED filing
- LLM-generated decisions, autonomous tool use, or unrestricted chat
- Multiple ERP connectors

## Functional Requirements

### FR-1: Source integrity

Every imported record must have `tenant_id`, `source_system`,
`source_record_id`, `observed_at`, and `import_batch_id`. Re-importing the same
source record must be idempotent and must not create duplicate financial facts.

### FR-2: Reconciliation before decisioning

The system must not rank an account with an unresolved balance calculation,
ambiguous customer identity, unsupported currency, or failed payment
allocation. It must surface the exception and provide a deterministic reason.
The normative balance formula and correction semantics are in
`docs/csv-contract.md`.

### FR-3: Account-level prioritization

The default queue ranks Customer Accounts using explainable inputs: verified
Outstanding Balance, overdue-age bucket, broken Promise to Pay, unresolved
dispute state, historical payment behaviour, contact eligibility, and total
exposure. Any unavailable or stale input is explicitly listed in the proposal.
The exact weights are a pilot hypothesis, stored as a Policy Version, and
cannot be changed retroactively for an existing proposal.

### FR-4: Safe proposals

Every Collection Proposal must include source references, evidence fields,
policy version, expected outcome, risk flags, suggested owner, and whether
approval is required. No proposal may directly execute a side effect.

### FR-5: Communication eligibility

The product must never infer Communication Eligibility from a phone number or
email address alone. `unknown`, `stale`, `conflicting`, `denied`, and `opted_out`
states cannot produce a customer-contact proposal. `unknown` may produce only a
`review_required` or evidence-request proposal. Only an authorized future role
may resolve `unknown` to `eligible`; ordinary approval cannot override denied
or opted-out states. See `docs/lifecycles.md`.

### FR-6: Approval controls

In validation mode approval is operator-scoped and records the configured actor;
there is no execution side effect. In hosted mode approval must be
action-specific, tenant-scoped, auditable, role-checked, segregated from
proposal creation where required, and stale when material evidence changes.
The system must support rejection with reason and prevent duplicate execution
through an idempotency key when connectors are later enabled.

### FR-7: Promise-to-pay lifecycle

The system must support proposed, accepted, fulfilled, broken, cancelled, and
unknown states. A Promise to Pay must preserve amount, expected date, source,
recorded-by user, and timestamps.

### FR-8: Outcome attribution

Reports must distinguish observed payment after an action from causal proof.
The MVP follows `docs/measurement-protocol.md` for baseline, cohort, window,
in-flight payment, partial payment, and language rules. It must not claim that a
message or proposal caused payment without an explicitly designed experiment.

### FR-9: Data minimization

Contact details and financial records are tenant-scoped data. The MVP must
support export and deletion of tenant data, define retention for imported raw
payloads and audit records, and exclude PII from logs and telemetry.
`docs/data-lifecycle.md` defines active-retention audit behavior, redaction,
tombstones, legal holds, and pilot defaults.

### FR-10: Pilot interface

The validation MVP must provide the CLI/report capabilities in
`docs/pilot-interface.md`: import, ranked queue, case inspection, proposal
decision, Promise-to-Pay recording, outcome recording, metrics, export, and
purge. Each command is tenant-explicit and audited.

## Non-Functional Requirements

- Reproducible local setup from a clean Python environment
- Unit tests for decisioning, reconciliation, lifecycle transitions, and
  permission states; integration tests for import idempotency, tenant scope,
  export, and purge
- No network access required for the validation MVP
- CLI/report flow can complete import, decision, promise, outcome, export, and
  purge for a fixture tenant
- Deterministic decisions for identical input, policy version, and date
- All externally sourced values treated as untrusted input
- No secrets in fixtures, tests, logs, or repository history
- Documentation must distinguish open-source core from provider-dependent
  adapters and third-party licensing

## Technical Direction

### Phase 1

- Python package with pure domain logic
- CSV import command and local SQLite persistence only when persistence is
  required by the vertical slice
- Standard-library-first policy logic; add dependencies only with a documented
  reason and license review
- No FastAPI, Temporal, LangGraph, Postgres, vector database, or messaging SDK
  until a user-facing requirement and verification test justifies it

### Phase 2, after paid validation

- ERPNext API/export connector with provenance and retry-safe sync
- Web application/API with explicit authentication, authorization, CSRF,
  security headers, rate limits, pagination, and tenant isolation
- PostgreSQL for hosted multi-tenant persistence if the measured workload needs
  it; SQLite remains a supported local mode if practical
- Durable workflow engine only for long-running approvals/retries that cannot
  be represented safely as persisted state transitions
- LLM assistance only for evidence-grounded summarization and draft text;
  policy code remains authoritative and model output is schema-validated

## Open-Source and Business Model

The core domain model, CSV importer, policy engine, audit format, and test
fixtures remain Apache-2.0 open source. Provider adapters may be separate
packages with their own terms and must not be required by the core.

Potential paid offerings after validation:

- managed hosting and backups
- ERPNext onboarding and connector support
- policy configuration and implementation-partner services
- security, support, and data-residency options

Initial pricing is a hypothesis, not a promise: test paid pilots around INR
10,000-20,000 setup plus INR 2,000-5,000 monthly for one legal entity. Do not
price on AI calls, invoice count, or WhatsApp message volume until customer
value and provider costs are understood.

## Success Criteria

The validation MVP is successful only if all are true:

- Three qualified companies pay for a 60-90 day pilot.
- Each pilot has at least INR 25 lakh of in-scope receivables and a baseline for
  30+, 60+, and 90+ day ageing.
- At least 95% of source rows are reconciled or explicitly classified, at least
  80% of in-scope INR exposure is decision-eligible, and the priority cohort's
  exposure coverage is reported separately. Classification alone is not a
  success outcome.
- A finance lead uses the queue weekly for at least six consecutive weeks.
- At least 80% of high-priority cases receive a documented next action within
  one business day.
- Payment outcomes and broken Promises to Pay are recorded for the priority
  cohort.
- At least one ERPNext partner agrees to trial implementation or resale.
- Finance review time falls by at least 25% versus baseline, or the customer
  documents an equivalent operational benefit; overdue priority exposure
  improves versus the agreed baseline; and the customer renews or pays for the
  next period. See `docs/measurement-protocol.md`.

### Guardrail metrics

- Zero cross-tenant data exposures
- Zero duplicate or unauthorized outbound actions
- Zero autonomous payment, tax, or legal actions
- Source reconciliation error rate visible and bounded
- Customer opt-out and complaint events recorded
- Proposal rejection and correction rates reported

## Research and Source Register

- SHAKE manifesto: https://shakegraph.com/manifesto
- ERPNext receivables and dunning: https://docs.frappe.io/erpnext/dunning
- ERPNext repository and license: https://github.com/frappe/erpnext
- India Compliance: https://github.com/resilient-tech/india-compliance
- Frappe partner channel: https://frappe.io/partners
- MSME Samadhaan delayed-payment information: https://samadhaan.msme.gov.in/
- RBI Account Aggregator Directions, 2025:
  https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12936
- WhatsApp Business policies and Cloud API documentation must be re-verified
  from official Meta sources immediately before any messaging adapter work.

## Assumptions Requiring Validation

1. ERPNext-based B2B distributors and light manufacturers have enough overdue
   exposure to pay for a separate collections workflow.
2. Account-level prioritization and Promise-to-Pay tracking are more valuable
   than ordinary reminders already present in ERPNext and competing products.
3. Finance leads will provide payment allocation and contact evidence, or pay
   for data-cleaning assistance.
4. ERPNext partners can provide distribution and implementation leverage.
5. A CSV-first workflow can demonstrate value before live integrations.
6. One Legal Entity per validation deployment is sufficient for pilot use.
7. The first pilot requires only INR and Asia/Kolkata business dates.

## Approval Gate

The human owner must approve this specification, the capability map, and
`tasks/plan.md` before implementation proceeds beyond documentation. Any
change to ICP, source-of-record boundary, financial side-effect permissions,
or compliance scope requires a spec update first.
