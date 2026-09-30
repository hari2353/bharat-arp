"""Immutable normalized source facts used by the validation MVP."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class SourceRef:
    tenant_id: str
    source_system: str
    source_record_id: str
    record_type: str
    source_updated_at: datetime
    import_batch_id: str

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return (
            self.tenant_id,
            self.source_system,
            self.source_record_id,
            self.record_type,
        )


@dataclass(frozen=True)
class InvoiceRecord:
    ref: SourceRef
    customer_id: str
    invoice_date: date
    due_date: date
    amount_inr: Decimal
    status: Literal["submitted", "paid", "cancelled", "overdue", "unknown"]


@dataclass(frozen=True)
class Payment:
    ref: SourceRef
    payment_date: date
    amount_inr: Decimal
    status: Literal["posted", "reversed", "pending", "unknown"]


@dataclass(frozen=True)
class PaymentAllocation:
    ref: SourceRef
    payment_id: str
    invoice_id: str
    allocated_amount_inr: Decimal


@dataclass(frozen=True)
class CreditNote:
    ref: SourceRef
    invoice_id: str
    amount_inr: Decimal
    status: Literal["posted", "reversed", "pending", "unknown"]


@dataclass(frozen=True)
class Dispute:
    ref: SourceRef
    customer_id: str
    invoice_id: str
    category: str
    status: str
    opened_at: datetime
    resolved_at: datetime | None
