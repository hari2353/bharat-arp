from datetime import date
from decimal import Decimal

from bharat_arp.decisioning import (
    AccountExposure,
    CustomerAccount,
    rank_accounts,
)


def test_ranks_customer_accounts_by_exposure_and_ageing_with_explanations():
    accounts = [
        CustomerAccount(
            customer_id="CUST-LOW",
            legal_name="Low Exposure",
            exposures=(
                AccountExposure(
                    invoice_id="INV-LOW",
                    outstanding=Decimal("10000.00"),
                    due_date=date(2026, 9, 20),
                    reconciliation_state="unpaid",
                ),
            ),
        ),
        CustomerAccount(
            customer_id="CUST-HIGH",
            legal_name="High Exposure",
            exposures=(
                AccountExposure(
                    invoice_id="INV-HIGH",
                    outstanding=Decimal("125000.00"),
                    due_date=date(2026, 7, 1),
                    reconciliation_state="partially_paid",
                ),
            ),
            broken_promises=1,
        ),
    ]

    ranked = rank_accounts(accounts, as_of=date(2026, 9, 30), policy_version="v1")

    assert [item.customer_id for item in ranked] == ["CUST-HIGH", "CUST-LOW"]
    assert ranked[0].eligible is True
    assert ranked[0].score > ranked[1].score
    assert "outstanding_inr=125000.00" in ranked[0].explanation
    assert "broken_promises=1" in ranked[0].explanation
    assert ranked[0].policy_version == "v1"


def test_unresolved_and_overpaid_exposure_is_excluded_with_visible_reason():
    accounts = [
        CustomerAccount(
            customer_id="CUST-BAD",
            legal_name="Needs Review",
            exposures=(
                AccountExposure(
                    invoice_id="INV-BAD",
                    outstanding=Decimal("-10.00"),
                    due_date=date(2026, 7, 1),
                    reconciliation_state="overpaid",
                ),
            ),
            data_quality_exceptions=("unresolved_payment_allocation",),
        )
    ]

    ranked = rank_accounts(accounts, as_of=date(2026, 9, 30), policy_version="v1")

    assert ranked[0].eligible is False
    assert ranked[0].score == Decimal("0.00")
    assert "not eligible" in ranked[0].explanation
    assert "unresolved_payment_allocation" in ranked[0].explanation


def test_ageing_cohort_is_explicit_and_future_due_is_not_actionable():
    account = CustomerAccount(
        customer_id="CUST-FUTURE",
        legal_name="Future Due",
        exposures=(
            AccountExposure(
                invoice_id="INV-FUTURE",
                outstanding=Decimal("90000.00"),
                due_date=date(2026, 10, 5),
                reconciliation_state="unpaid",
            ),
        ),
    )

    ranked = rank_accounts([account], as_of=date(2026, 9, 30), policy_version="v1")

    assert ranked[0].ageing_bucket == "not_due"
    assert ranked[0].eligible is False
