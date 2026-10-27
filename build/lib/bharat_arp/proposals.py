"""Non-mutating collection proposals built from ranked account evidence."""

from dataclasses import dataclass
from decimal import Decimal

from .decisioning import RankedAccount
from .receivables import CommunicationEligibility


@dataclass(frozen=True)
class AccountProposal:
    source_customer_id: str
    action: str
    channel: str
    reason: str
    expected_outcome: str
    policy_version: str
    requires_approval: bool
    executes_side_effect: bool
    outstanding: Decimal


def propose_account_action(
    ranked_account: RankedAccount, *, contact: CommunicationEligibility | None
) -> AccountProposal:
    """Create a proposal; this function cannot send or mutate external records."""
    if not ranked_account.eligible:
        return AccountProposal(
            source_customer_id=ranked_account.customer_id,
            action="no_action",
            channel="none",
            reason="Account is not eligible for collection action.",
            expected_outcome="No customer contact or external mutation.",
            policy_version=ranked_account.policy_version,
            requires_approval=False,
            executes_side_effect=False,
            outstanding=ranked_account.outstanding,
        )

    risk_inputs = set(ranked_account.missing_inputs)
    if "open_dispute" in risk_inputs:
        return _review(ranked_account, "open_dispute requires evidence review.")
    if contact is None or contact.state in {"unknown", "stale", "conflicting"}:
        return _review(ranked_account, "Communication eligibility requires human review.")
    if contact.state in {"denied", "opted_out"}:
        return AccountProposal(
            source_customer_id=ranked_account.customer_id,
            action="no_action",
            channel="none",
            reason="Customer contact is denied or opted out.",
            expected_outcome="No customer contact or external mutation.",
            policy_version=ranked_account.policy_version,
            requires_approval=False,
            executes_side_effect=False,
            outstanding=ranked_account.outstanding,
        )

    return AccountProposal(
        source_customer_id=ranked_account.customer_id,
        action="draft_customer_follow_up",
        channel=contact.channel,
        reason=ranked_account.explanation,
        expected_outcome="Approved customer follow-up and recorded payment promise.",
        policy_version=ranked_account.policy_version,
        requires_approval=True,
        executes_side_effect=False,
        outstanding=ranked_account.outstanding,
    )


def _review(ranked_account: RankedAccount, reason: str) -> AccountProposal:
    return AccountProposal(
        source_customer_id=ranked_account.customer_id,
        action="review_required",
        channel="none",
        reason=reason,
        expected_outcome="Resolve evidence before considering customer contact.",
        policy_version=ranked_account.policy_version,
        requires_approval=True,
        executes_side_effect=False,
        outstanding=ranked_account.outstanding,
    )
