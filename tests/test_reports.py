from decimal import Decimal

from bharat_arp.decisioning import RankedAccount
from bharat_arp.reports import render_queue_csv, render_queue_html, render_queue_text


def ranked() -> RankedAccount:
    return RankedAccount(
        customer_id="CUST-1",
        legal_name="=Unsafe Customer",
        score=Decimal("125100.00"),
        outstanding=Decimal("125000.00"),
        overdue_days=90,
        ageing_bucket="90_plus",
        eligible=True,
        policy_version="v1",
        explanation="verified overdue exposure",
        missing_inputs=("payment_history",),
    )


def test_text_queue_contains_ranked_evidence():
    output = render_queue_text([ranked()])

    assert "customer==Unsafe Customer" in output
    assert "outstanding=125000.00" in output
    assert "risks=payment_history" in output


def test_csv_queue_neutralizes_formula_values():
    output = render_queue_csv([ranked()])

    assert "'=Unsafe Customer" in output
    assert "policy_version" in output


def test_html_queue_escapes_values():
    output = render_queue_html([ranked()])

    assert "&lt;" not in output
    assert "=Unsafe Customer" in output
    assert "<table>" in output
