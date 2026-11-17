from datetime import date, timedelta
from decimal import Decimal

from bharat_arp.metrics import AccountMeasurement, days_sales_outstanding, measure_pilot, snapshot_pilot


def measurement(**overrides):
    values = {
        "customer_id": "CUST-1",
        "opening_outstanding": Decimal("100000.00"),
        "closing_outstanding": Decimal("60000.00"),
        "priority": True,
        "decision_eligible": True,
        "actioned_at": date(2026, 9, 2),
        "due_on": date(2026, 9, 1),
        "payment_received_at": date(2026, 9, 10),
        "payment_amount": Decimal("40000.00"),
        "payment_in_flight": False,
        "promise_status": "fulfilled",
    }
    values.update(overrides)
    return AccountMeasurement(**values)


def test_metrics_reports_observed_after_payment_without_causal_claim():
    report = measure_pilot(
        [measurement()],
        baseline_review_hours=20,
        pilot_review_hours=14,
    )

    assert report.priority_recovered_cash == Decimal("40000.00")
    assert report.priority_eligible_exposure == Decimal("100000.00")
    assert report.action_within_one_business_day == 1
    assert report.finance_review_hours_saved == Decimal("6.00")
    assert report.attribution_language == "payment observed after proposal"


def test_in_flight_payment_is_excluded_and_non_priority_is_separate():
    report = measure_pilot(
        [
            measurement(payment_in_flight=True, payment_amount=Decimal("50000.00")),
            measurement(
                customer_id="CUST-2",
                priority=False,
                opening_outstanding=Decimal("20000.00"),
                closing_outstanding=Decimal("10000.00"),
                payment_amount=Decimal("10000.00"),
            ),
        ],
        baseline_review_hours=10,
        pilot_review_hours=10,
    )

    assert report.priority_recovered_cash == Decimal("0.00")
    assert report.non_priority_recovered_cash == Decimal("10000.00")
    assert report.in_flight_payment_count == 1


def test_action_latency_counts_only_actions_within_one_business_day():
    report = measure_pilot(
        [
            measurement(actioned_at=date(2026, 9, 2)),
            measurement(customer_id="CUST-2", actioned_at=date(2026, 9, 4)),
        ],
        baseline_review_hours=10,
        pilot_review_hours=10,
    )

    assert report.action_within_one_business_day == 1


def test_weekly_snapshot_reports_cohorts_ageing_and_eligibility():
    snapshot = snapshot_pilot(
        "TENANT-1",
        as_of=date(2026, 9, 30),
        measurements=[
            measurement(),
            measurement(
                customer_id="CUST-2",
                priority=False,
                opening_outstanding=Decimal("20000.00"),
                closing_outstanding=Decimal("20000.00"),
                due_on=date(2026, 7, 1),
                decision_eligible=False,
                payment_received_at=None,
                promise_status=None,
            ),
        ],
    )

    assert snapshot.priority_accounts == 1
    assert snapshot.non_priority_accounts == 1
    assert snapshot.priority_eligible_exposure == Decimal("100000.00")
    assert snapshot.non_priority_exposure == Decimal("20000.00")
    assert snapshot.ageing_60_plus_accounts == 1
    assert snapshot.promise_fulfilled == 1


# ── DSO (market-steal: the KPI every AR vendor sells first) ───────────────────
from datetime import date, datetime, timezone
from decimal import Decimal

from bharat_arp.metrics import days_sales_outstanding
from bharat_arp.models import InvoiceRecord, SourceRef


def _inv(inv_id: str, customer: str, amount: str, invoice_date: date,
         due_date: date, status: str = "submitted") -> InvoiceRecord:
    return InvoiceRecord(
        ref=SourceRef(tenant_id="T1", source_system="erpnext_csv",
                      source_record_id=inv_id, record_type="invoices",
                      source_updated_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
                      import_batch_id="B1"),
        customer_id=customer, invoice_date=invoice_date, due_date=due_date,
        amount_inr=Decimal(amount), status=status,  # type: ignore[arg-type]
    )


def test_dso_matches_hand_computation():
    """One overdue-unpaid invoice of 300k (I2 is paid, I3 not yet due);
    900k invoiced in the 90-day window: DSO = 300000/900000 * 90 = 30.0."""
    invoices = [
        _inv("I1", "C1", "300000.00", date(2026, 7, 10), date(2026, 8, 10)),
        _inv("I2", "C2", "300000.00", date(2026, 8, 1), date(2026, 9, 1),
             status="paid"),
        _inv("I3", "C3", "300000.00", date(2026, 9, 15), date(2026, 10, 15)),
    ]
    dso = days_sales_outstanding(invoices, as_of=date(2026, 9, 30))
    assert dso == Decimal("30.00")


def test_dso_excludes_cancelled_and_not_yet_due_invoices_from_outstanding():
    invoices = [
        _inv("I1", "C1", "300000.00", date(2026, 7, 10), date(2026, 8, 10)),
        _inv("X1", "C2", "999999.00", date(2026, 7, 10), date(2026, 8, 10),
             status="cancelled"),
        _inv("F1", "C3", "999999.00", date(2026, 9, 15), date(2026, 12, 15)),
    ]
    dso = days_sales_outstanding(invoices, as_of=date(2026, 9, 30))
    # outstanding: only I1 (300k, due); sales window 90d: I1 + F1 = 1.3M
    # F1 is not yet due so it drops from outstanding but still counts as sales
    assert dso == (Decimal("300000.00") / Decimal("1300000.00") * 90).quantize(Decimal("0.01"))


def test_dso_with_no_sales_in_window_is_none_not_a_crash():
    invoices = [_inv("OLD", "C1", "300000.00", date(2025, 1, 1), date(2025, 2, 1))]
    assert days_sales_outstanding(invoices, as_of=date(2026, 9, 30)) is None


def test_dso_zero_when_nothing_outstanding():
    invoices = [_inv("I1", "C1", "300000.00", date(2026, 8, 1), date(2026, 8, 31),
                     status="paid")]
    assert days_sales_outstanding(invoices, as_of=date(2026, 9, 30)) == Decimal("0.00")


def test_dso_uses_reconciled_outstanding_not_gross_invoice_amount():
    """100k invoice with a 40k posted payment allocated to it: outstanding is
    60k, so DSO = 60000/100000*90 = 54.00 — not the gross 90.00."""
    from bharat_arp.models import Payment, PaymentAllocation

    ref_pay = SourceRef(tenant_id="T1", source_system="erpnext_csv",
                        source_record_id="PAY-1", record_type="payments",
                        source_updated_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
                        import_batch_id="B1")
    ref_alloc = SourceRef(tenant_id="T1", source_system="erpnext_csv",
                          source_record_id="ALLOC-1", record_type="payment_allocations",
                          source_updated_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
                          import_batch_id="B1")
    invoices = [_inv("I1", "C1", "100000.00", date(2026, 8, 1), date(2026, 8, 31))]
    payments = [Payment(ref=ref_pay, payment_date=date(2026, 9, 5),
                        amount_inr=Decimal("40000.00"), status="posted")]
    allocations = [PaymentAllocation(ref=ref_alloc, payment_id="PAY-1",
                                     invoice_id="I1",
                                     allocated_amount_inr=Decimal("40000.00"))]
    dso = days_sales_outstanding(invoices, payments=payments,
                                 allocations=allocations, credit_notes=(),
                                 as_of=date(2026, 9, 30))
    assert dso == Decimal("54.00")
