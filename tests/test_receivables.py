from datetime import date, datetime, timezone

from bharat_arp.receivables import (
    CommunicationEligibility,
    Invoice,
    propose_collection_action,
)


def eligible_whatsapp_contact():
    return CommunicationEligibility(
        contact_id="CONTACT-1001",
        contact_role="accounts_payable",
        channel="whatsapp",
        state="eligible",
        evidence_source="customer_permission_record",
        observed_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
    )


def test_overdue_invoice_creates_approval_gated_whatsapp_action():
    invoice = Invoice(
        invoice_id="INV-1001",
        customer_name="Sharma Engineering",
        amount_inr=125000,
        due_date=date(2026, 9, 1),
        status="unpaid",
        communication_eligibility=eligible_whatsapp_contact(),
    )

    proposal = propose_collection_action(invoice, today=date(2026, 9, 30))

    assert proposal.action == "draft_customer_follow_up"
    assert proposal.channel == "whatsapp"
    assert proposal.requires_approval is True
    assert proposal.invoice_id == "INV-1001"
    assert "125000" in proposal.reason


def test_paid_invoice_does_not_create_action():
    invoice = Invoice(
        invoice_id="INV-1002",
        customer_name="Kumar Traders",
        amount_inr=5000,
        due_date=date(2026, 9, 1),
        status="paid",
        communication_eligibility=eligible_whatsapp_contact(),
    )

    proposal = propose_collection_action(invoice, today=date(2026, 9, 30))

    assert proposal.action == "no_action"
    assert proposal.requires_approval is False


def test_phone_number_without_permission_evidence_requires_review():
    invoice = Invoice(
        invoice_id="INV-1003",
        customer_name="No Phone Customer",
        amount_inr=2500,
        due_date=date(2026, 9, 1),
        status="unpaid",
        communication_eligibility=None,
    )

    proposal = propose_collection_action(invoice, today=date(2026, 9, 30))

    assert proposal.action == "review_required"
    assert proposal.channel == "none"
    assert proposal.requires_approval is True


def test_unknown_permission_never_creates_customer_contact_proposal():
    invoice = Invoice(
        invoice_id="INV-1004",
        customer_name="Unknown Permission Customer",
        amount_inr=2500,
        due_date=date(2026, 9, 1),
        status="unpaid",
        communication_eligibility=CommunicationEligibility(
            contact_id="CONTACT-1004",
            contact_role="accounts_payable",
            channel="email",
            state="unknown",
            evidence_source="erpnext_export",
            observed_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
        ),
    )

    proposal = propose_collection_action(invoice, today=date(2026, 9, 30))

    assert proposal.action == "review_required"
    assert proposal.channel == "none"


def test_opted_out_contact_creates_no_action():
    invoice = Invoice(
        invoice_id="INV-1005",
        customer_name="Opted Out Customer",
        amount_inr=2500,
        due_date=date(2026, 9, 1),
        status="unpaid",
        communication_eligibility=CommunicationEligibility(
            contact_id="CONTACT-1005",
            contact_role="accounts_payable",
            channel="whatsapp",
            state="opted_out",
            evidence_source="customer_opt_out",
            observed_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
        ),
    )

    proposal = propose_collection_action(invoice, today=date(2026, 9, 30))

    assert proposal.action == "no_action"
    assert proposal.channel == "none"
    assert proposal.requires_approval is False
