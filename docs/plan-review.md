# Plan Review: Bharat ARP

## Verdict

The original plan had a sound architectural thesis but was too broad to be a
credible product plan. It moved too quickly from “agentic ERP decision layer” to
ERPNext, GST, UPI, Temporal, LangGraph, PostgreSQL, and provider integrations
without validating a specific buyer problem.

The revised plan is narrower and intentionally less impressive on paper:

> A collections control tower for Indian B2B distributors and light
> manufacturers already using ERPNext.

It starts with CSVs and deterministic evidence-backed workflows, then earns
live integrations and AI only after paid validation.

## Findings and Corrections

### Review follow-up

The second review identified implementation blockers in the first revision.
They are resolved by making the validation mode explicitly single-tenant and
local, adding a versioned financial CSV contract, defining data lifecycle and
workflow state machines, specifying a CLI/report surface, and moving hosted
identity, authorization, and live integrations behind a paid-validation gate.

### Product

- **Finding:** “Indian SMBs” is not a usable initial customer segment.
- **Correction:** target ERPNext-based B2B distributors and light manufacturers
  with material credit receivables.
- **Finding:** overdue reminders are already available in ERPNext and adjacent
  products.
- **Correction:** compete on account-level prioritization, dispute/evidence
  handling, Promise-to-Pay tracking, and measured recovery outcomes.
- **Finding:** approval alone can become another inbox.
- **Correction:** the product must reduce inspection work, support a ranked
  queue, capture outcomes, and report whether promises were kept.

### Business

- **Finding:** open source is not itself a distribution strategy.
- **Correction:** validate through founder-led paid pilots and ERPNext partners;
  monetize hosting, onboarding, support, and configuration later.
- **Finding:** pricing and success metrics were previously implicit.
- **Correction:** treat pilot pricing as a hypothesis and measure recovered cash,
  ageing, action latency, and finance time saved rather than AI activity.

### Technical

- **Finding:** the proposed stack was too advanced for an unvalidated workflow.
- **Correction:** pure Python plus CSV fixtures first; defer FastAPI, Temporal,
  LangGraph, PostgreSQL, and vector search until justified by requirements.
- **Finding:** the initial `Invoice` model cannot support collection decisioning.
- **Correction:** model Customer Account, Outstanding Balance, Payment
  Allocation, disputes, contact eligibility, Promise to Pay, proposals,
  approvals, and outcomes.

- **Finding:** the existing prototype chose WhatsApp from phone presence and
  fell back to email without an email field.
- **Correction:** this behavior is explicitly quarantined as a pre-Phase-1
  task. Communication Eligibility has unknown, eligible, denied, opted-out,
  stale, and conflicting states with one canonical transition rule.

- **Finding:** outstanding balance, source correction, currency, allocation,
  and audit deletion semantics were underspecified.
- **Correction:** `docs/csv-contract.md` and `docs/data-lifecycle.md` are now
  normative inputs to implementation.

- **Finding:** the plan required a weekly queue but did not define an interface.
- **Correction:** the validation MVP is CLI plus generated CSV/HTML reports;
  hosted web UI is a post-validation decision.
- **Finding:** direct automation was implied before provenance and idempotency.
- **Correction:** every source record has provenance; every future side effect
  has approval and an idempotency key.

### Security and privacy

- **Finding:** a phone number is not evidence of WhatsApp permission or identity.
- **Correction:** Communication Eligibility is an explicit domain state; unknown
  means human review, not automatic contact.
- **Finding:** tenant isolation, retention, deletion, and role separation were
  named but not acceptance criteria.
- **Correction:** they are now functional/non-functional requirements and
  verification gates.
- **Finding:** bank and Account Aggregator ideas create unnecessary regulatory
  exposure early.
- **Correction:** no Account Aggregator, payment initiation, or bank API in the
  validation MVP; use exports and licensed providers later.

### India and compliance

- **Finding:** GST and e-invoice are India-specific but not necessarily the best
  first product wedge.
- **Correction:** defer them; first prove delayed B2B cash recovery.
- **Finding:** delayed-payment escalation is a promising expansion but can become
  legal advice.
- **Correction:** retain it as a future evidence-pack capability only; no filing
  or legal conclusion in the product.

### Open source and licensing

- **Finding:** core and provider-dependent integrations were mixed conceptually.
- **Correction:** keep the Apache-2.0 domain/policy core independent of ERPNext,
  India Compliance, Meta, bank, and GST provider code. Review license terms for
  any separate adapter or Frappe app.

## Decisions Changed

1. The commercial wedge is collections decisioning, not generic ARP.
2. The initial ICP is ERPNext-based Indian B2B distributors and light
   manufacturers.
3. The first validation mode is CSV-first and offline-capable.
4. The first product is deterministic and human-controlled; no LLM authority.
5. GST, UPI, bank, ONDC, Account Aggregator, and legal workflows are deferred.
6. Outcome attribution is measured cautiously and never claimed from a single
   post-contact payment.

## Sources Reviewed

- ERPNext dunning documentation shows existing formal overdue reminder,
  interest/fee, and payment-resolution workflows:
  https://docs.frappe.io/erpnext/dunning
- Frappe documents a trained partner ecosystem in 30+ countries:
  https://frappe.io/partners
- MSME Samadhaan describes delayed-payment provisions and a transition to the
  MSME ODR portal: https://samadhaan.msme.gov.in/
- RBI Account Aggregator Directions, 2025 define consent, registration,
  permitted activity, and data-handling constraints:
  https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12936
- SHAKE manifesto provides the architectural inspiration but not a technical
  or compliance standard: https://shakegraph.com/manifesto
