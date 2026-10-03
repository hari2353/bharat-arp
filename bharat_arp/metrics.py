"""Conservative pilot measurement for collection outcomes."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class AccountMeasurement:
    customer_id: str
    opening_outstanding: Decimal
    closing_outstanding: Decimal
    priority: bool
    decision_eligible: bool
    actioned_at: date | None
    due_on: date
    payment_received_at: date | None
    payment_amount: Decimal
    payment_in_flight: bool
    promise_status: str | None


@dataclass(frozen=True)
class PilotReport:
    priority_recovered_cash: Decimal
    non_priority_recovered_cash: Decimal
    priority_eligible_exposure: Decimal
    action_within_one_business_day: int
    finance_review_hours_saved: Decimal
    in_flight_payment_count: int
    fulfilled_promises: int
    broken_promises: int
    attribution_language: str


@dataclass(frozen=True)
class WeeklySnapshot:
    tenant_id: str
    as_of: date
    priority_accounts: int
    non_priority_accounts: int
    priority_eligible_exposure: Decimal
    non_priority_exposure: Decimal
    ageing_30_plus_accounts: int
    ageing_60_plus_accounts: int
    ageing_90_plus_accounts: int
    decision_eligible_accounts: int
    decision_eligible_exposure: Decimal
    in_flight_payment_count: int
    promise_fulfilled: int
    promise_partial: int
    promise_broken: int
    attribution_language: str = "payment observed after proposal"


def measure_pilot(
    measurements: list[AccountMeasurement],
    *,
    baseline_review_hours: Decimal | int,
    pilot_review_hours: Decimal | int,
) -> PilotReport:
    priority_recovered = Decimal("0.00")
    non_priority_recovered = Decimal("0.00")
    priority_eligible = Decimal("0.00")
    within_one_day = 0
    in_flight = 0
    fulfilled = 0
    broken = 0

    for item in measurements:
        if item.priority and item.decision_eligible:
            priority_eligible += item.opening_outstanding
        if item.payment_in_flight:
            in_flight += 1
        elif item.payment_received_at is not None:
            if item.priority:
                priority_recovered += item.payment_amount
            else:
                non_priority_recovered += item.payment_amount
        if item.actioned_at is not None and _business_days_after(
            item.due_on, item.actioned_at
        ) <= 1:
            within_one_day += 1
        if item.promise_status == "fulfilled":
            fulfilled += 1
        elif item.promise_status == "broken":
            broken += 1

    return PilotReport(
        priority_recovered_cash=priority_recovered,
        non_priority_recovered_cash=non_priority_recovered,
        priority_eligible_exposure=priority_eligible,
        action_within_one_business_day=within_one_day,
        finance_review_hours_saved=Decimal(str(baseline_review_hours))
        - Decimal(str(pilot_review_hours)),
        in_flight_payment_count=in_flight,
        fulfilled_promises=fulfilled,
        broken_promises=broken,
        attribution_language="payment observed after proposal",
    )


def snapshot_pilot(
    tenant_id: str, *, as_of: date, measurements: list[AccountMeasurement]
) -> WeeklySnapshot:
    priority = [item for item in measurements if item.priority]
    non_priority = [item for item in measurements if not item.priority]
    eligible = [item for item in measurements if item.decision_eligible]
    return WeeklySnapshot(
        tenant_id=tenant_id,
        as_of=as_of,
        priority_accounts=len(priority),
        non_priority_accounts=len(non_priority),
        priority_eligible_exposure=sum(
            (item.opening_outstanding for item in priority if item.decision_eligible),
            Decimal("0.00"),
        ),
        non_priority_exposure=sum(
            (item.opening_outstanding for item in non_priority), Decimal("0.00")
        ),
        ageing_30_plus_accounts=sum(
            (as_of - item.due_on).days >= 30 for item in measurements
        ),
        ageing_60_plus_accounts=sum(
            (as_of - item.due_on).days >= 60 for item in measurements
        ),
        ageing_90_plus_accounts=sum(
            (as_of - item.due_on).days >= 90 for item in measurements
        ),
        decision_eligible_accounts=len(eligible),
        decision_eligible_exposure=sum(
            (item.opening_outstanding for item in eligible), Decimal("0.00")
        ),
        in_flight_payment_count=sum(item.payment_in_flight for item in measurements),
        promise_fulfilled=sum(item.promise_status == "fulfilled" for item in measurements),
        promise_partial=sum(item.promise_status == "partial" for item in measurements),
        promise_broken=sum(item.promise_status == "broken" for item in measurements),
    )


def _business_days_after(start: date, end: date) -> int:
    if end < start:
        return 0
    days = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days += 1
    return days
