"""Versioned CSV boundary contracts for the validation MVP."""

from dataclasses import dataclass


COMMON_FIELDS = (
    "tenant_id",
    "source_system",
    "source_record_id",
    "source_updated_at",
    "import_batch_id",
)

REQUIRED_FIELDS = {
    "customers": COMMON_FIELDS + ("source_customer_id", "legal_name", "status"),
    "contacts": COMMON_FIELDS
    + (
        "source_contact_id",
        "source_customer_id",
        "display_name",
        "role",
        "email",
        "phone",
        "email_permission",
        "whatsapp_permission",
        "opted_out",
        "permission_observed_at",
    ),
    "invoices": COMMON_FIELDS
    + (
        "source_invoice_id",
        "source_customer_id",
        "invoice_date",
        "due_date",
        "amount_inr",
        "status",
    ),
    "payments": COMMON_FIELDS
    + ("source_payment_id", "payment_date", "amount_inr", "status"),
    "payment_allocations": COMMON_FIELDS
    + ("source_payment_id", "source_invoice_id", "allocated_amount_inr"),
    "credit_notes": COMMON_FIELDS
    + ("source_credit_note_id", "source_invoice_id", "credit_date", "amount_inr", "status"),
    "disputes": COMMON_FIELDS
    + (
        "source_dispute_id",
        "source_customer_id",
        "source_invoice_id",
        "category",
        "status",
        "opened_at",
        "resolved_at",
    ),
}


@dataclass(frozen=True)
class CsvError:
    row_number: int | None
    code: str
    message: str


@dataclass(frozen=True)
class CsvValidationResult:
    record_type: str
    rows: tuple[dict[str, str], ...]
    errors: tuple[CsvError, ...]
