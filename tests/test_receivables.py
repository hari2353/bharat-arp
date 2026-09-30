from datetime import date

from bharat_arp.receivables import Invoice, propose_collection_action


def test_overdue_invoice_creates_approval_gated_whatsapp_action():
    invoice = Invoice(
        invoice_id="INV-1001",
        customer_name="Sharma Engineering",
        amount_inr=125000,
        due_date=date(2026, 9, 1),
        status="unpaid",
        customer_phone="+919876543210",
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
        customer_phone="+919876543211",
    )

    proposal = propose_collection_action(invoice, today=date(2026, 9, 30))

    assert proposal.action == "no_action"
    assert proposal.requires_approval is False


def test_missing_phone_number_is_never_sent_to_whatsapp():
    invoice = Invoice(
        invoice_id="INV-1003",
        customer_name="No Phone Customer",
        amount_inr=2500,
        due_date=date(2026, 9, 1),
        status="unpaid",
        customer_phone=None,
    )

    proposal = propose_collection_action(invoice, today=date(2026, 9, 30))

    assert proposal.action == "draft_customer_follow_up"
    assert proposal.channel == "email"
    assert proposal.requires_approval is True
