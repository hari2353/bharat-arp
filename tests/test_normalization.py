from datetime import datetime, timezone
from decimal import Decimal

from bharat_arp.normalization import NormalizedSourceStore


COMMON = {
    "tenant_id": "TENANT-1",
    "source_system": "erpnext_csv",
    "source_updated_at": "2026-09-30T10:00:00+05:30",
    "import_batch_id": "BATCH-1",
}


def invoice_row(*, amount: str = "1000.00", batch: str = "BATCH-1") -> dict[str, str]:
    return {
        **COMMON,
        "import_batch_id": batch,
        "source_record_id": "INV-1",
        "source_invoice_id": "INV-1",
        "source_customer_id": "CUST-1",
        "invoice_date": "2026-08-01",
        "due_date": "2026-09-01",
        "amount_inr": amount,
        "status": "submitted",
    }


def test_identical_source_replay_is_a_noop():
    store = NormalizedSourceStore()

    first = store.upsert_rows("invoices", [invoice_row()])
    second = store.upsert_rows("invoices", [invoice_row()])

    assert first.created == 1
    assert first.updated == 0
    assert second.created == 0
    assert second.updated == 0
    assert second.unchanged == 1
    assert len(store.current_records("invoices")) == 1


def test_corrected_source_record_preserves_history_and_updates_current_value():
    store = NormalizedSourceStore()
    store.upsert_rows("invoices", [invoice_row()])

    corrected = invoice_row(amount="1250.00", batch="BATCH-2")
    corrected["source_updated_at"] = "2026-10-01T10:00:00+05:30"
    result = store.upsert_rows("invoices", [corrected])

    current = store.current_records("invoices")[0]
    assert result.updated == 1
    assert current.amount_inr == Decimal("1250.00")
    assert len(store.history("invoices", "INV-1")) == 2


def test_tenant_mismatch_and_bad_amount_are_rejected_without_persisting():
    store = NormalizedSourceStore()
    bad_tenant = invoice_row()
    bad_tenant["tenant_id"] = "TENANT-2"
    bad_amount = invoice_row(amount="not-money")
    bad_amount["source_record_id"] = "INV-2"
    bad_amount["source_invoice_id"] = "INV-2"

    result = store.upsert_rows("invoices", [bad_tenant, bad_amount])

    assert result.created == 0
    assert {error.code for error in result.errors} == {
        "tenant_mismatch",
        "invalid_amount",
    }
    assert store.current_records("invoices") == ()


def test_source_status_is_preserved_for_explicit_cancellation():
    store = NormalizedSourceStore()
    cancelled = invoice_row()
    cancelled["status"] = "cancelled"

    store.upsert_rows("invoices", [cancelled])

    assert store.current_records("invoices")[0].status == "cancelled"


def test_source_system_is_part_of_identity():
    store = NormalizedSourceStore()
    first = invoice_row()
    second = invoice_row()
    second["source_system"] = "manual_csv"

    result = store.upsert_rows("invoices", [first, second])

    assert result.created == 2
    assert len(store.current_records("invoices")) == 2


def test_open_dispute_is_normalized_as_a_workflow_risk_fact():
    store = NormalizedSourceStore()
    row = {
        **COMMON,
        "source_record_id": "DISP-1",
        "source_dispute_id": "DISP-1",
        "source_customer_id": "CUST-1",
        "source_invoice_id": "INV-1",
        "category": "quantity_mismatch",
        "status": "open",
        "opened_at": "2026-09-15T10:00:00+05:30",
        "resolved_at": "",
    }

    result = store.upsert_rows("disputes", [row])

    assert result.created == 1
    assert store.current_records("disputes")[0].status == "open"
