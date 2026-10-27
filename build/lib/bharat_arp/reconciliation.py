"""Pure, conservative invoice balance reconciliation."""

from dataclasses import dataclass
from decimal import Decimal

from .models import CreditNote, InvoiceRecord, Payment, PaymentAllocation


@dataclass(frozen=True)
class ReconciliationResult:
    gross_due: Decimal
    allocated: Decimal
    outstanding: Decimal
    state: str
    exceptions: tuple[str, ...]


def reconcile_invoice(
    invoice: InvoiceRecord,
    *,
    payments: list[Payment],
    allocations: list[PaymentAllocation],
    credit_notes: list[CreditNote],
) -> ReconciliationResult:
    """Calculate an invoice balance without silently correcting bad source data."""
    exceptions: list[str] = []
    if invoice.status == "cancelled":
        return ReconciliationResult(
            gross_due=Decimal("0.00"),
            allocated=Decimal("0.00"),
            outstanding=Decimal("0.00"),
            state="cancelled",
            exceptions=(),
        )

    posted_credits = sum(
        (
            note.amount_inr
            for note in credit_notes
            if note.invoice_id == invoice.ref.source_record_id
            and note.status == "posted"
        ),
        Decimal("0.00"),
    )
    gross_due = invoice.amount_inr - posted_credits

    payments_by_id = {payment.ref.source_record_id: payment for payment in payments}
    allocated = Decimal("0.00")
    for allocation in allocations:
        if allocation.invoice_id != invoice.ref.source_record_id:
            continue
        payment = payments_by_id.get(allocation.payment_id)
        if payment is None:
            exceptions.append(f"payment_missing:{allocation.payment_id}")
            continue
        if payment.status != "posted":
            exceptions.append(f"payment_not_posted:{allocation.payment_id}")
            continue
        if allocation.allocated_amount_inr < 0:
            exceptions.append(f"allocation_negative:{allocation.ref.source_record_id}")
            continue
        allocated += allocation.allocated_amount_inr

    outstanding = gross_due - allocated
    if outstanding < 0:
        exceptions.append("overpayment")
        state = "overpaid"
    elif outstanding == 0:
        state = "paid"
    elif allocated > 0:
        state = "partially_paid"
    else:
        state = "unpaid"

    return ReconciliationResult(
        gross_due=gross_due,
        allocated=allocated,
        outstanding=outstanding,
        state=state,
        exceptions=tuple(exceptions),
    )
