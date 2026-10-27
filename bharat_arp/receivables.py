"""Approval-gated receivables decisions.

This module contains deterministic policy logic only. It proposes an action;
an integration worker must perform any external side effect after approval.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


CommunicationChannel = Literal["whatsapp", "email"]
CommunicationEligibilityState = Literal[
    "eligible", "unknown", "denied", "opted_out", "stale", "conflicting"
]


@dataclass(frozen=True)
class CommunicationEligibility:
    contact_id: str
    contact_role: str
    channel: CommunicationChannel
    state: CommunicationEligibilityState
    evidence_source: str
    observed_at: datetime


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    customer_name: str
    amount_inr: int
    due_date: date
    status: Literal["unpaid", "paid", "cancelled"]
    communication_eligibility: CommunicationEligibility | None


@dataclass(frozen=True)
class CollectionProposal:
    invoice_id: str
    action: Literal["draft_customer_follow_up", "review_required", "no_action"]
    channel: Literal["whatsapp", "email", "none"]
    reason: str
    requires_approval: bool


def propose_collection_action(invoice: Invoice, *, today: date) -> CollectionProposal:
    """Return the safest next step for one invoice.

    Every customer contact remains approval-gated. The function does not call
    WhatsApp, email, ERPNext, or any other external service.
    """
    if invoice.status != "unpaid" or invoice.due_date >= today:
        return CollectionProposal(
            invoice_id=invoice.invoice_id,
            action="no_action",
            channel="none",
            reason="Invoice is not overdue and unpaid.",
            requires_approval=False,
        )

    eligibility = invoice.communication_eligibility
    if eligibility is None or eligibility.state in {
        "unknown",
        "stale",
        "conflicting",
    }:
        return CollectionProposal(
            invoice_id=invoice.invoice_id,
            action="review_required",
            channel="none",
            reason="Communication eligibility requires human review.",
            requires_approval=True,
        )

    if eligibility.state in {"denied", "opted_out"}:
        return CollectionProposal(
            invoice_id=invoice.invoice_id,
            action="no_action",
            channel="none",
            reason="Customer contact is denied or opted out.",
            requires_approval=False,
        )

    days_overdue = (today - invoice.due_date).days
    return CollectionProposal(
        invoice_id=invoice.invoice_id,
        action="draft_customer_follow_up",
        channel=eligibility.channel,
        reason=(
            f"Invoice {invoice.invoice_id} for INR {invoice.amount_inr} is "
            f"{days_overdue} days overdue."
        ),
        requires_approval=True,
    )
