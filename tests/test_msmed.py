"""MSMED delayed-payment lever — the "Bharat" differentiator no scanned
competitor implements. MSMED Act: a buyer who has not paid an MSME supplier
within the agreed terms (45 days absent agreement) owes compound interest
at three times the RBI bank rate (§16), and the supplier may file on MSME
Samadhaan once the notice window also lapses (§18, 45+15 days by default).

Deterministic math on the evidence ledger; the bank rate is a dated config
input, never fetched. Every result is a proposal input — nothing is filed,
sent, or claimed automatically."""

from datetime import date
from decimal import Decimal

from bharat_arp.decisioning import RankedAccount
from bharat_arp.msmed import MsmedConfig, msmed_position


def ranked(overdue_days=60, outstanding="100000.00", eligible=True):
    return RankedAccount(
        customer_id="CUST-1",
        legal_name="Acme",
        score=Decimal("100.00"),
        outstanding=Decimal(outstanding),
        overdue_days=overdue_days,
        ageing_bucket="60_89",
        eligible=eligible,
        policy_version="v1",
        explanation="outstanding_inr=100000.00",
        missing_inputs=(),
    )


# ---------------------------------------------------------------- guards
def test_within_agreed_terms_yields_no_position():
    assert (
        msmed_position(
            ranked(overdue_days=30), as_of=date(2026, 9, 30), config=MsmedConfig()
        )
        is None
    )


def test_non_msme_supplier_tenant_yields_nothing():
    config = MsmedConfig(msme_supplier=False)
    assert (
        msmed_position(ranked(overdue_days=120), as_of=date(2026, 9, 30), config=config)
        is None
    )


def test_ineligible_or_paid_account_yields_nothing():
    assert (
        msmed_position(
            ranked(eligible=False), as_of=date(2026, 9, 30), config=MsmedConfig()
        )
        is None
    )
    assert (
        msmed_position(
            ranked(outstanding="0.00"), as_of=date(2026, 9, 30), config=MsmedConfig()
        )
        is None
    )


# ---------------------------------------------------------------- §16 math
def test_compound_interest_matches_hand_computation():
    """₹1,00,000, 90 days beyond 45-day terms, bank rate 6.5%:
    3×6.5% = 19.5%/yr -> 1.625%/month, 3 complete months:
    100000 × (1.01625³ − 1) = 100000 × 0.049546478... = 4954.65."""
    pos = msmed_position(
        ranked(overdue_days=135), as_of=date(2026, 9, 30), config=MsmedConfig()
    )
    assert pos.days_beyond_terms == 90
    assert pos.interest_accrued == Decimal("4954.65")


def test_partial_month_accrues_nothing_yet():
    """Interest compounds on completed months only (floor approximation,
    stated in the explanation): 15 days beyond terms -> 0.00 accrued."""
    pos = msmed_position(
        ranked(overdue_days=60), as_of=date(2026, 9, 30), config=MsmedConfig()
    )
    assert pos.days_beyond_terms == 15
    assert pos.interest_accrued == Decimal("0.00")


def test_explanation_carries_the_math_and_inputs():
    pos = msmed_position(
        ranked(overdue_days=135),
        as_of=date(2026, 9, 30),
        config=MsmedConfig(bank_rate_annual_pct=Decimal("6.5")),
    )
    for needle in ("bank_rate=6.5", "months=3", "terms_days=45", "compounded monthly"):
        assert needle in pos.explanation, needle
    assert pos.policy_version == "msmed-2026-11"


# ---------------------------------------------------------------- §18 gate
def test_samadhaan_eligibility_boundary():
    eligible = msmed_position(
        ranked(overdue_days=60), as_of=date(2026, 9, 30), config=MsmedConfig()
    )
    not_yet = msmed_position(
        ranked(overdue_days=59), as_of=date(2026, 9, 30), config=MsmedConfig()
    )
    assert eligible is not None and eligible.samadhaan_eligible is True  # 45+15
    assert not_yet is not None and not_yet.samadhaan_eligible is False  # 14d beyond


def test_custom_terms_shift_the_whole_calculation():
    """Agreed 30-day terms: overdue 60 -> 30 days beyond -> 1 month of
    interest, and the Samadhaan gate is 30+15=45 overdue, already open."""
    config = MsmedConfig(terms_days=30)
    pos = msmed_position(
        ranked(overdue_days=60), as_of=date(2026, 9, 30), config=config
    )
    assert pos.days_beyond_terms == 30
    assert pos.interest_accrued == Decimal("1625.00")  # 100000 × 0.01625
    assert pos.samadhaan_eligible is True  # 30 >= 15 notice days


def test_msmed_interest_uses_undisputed_base_for_mixed_accounts():
    """170k outstanding but 100k sits on disputed lines: §16 interest is
    computed on the 70k that matches the undisputed ageing, and the
    explanation says what was excluded. 70000 x (1.01625^3 - 1) = 3468.25."""
    account = RankedAccount(
        customer_id="CUST-1",
        legal_name="Acme",
        score=Decimal("100.00"),
        outstanding=Decimal("170000.00"),
        overdue_days=135,
        ageing_bucket="90_plus",
        eligible=True,
        policy_version="v1",
        explanation="outstanding_inr=170000.00",
        missing_inputs=(),
        disputed_outstanding=Decimal("100000.00"),
    )
    pos = msmed_position(account, as_of=date(2026, 9, 30), config=MsmedConfig())
    assert pos.interest_accrued == Decimal("3468.25")
    assert "disputed_excluded_inr=100000.00" in pos.explanation


def test_interest_is_capped_at_the_undisputed_outstanding():
    """A slipped decimal on --bank-rate (650%) must not mint interest larger
    than the principal: capped, and the explanation says so."""
    config = MsmedConfig(bank_rate_annual_pct=Decimal("650"))
    pos = msmed_position(
        ranked(overdue_days=135), as_of=date(2026, 9, 30), config=config
    )
    assert pos.interest_accrued == Decimal("100000.00")  # == base
    assert "capped" in pos.explanation
