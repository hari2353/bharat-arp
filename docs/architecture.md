# Architecture Notes

## Product Boundary

The manifesto's useful distinction is between a legally defensible record and a
system that helps decide what happens next. Bharat ARP applies that idea to a
narrow workflow: collections decisioning for ERPNext-based Indian B2B
distributors and light manufacturers.

ERPNext remains authoritative for accounting facts. Bharat ARP owns normalized
provenance, Collection Cases, Collection Proposals, approvals, Promises to Pay,
and Collection Outcomes. It does not replace the ledger or claim to provide tax
or legal advice.

## Initial Domain Contracts

The first contracts are intentionally operational rather than generic:

- `CustomerAccount`: customer-level aggregation across invoices and payments.
- `Invoice`: a normalized receivables fact with source provenance.
- `Payment`: a source fact of money received, distinct from its allocations.
- `PaymentAllocation`: an explicit payment-to-invoice relationship.
- `CreditNote`: a source adjustment that reduces amount due.
- `Contact` and `CommunicationEligibility`: a person/channel record and its
  permission evidence.
- `Dispute`: an open challenge that can block customer-contact proposals.
- `CollectionCase`: a work item for an overdue customer exposure.
- `CollectionProposal`: a non-mutating recommendation with evidence, policy
  version, risk flags, and approval requirement.
- `PromiseToPay`: an amount/date commitment with a lifecycle status.
- `CollectionOutcome`: the observed result of a proposal or case.

Every persisted record requires `tenant_id`, source references where relevant,
timestamps, and audit metadata. Audit records are append-only during retention;
purge redaction and legal holds follow `docs/data-lifecycle.md`. Future side
effects require an idempotency key, explicit approval, and a provider-specific
adapter.

In validation mode, one local deployment maps to one Tenant and one Legal Entity.
The operator is explicit and all workflow commands are tenant-scoped. Hosted
multi-user roles are a later capability, not an implied property of the local
prototype.

## Validation Architecture

The first product is CSV-first and offline-capable. It validates source data,
calculates outstanding balances, ranks accounts using transparent policy rules,
and records human outcomes. It does not need provider credentials.

Do not add FastAPI, PostgreSQL, Temporal, LangGraph, vector search, GST,
e-invoice, e-waybill, UPI, bank, ONDC, Account Aggregator, or messaging SDKs
until a paid pilot and a specific acceptance criterion justify them.

## Later Integration Boundary

When live integrations are justified, use ERPNext APIs or supported exports,
not direct database writes. Treat GST, payment, bank, and messaging systems as
provider boundaries with their own authentication, retry, consent, rate-limit,
signature, and licensing requirements.

## Safety Rules

- No payment initiation in the validation MVP.
- No GST, e-invoice, or e-waybill submission in the validation MVP.
- No autonomous legal notice, MSMED filing, or credit-limit change.
- No unrestricted SQL, shell, or HTTP tools exposed to a model.
- No LLM authority in the validation MVP; later model output is untrusted and
  must be schema-validated and evidence-linked.
- No customer data sent to a model provider without explicit configuration,
  consent/contractual basis, and an appropriate data-processing agreement.
- Communication eligibility is never inferred from a phone number alone.
- All future outbound actions require explicit approval, an idempotency key, and
  an audit record.
- Tenant isolation, retention, export, and deletion are acceptance criteria,
  not optional hardening work.
