"""Explainable, deterministic account-level collection prioritization."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class AccountExposure:
    invoice_id: str
    outstanding: Decimal
    due_date: date
    reconciliation_state: str


@dataclass(frozen=True)
class CustomerAccount:
    customer_id: str
    legal_name: str
    exposures: tuple[AccountExposure, ...]
    broken_promises: int = 0
    unresolved_dispute: bool = False
    payment_history_available: bool = False
    data_quality_exceptions: tuple[str, ...] = ()
    disputed_invoice_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RankedAccount:
    customer_id: str
    legal_name: str
    score: Decimal
    outstanding: Decimal
    overdue_days: int
    ageing_bucket: str
    eligible: bool
    policy_version: str
    explanation: str
    missing_inputs: tuple[str, ...]
    disputed_outstanding: Decimal = Decimal("0.00")


def _ageing_bucket(overdue_days: int) -> str:
    if overdue_days <= 0:
        return "not_due"
    if overdue_days < 30:
        return "1_29"
    if overdue_days < 60:
        return "30_59"
    if overdue_days < 90:
        return "60_89"
    return "90_plus"


def rank_accounts(
    accounts: list[CustomerAccount], *, as_of: date, policy_version: str
) -> tuple[RankedAccount, ...]:
    ranked: list[RankedAccount] = []
    for account in accounts:
        outstanding = sum(
            (exposure.outstanding for exposure in account.exposures), Decimal("0.00")
        )
        overdue_exposures = [
            exposure
            for exposure in account.exposures
            if exposure.due_date < as_of and exposure.outstanding > 0
        ]
        # Dispute containment (market-steal, Kolleno): contested lines drop
        # out of the chase set instead of freezing the account. A bare
        # unresolved_dispute boolean without invoice ids cannot isolate the
        # contested lines, so that caller keeps the legacy contract exactly
        # (ranking on the whole account, open_dispute missing input blocks
        # the contact proposal, eligibility unchanged).
        disputed_ids = account.disputed_invoice_ids
        legacy_dispute = account.unresolved_dispute and not disputed_ids
        if legacy_dispute:
            # no line attribution: report nothing as disputed — claiming the
            # whole overdue balance is "disputed" is knowledge we do not have
            disputed_overdue = overdue_exposures
            chaseable = overdue_exposures
            undisputed_outstanding = outstanding
        else:
            disputed_overdue = [
                e for e in overdue_exposures if e.invoice_id in disputed_ids
            ]
            chaseable = [
                e for e in overdue_exposures if e.invoice_id not in disputed_ids
            ]
            undisputed_outstanding = sum(
                (e.outstanding for e in account.exposures
                 if e.invoice_id not in disputed_ids),
                Decimal("0.00"),
            )
        disputed_outstanding = sum(
            (e.outstanding for e in disputed_overdue), Decimal("0.00")
        ) if not legacy_dispute else Decimal("0.00")
        overdue_days = max(
            ((as_of - exposure.due_date).days for exposure in chaseable),
            default=0,
        )
        ageing_bucket = _ageing_bucket(overdue_days)
        missing_inputs = []
        if not account.payment_history_available:
            missing_inputs.append("payment_history")
        if not account.exposures:
            missing_inputs.append("outstanding_exposure")

        eligible = bool(chaseable) and not account.data_quality_exceptions
        if outstanding < 0:
            eligible = False
            missing_inputs.append("overpayment_review")
        if legacy_dispute or (disputed_overdue and not chaseable):
            missing_inputs.append("open_dispute")
        missing_inputs.extend(account.data_quality_exceptions)

        if eligible:
            score = (
                undisputed_outstanding
                + Decimal(overdue_days * 100)
                + Decimal(account.broken_promises * 10000)
            )
        else:
            score = Decimal("0.00")

        explanation = (
            f"outstanding_inr={outstanding:.2f}; "
            f"overdue_days={overdue_days}; ageing_bucket={ageing_bucket}; "
            f"broken_promises={account.broken_promises}"
        )
        if legacy_dispute:
            explanation += "; dispute_lines_unattributed=true"
        if disputed_overdue and chaseable and not legacy_dispute:
            explanation += (
                f"; undisputed_outstanding_inr={undisputed_outstanding:.2f};"
                f" dispute_contained_invoices={len(disputed_overdue)}"
            )
        if missing_inputs:
            explanation += f"; missing_or_risk_inputs={','.join(missing_inputs)}"
        if not eligible:
            explanation += "; not eligible for collection action"
        ranked.append(
            RankedAccount(
                customer_id=account.customer_id,
                legal_name=account.legal_name,
                score=score,
                outstanding=outstanding,
                overdue_days=overdue_days,
                ageing_bucket=ageing_bucket,
                eligible=eligible,
                policy_version=policy_version,
                explanation=explanation,
                missing_inputs=tuple(missing_inputs),
                disputed_outstanding=disputed_outstanding,
            )
        )

    return tuple(
        sorted(ranked, key=lambda item: (-item.score, item.customer_id))
    )
