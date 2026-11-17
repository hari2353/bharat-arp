"""MSMED delayed-payment lever — the "Bharat" differentiator no scanned
competitor implements. MSMED Act: a buyer who has not paid an MSME supplier
within the agreed terms (45 days absent agreement) owes compound interest
at three times the RBI bank rate, compounded monthly (§16), and the
supplier may file on MSME Samadhaan once the notice window also lapses
(§18; 15 days beyond the terms by default).

Deterministic math on the evidence ledger. The bank rate is a dated config
input, never fetched. Every result is a proposal input — nothing is filed,
sent, or claimed automatically.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .decisioning import RankedAccount

POLICY_VERSION = "msmed-2026-11"
TWO_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class MsmedConfig:
    msme_supplier: bool = True
    bank_rate_annual_pct: Decimal = Decimal("6.5")   # RBI bank rate, dated input
    terms_days: int = 45                             # MSMED default absent agreement
    notice_days: int = 15                            # §18 notice window
    policy_version: str = POLICY_VERSION


@dataclass(frozen=True)
class MsmedPosition:
    customer_id: str
    overdue_days: int
    days_beyond_terms: int
    interest_accrued: Decimal
    samadhaan_eligible: bool
    explanation: str
    policy_version: str


def msmed_position(
    ranked: RankedAccount, *, as_of: date, config: MsmedConfig
) -> MsmedPosition | None:
    """§16 interest accrued and §18 Samadhaan eligibility for one ranked
    account, or None when the lever does not apply. Deterministic: `as_of`
    and the bank rate are arguments, never the clock or the network."""
    if not config.msme_supplier:
        return None
    if not ranked.eligible or ranked.outstanding <= 0:
        return None
    days_beyond_terms = ranked.overdue_days - config.terms_days
    if days_beyond_terms <= 0:
        return None
    # §16: 3x bank rate per annum, compounded monthly. Interest accrues on
    # completed months only (floor-month approximation — stated in the
    # explanation so a reviewer can recompute by hand).
    monthly_rate = (
        Decimal(3) * config.bank_rate_annual_pct / Decimal(100) / Decimal(12)
    )
    months = days_beyond_terms // 30
    growth = (Decimal(1) + monthly_rate) ** months
    interest = (ranked.outstanding * (growth - Decimal(1))).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    samadhaan_eligible = days_beyond_terms >= config.notice_days
    explanation = (
        f"customer={ranked.customer_id}; overdue_days={ranked.overdue_days}; "
        f"terms_days={config.terms_days}; days_beyond_terms={days_beyond_terms}; "
        f"bank_rate={config.bank_rate_annual_pct}; rate=3x bank rate "
        f"compounded monthly; months={months}; "
        f"outstanding_inr={ranked.outstanding:.2f}; "
        f"interest_accrued_inr={interest:.2f}; "
        f"samadhaan_eligible={str(samadhaan_eligible).lower()} "
        f"(notice_days={config.notice_days})"
    )
    return MsmedPosition(
        customer_id=ranked.customer_id,
        overdue_days=ranked.overdue_days,
        days_beyond_terms=days_beyond_terms,
        interest_accrued=interest,
        samadhaan_eligible=samadhaan_eligible,
        explanation=explanation,
        policy_version=config.policy_version,
    )
