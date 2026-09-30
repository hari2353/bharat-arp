from datetime import date, datetime, timezone
from decimal import Decimal

from bharat_arp.models import (
    CreditNote,
    InvoiceRecord,
    Payment,
    PaymentAllocation,
    SourceRef,
)
from bharat_arp.reconciliation import reconcile_invoice


def source(record_type: str, record_id: str) -> SourceRef:
    return SourceRef(
        tenant_id="TENANT-1",
        source_system="erpnext_csv",
        source_record_id=record_id,
        record_type=record_type,
        source_updated_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
        import_batch_id="BATCH-1",
    )


def invoice(amount: str = "1000.00", status: str = "submitted") -> InvoiceRecord:
    return InvoiceRecord(
        ref=source("invoice", "INV-1"),
        customer_id="CUST-1",
        invoice_date=date(2026, 8, 1),
        due_date=date(2026, 9, 1),
        amount_inr=Decimal(amount),
        status=status,
    )


def test_reconciles_partial_payment_and_credit_note_with_decimal_arithmetic():
    result = reconcile_invoice(
        invoice(),
        payments=[
            Payment(
                ref=source("payment", "PAY-1"),
                payment_date=date(2026, 9, 10),
                amount_inr=Decimal("500.10"),
                status="posted",
            )
        ],
        allocations=[
            PaymentAllocation(
                ref=source("payment_allocation", "ALLOC-1"),
                payment_id="PAY-1",
                invoice_id="INV-1",
                allocated_amount_inr=Decimal("500.10"),
            )
        ],
        credit_notes=[
            CreditNote(
                ref=source("credit_note", "CN-1"),
                invoice_id="INV-1",
                amount_inr=Decimal("99.90"),
                status="posted",
            )
        ],
    )

    assert result.gross_due == Decimal("900.10")
    assert result.allocated == Decimal("500.10")
    assert result.outstanding == Decimal("400.00")
    assert result.state == "partially_paid"
    assert result.exceptions == ()


def test_rejects_allocation_to_pending_payment_without_using_it():
    result = reconcile_invoice(
        invoice(),
        payments=[
            Payment(
                ref=source("payment", "PAY-1"),
                payment_date=date(2026, 9, 10),
                amount_inr=Decimal("1000.00"),
                status="pending",
            )
        ],
        allocations=[
            PaymentAllocation(
                ref=source("payment_allocation", "ALLOC-1"),
                payment_id="PAY-1",
                invoice_id="INV-1",
                allocated_amount_inr=Decimal("1000.00"),
            )
        ],
        credit_notes=[],
    )

    assert result.allocated == Decimal("0.00")
    assert result.outstanding == Decimal("1000.00")
    assert result.state == "unpaid"
    assert "payment_not_posted:PAY-1" in result.exceptions


def test_surfaces_overpayment_instead_of_clamping_balance_to_zero():
    result = reconcile_invoice(
        invoice(),
        payments=[
            Payment(
                ref=source("payment", "PAY-1"),
                payment_date=date(2026, 9, 10),
                amount_inr=Decimal("1200.00"),
                status="posted",
            )
        ],
        allocations=[
            PaymentAllocation(
                ref=source("payment_allocation", "ALLOC-1"),
                payment_id="PAY-1",
                invoice_id="INV-1",
                allocated_amount_inr=Decimal("1200.00"),
            )
        ],
        credit_notes=[],
    )

    assert result.outstanding == Decimal("-200.00")
    assert result.state == "overpaid"
    assert "overpayment" in result.exceptions


def test_cancelled_invoice_does_not_contribute_to_outstanding_balance():
    result = reconcile_invoice(
        invoice(status="cancelled"),
        payments=[],
        allocations=[],
        credit_notes=[],
    )

    assert result.gross_due == Decimal("0.00")
    assert result.outstanding == Decimal("0.00")
    assert result.state == "cancelled"
