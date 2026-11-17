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


# ── dispute containment (market-steal: Kolleno) ───────────────────────────────
# A disputed line must not freeze the whole account: undisputed overdue lines
# stay chaseable, the disputed ones are tracked separately and routed out.


def _exposure(inv: str, amount: str, due: date) -> AccountExposure:
    return AccountExposure(invoice_id=inv, outstanding=Decimal(amount),
                           due_date=due, reconciliation_state="unpaid")


def test_disputed_lines_contained_undisputed_stay_chaseable():
    accounts = [CustomerAccount(
        customer_id="CUST-MIXED", legal_name="Mixed",
        exposures=(_exposure("INV-CLEAN", "50000.00", date(2026, 8, 1)),
                   _exposure("INV-DISPUTED", "70000.00", date(2026, 7, 1))),
        disputed_invoice_ids=frozenset({"INV-DISPUTED"}),
        unresolved_dispute=True,
    )]
    ranked = rank_accounts(accounts, as_of=date(2026, 9, 30),
                           policy_version="containment-1")
    item = ranked[0]
    assert item.eligible is True                       # chaseable on INV-CLEAN
    assert item.disputed_outstanding == Decimal("70000.00")
    assert item.outstanding == Decimal("120000.00")    # total exposure unchanged
    assert "dispute_contained_invoices=1" in item.explanation
    # score is driven by the chaseable 50000, not the frozen 120000
    clean_only = [CustomerAccount(
        customer_id="CUST-MIXED", legal_name="Mixed",
        exposures=(_exposure("INV-CLEAN", "50000.00", date(2026, 8, 1)),))]
    baseline = rank_accounts(clean_only, as_of=date(2026, 9, 30),
                             policy_version="containment-1")[0]
    assert item.score == baseline.score


def test_all_overdue_disputed_account_stays_frozen():
    accounts = [CustomerAccount(
        customer_id="CUST-FROZEN", legal_name="Frozen",
        exposures=(_exposure("INV-D1", "70000.00", date(2026, 7, 1)),),
        disputed_invoice_ids=frozenset({"INV-D1"}),
        unresolved_dispute=True,
    )]
    ranked = rank_accounts(accounts, as_of=date(2026, 9, 30),
                           policy_version="containment-1")
    assert ranked[0].eligible is False
    assert "open_dispute" in ranked[0].missing_inputs
    assert ranked[0].disputed_outstanding == Decimal("70000.00")


def test_dispute_flag_without_ids_keeps_legacy_missing_input():
    """Old callers pass only the boolean: without invoice ids the contested
    lines cannot be isolated, so the legacy contract holds — account stays
    eligible for review but every customer contact is proposal-blocked."""
    accounts = [CustomerAccount(
        customer_id="CUST-LEGACY", legal_name="Legacy",
        exposures=(_exposure("INV-1", "50000.00", date(2026, 8, 1)),),
        unresolved_dispute=True,
    )]
    ranked = rank_accounts(accounts, as_of=date(2026, 9, 30),
                           policy_version="containment-1")
    assert ranked[0].eligible is True                 # legacy behavior
    assert "open_dispute" in ranked[0].missing_inputs  # proposal gate


def test_undisputed_account_output_unchanged_by_containment_fields():
    accounts = [CustomerAccount(
        customer_id="CUST-CLEAN", legal_name="Clean",
        exposures=(_exposure("INV-1", "50000.00", date(2026, 8, 1)),),
    )]
    ranked = rank_accounts(accounts, as_of=date(2026, 9, 30),
                           policy_version="containment-1")
    assert ranked[0].eligible is True
    assert ranked[0].disputed_outstanding == Decimal("0.00")
    assert "dispute_contained" not in ranked[0].explanation
