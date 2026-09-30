# Data Lifecycle and Pilot Controls

The validation MVP is a single-tenant local deployment. One configured tenant
is accepted per deployment, and the operator is responsible for protecting the
machine and imported files. Every domain record still carries `tenant_id` so
the model and repositories cannot silently become cross-tenant later.

## Data Classes

| Class | Examples | Default retention | Deletion behavior |
|---|---|---:|---|
| Source financial | invoices, payments, allocations, credit notes | 24 months | delete on tenant purge unless legal hold |
| Contact data | names, email, phone, permission state | 12 months | delete on tenant purge; redact from derived records |
| Workflow data | cases, proposals, promises, outcomes | 24 months | delete on tenant purge unless legal hold |
| Raw import | original CSV rows and file metadata | 90 days | delete after retention or tenant purge |
| Audit record | actor, action, object reference, timestamps | 24 months | append-only during retention; pseudonymize references on purge |
| Aggregate metrics | exposure and cohort counts without contact data | 24 months | delete on tenant purge if tenant-identifiable |

These are pilot defaults, not legal advice. A customer-specific retention or
legal-hold policy must override them before real data is imported.

## Audit Semantics

Audit records are append-only and tamper-evident during their active retention
period. They contain no message body, full contact value, secret, or raw CSV
payload. They reference tenant-scoped object identifiers and a redacted action
summary.

After an approved tenant purge, audit records are not rewritten to change
history. Their tenant and object references are replaced by a non-reversible
deletion tombstone, actor identifiers are pseudonymized, and the purge event
records the reason, actor, time, and policy used. A legal hold suspends purge
for the held records.

## Required Pilot Controls

- No maintainer or developer access to pilot data by default.
- No telemetry containing customer names, contact values, invoice IDs, or
  amounts.
- Local import and export paths must be explicitly selected and stay within the
  configured workspace root.
- Generated CSV exports must neutralize spreadsheet formulas in text fields.
- Export and deletion must cover source, normalized, workflow, raw-import, and
  audit-derived records according to the active retention policy.
- Pilot data processing, operator access, incident handling, and subprocessors
  require customer agreement and legal review before production use.
