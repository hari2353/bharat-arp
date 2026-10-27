from datetime import datetime, timezone
from decimal import Decimal

from bharat_arp.decisioning import RankedAccount
from bharat_arp.proposals import propose_account_action
from bharat_arp.receivables import CommunicationEligibility


def ranked(*, eligible: bool = True, missing_inputs: tuple[str, ...] = ()):
    return RankedAccount(
        customer_id="CUST-1",
        legal_name="Sharma Engineering",
        score=Decimal("130000.00"),
        outstanding=Decimal("125000.00"),
        overdue_days=90,
        ageing_bucket="90_plus",
        eligible=eligible,
        policy_version="v1",
        explanation="outstanding_inr=125000.00; overdue_days=90",
        missing_inputs=missing_inputs,
    )


def contact(state: str):
    return CommunicationEligibility(
        contact_id="CONTACT-1",
        contact_role="accounts_payable",
        channel="email",
        state=state,
        evidence_source="customer_permission_record",
        observed_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
    )


def test_eligible_contact_creates_draft_only_proposal_with_evidence():
    proposal = propose_account_action(ranked(), contact=contact("eligible"))

    assert proposal.action == "draft_customer_follow_up"
    assert proposal.channel == "email"
    assert proposal.requires_approval is True
    assert proposal.executes_side_effect is False
    assert proposal.policy_version == "v1"
    assert proposal.source_customer_id == "CUST-1"


def test_unknown_contact_creates_review_proposal_not_contact_draft():
    proposal = propose_account_action(ranked(), contact=contact("unknown"))

    assert proposal.action == "review_required"
    assert proposal.channel == "none"
    assert proposal.requires_approval is True
    assert proposal.executes_side_effect is False


def test_open_dispute_blocks_customer_contact():
    proposal = propose_account_action(
        ranked(missing_inputs=("open_dispute",)), contact=contact("eligible")
    )

    assert proposal.action == "review_required"
    assert proposal.channel == "none"
    assert "open_dispute" in proposal.reason


def test_ineligible_account_produces_no_action():
    proposal = propose_account_action(ranked(eligible=False), contact=contact("eligible"))

    assert proposal.action == "no_action"
    assert proposal.requires_approval is False
