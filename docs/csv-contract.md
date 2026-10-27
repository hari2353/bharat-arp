# CSV Contract: Validation MVP

This is the normative input contract for the offline validation MVP. A pilot
may provide equivalent exports, but the importer must map them into this
contract before decisioning.

## File Set

Each import batch contains these UTF-8 CSV files:

- `customers.csv`
- `contacts.csv`
- `invoices.csv`
- `payments.csv`
- `payment_allocations.csv`
- `credit_notes.csv`
- `disputes.csv`

Every file has a header row, comma delimiter, quoted fields when needed, and a
maximum of 100,000 rows or 10 MB per file in the validation MVP. Unknown
columns are rejected unless the schema version explicitly permits them.

## Common Fields

Every row contains:

- `tenant_id`: the configured deployment tenant; mismatches are rejected
- `source_system`: stable source name, such as `erpnext_csv`
- `source_record_id`: stable identifier within `source_system`
- `source_updated_at`: ISO-8601 timestamp with offset
- `import_batch_id`: caller-provided batch identifier

The identity key is `(tenant_id, source_system, source_record_id, record_type)`.
`import_batch_id` is provenance, not identity.

## Financial Rules

The validation MVP supports INR only and uses `Asia/Kolkata` for date-only
business dates. Amounts are decimal values with at most two fractional digits;
floating-point arithmetic is prohibited.

For each invoice as of an `as_of_date`:

```text
gross_due = invoice_amount + valid_debit_adjustments - valid_credit_notes
allocated = sum(valid_payment_allocations)
outstanding = gross_due - allocated
```

Rules:

- An allocation must reference an existing payment and invoice in the same
  tenant and currency.
- An allocation cannot exceed the payment's remaining allocatable amount or the
  invoice's gross due without an explicit source correction exception.
- A negative outstanding balance is an overpayment/credit exception; it is not
  silently clamped to zero.
- Cancelled or voided source records do not contribute to gross due after their
  effective source timestamp.
- Duplicate source rows are rejected or coalesced only when their source
  identity and complete payload are identical.
- Partial allocations remain visible and produce a partial-payment state.
- Refunds and multi-currency records are rejected as unsupported in this phase.

## Required Record Fields

### `customers.csv`

`source_customer_id`, `legal_name`, `status`

### `contacts.csv`

`source_contact_id`, `source_customer_id`, `display_name`, `role`,
`email`, `phone`, `email_permission`, `whatsapp_permission`, `opted_out`,
`permission_observed_at`

Permission values are `eligible`, `denied`, or `unknown`. A present phone or
email with `unknown` permission is not Communication Eligibility.

### `invoices.csv`

`source_invoice_id`, `source_customer_id`, `invoice_date`, `due_date`,
`amount_inr`, `status`

`status` is one of `submitted`, `paid`, `cancelled`, `overdue`, or `unknown`.
The normalized balance, not this status string, determines decision eligibility.

### `payments.csv`

`source_payment_id`, `payment_date`, `amount_inr`, `status`

`status` is one of `posted`, `reversed`, `pending`, or `unknown`.
Only `posted` payments can be allocated.

### `payment_allocations.csv`

`source_payment_id`, `source_invoice_id`, `allocated_amount_inr`

### `credit_notes.csv`

`source_credit_note_id`, `source_invoice_id`, `credit_date`,
`amount_inr`, `status`

Only `posted` credit notes reduce gross due.

### `disputes.csv`

`source_dispute_id`, `source_customer_id`, `source_invoice_id`, `category`,
`status`, `opened_at`, `resolved_at`

An open dispute is a risk flag and blocks an automatic customer-contact draft.

## Import Behavior

- Batch validation occurs before decisioning; invalid rows are retained as
  redacted error records and do not become financial facts.
- A batch may be partially accepted, but its acceptance summary must report
  rows and INR exposure accepted, rejected, and unresolved.
- Replaying an identical batch is a no-op.
- A corrected source record creates a new observed version while preserving the
  prior version and its audit trail.
- A source snapshot never deletes records implicitly. Voids/cancellations must
  be explicit source facts.
