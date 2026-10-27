---
status: accepted
---

# CSV-First Validation

The first validation product will use documented CSV imports and local fixtures
instead of live ERP, bank, GST, UPI, WhatsApp, or Account Aggregator APIs. This
keeps the core workflow testable without provider credentials, exposes the real
data-quality problem early, and prevents integration work from being mistaken
for product-market validation. The versioned contract is defined in
`docs/csv-contract.md`; live connectors are gated on paid pilot evidence.
