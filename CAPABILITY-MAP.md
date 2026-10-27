# Capability Map: Bharat ARP

The product is decomposed before implementation so each capability can be
validated independently and the dependency direction stays one-way.

| Module id | Responsibility | Depends on |
|---|---|---|
| `tenant-audit` | Tenant identity, operator scope, data classification, lifecycle, and append-only audit records with documented purge redaction | None |
| `source-ingestion` | CSV imports first; ERPNext adapter later; provenance and idempotent upserts | `tenant-audit` |
| `receivables-model` | Customers, invoices, outstanding balances, allocations, disputes, payment terms | `tenant-audit`, `source-ingestion` |
| `collections-decisioning` | Explainable account ranking and bounded next-action proposals | `receivables-model` |
| `promise-to-pay` | Record, update, and evaluate payment promises | `receivables-model` |
| `approval-actions` | Approval inbox and provider-neutral outbound action contract | `tenant-audit`, `collections-decisioning`, `promise-to-pay` |
| `outcome-measurement` | Payment linkage, broken-promise tracking, cohort metrics, pilot reporting | `receivables-model`, `promise-to-pay`, `approval-actions` |
| `connectors` | Optional ERPNext, email, and compliant messaging adapters | `source-ingestion`, `approval-actions` |

## Build Order

1. `tenant-audit`
2. `source-ingestion`
3. `receivables-model`
4. `collections-decisioning`
5. `promise-to-pay`
6. `approval-actions`
7. `outcome-measurement`
8. `connectors`

The first validation product stops after `outcome-measurement` and uses CSV
fixtures, a single configured operator, and local reports. It does not require
hosted roles or live ERP, bank, GST, UPI, WhatsApp, or LLM connections.

## Explicitly Deferred Capabilities

- GST return, e-invoice, and e-waybill submission
- Payment initiation or account aggregation
- ONDC integration
- Automatic legal notice or MSMED claim filing
- Autonomous credit blocking, refunds, payments, or tax actions
- General-purpose chatbot or unrestricted agent tools
- Multi-ERP support before the ERPNext workflow is proven
