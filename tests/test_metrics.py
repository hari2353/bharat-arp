from datetime import date, timedelta
from decimal import Decimal

from bharat_arp.metrics import AccountMeasurement, measure_pilot, snapshot_pilot


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
