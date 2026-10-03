import json
from decimal import Decimal
from pathlib import Path

from bharat_arp.cli import _state_from_store, _store_from_state, run
from bharat_arp.workflow import WorkflowStore


def test_cli_init_and_queue_are_tenant_scoped(tmp_path: Path, capsys):
    workspace = tmp_path / "workspace"

    assert run(["--workspace", str(workspace), "init", "--tenant", "TENANT-1"]) == 0
    assert run(["--workspace", str(workspace), "queue", "--tenant", "TENANT-1"]) == 0

    output = capsys.readouterr().out
    assert "TENANT-1" in output


def test_cli_proposal_decision_and_promise_record_write_audit(tmp_path: Path, capsys):
    workspace = tmp_path / "workspace"
    run(["--workspace", str(workspace), "init", "--tenant", "TENANT-1"])
    run(
        [
            "--workspace",
            str(workspace),
            "proposal",
            "create",
            "--tenant",
            "TENANT-1",
            "--proposal",
            "PROP-1",
            "--customer",
            "CUST-1",
        ]
    )
    run(
        [
            "--workspace",
            str(workspace),
            "proposal",
            "decide",
            "--tenant",
            "TENANT-1",
            "--proposal",
            "PROP-1",
            "--decision",
            "approve",
        ]
    )
    run(
        [
            "--workspace",
            str(workspace),
            "promise",
            "record",
            "--tenant",
            "TENANT-1",
            "--promise",
            "PROMISE-1",
            "--customer",
            "CUST-1",
            "--amount",
            "125000.00",
            "--due",
            "2026-10-15",
        ]
    )

    state = json.loads((workspace / "TENANT-1" / "state.json").read_text())
    assert state["proposals"][0]["status"] == "approved"
    assert state["promises"][0]["status"] == "proposed"
    assert [
        event["action"] for event in state["audit"] if not event["action"].startswith("command_")
    ] == [
        "proposal_created",
        "proposal_approved",
        "promise_recorded",
    ]
    assert "approved" in capsys.readouterr().out


def test_cli_rejects_tenant_path_traversal(tmp_path: Path):
    workspace = tmp_path / "workspace"

    assert run(["--workspace", str(workspace), "init", "--tenant", "../other"]) == 2


def test_cli_export_neutralizes_formula_values_and_purge_removes_tenant(tmp_path: Path):
    workspace = tmp_path / "workspace"
    run(["--workspace", str(workspace), "init", "--tenant", "TENANT-1"])
    state_path = workspace / "TENANT-1" / "state.json"
    state = json.loads(state_path.read_text())
    state["audit"].append(
        {
            "sequence": 1,
            "tenant_id": "TENANT-1",
            "actor_id": "pilot_operator",
            "action": "=HYPERLINK(\"https://evil.example\")",
            "object_id": "OBJ-1",
            "occurred_at": "2026-09-30T00:00:00+00:00",
        }
    )
    state_path.write_text(json.dumps(state))

    output = workspace / "export"
    assert (
        run(
            [
                "--workspace",
                str(workspace),
                "export",
                "--tenant",
                "TENANT-1",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert "'=HYPERLINK" in (output / "audit.csv").read_text()

    assert run(["--workspace", str(workspace), "purge", "--tenant", "TENANT-1"]) == 2
    assert run(["--workspace", str(workspace), "purge", "--tenant", "TENANT-1", "--confirm"]) == 0
    assert not (workspace / "TENANT-1").exists()


def test_cli_legal_hold_blocks_purge_and_purge_writes_tombstone(tmp_path: Path):
    workspace = tmp_path / "workspace"
    run(["--workspace", str(workspace), "init", "--tenant", "TENANT-1"])

    assert run(
        [
            "--workspace",
            str(workspace),
            "hold",
            "add",
            "--tenant",
            "TENANT-1",
            "--hold",
            "HOLD-1",
            "--reason",
            "customer dispute",
        ]
    ) == 0
    assert run(
        ["--workspace", str(workspace), "purge", "--tenant", "TENANT-1", "--confirm"]
    ) == 2
    assert (workspace / "TENANT-1" / "state.json").exists()

    assert run(
        [
            "--workspace",
            str(workspace),
            "hold",
            "remove",
            "--tenant",
            "TENANT-1",
            "--hold",
            "HOLD-1",
        ]
    ) == 0
    assert run(
        [
            "--workspace",
            str(workspace),
            "purge",
            "--tenant",
            "TENANT-1",
            "--confirm",
            "--reason",
            "pilot ended",
        ]
    ) == 0
    tombstone = workspace / ".purged" / "TENANT-1.json"
    assert not (workspace / "TENANT-1").exists()
    tombstone_state = json.loads(tombstone.read_text())
    assert tombstone_state["tenant_id"] == "DELETED-TENANT-1"
    assert tombstone_state["purge"]["reason"] == "pilot ended"
    assert tombstone_state["audit"][0]["tenant_id"] == "DELETED-TENANT-1"


def test_cli_export_rejects_path_outside_workspace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    run(["--workspace", str(workspace), "init", "--tenant", "TENANT-1"])

    assert run(
        [
            "--workspace",
            str(workspace),
            "export",
            "--tenant",
            "TENANT-1",
            "--output",
            str(tmp_path / "outside"),
        ]
    ) == 2


def test_cli_rejects_tenant_state_mismatch(tmp_path: Path):
    workspace = tmp_path / "workspace"
    run(["--workspace", str(workspace), "init", "--tenant", "TENANT-1"])
    state_path = workspace / "TENANT-1" / "state.json"
    state = json.loads(state_path.read_text())
    state["tenant_id"] = "TENANT-2"
    state_path.write_text(json.dumps(state))

    assert run(["--workspace", str(workspace), "metrics", "--tenant", "TENANT-1"]) == 2


def test_cli_retention_expires_raw_import_batches_but_respects_hold(tmp_path: Path):
    workspace = tmp_path / "workspace"
    run(["--workspace", str(workspace), "init", "--tenant", "TENANT-1"])
    state_path = workspace / "TENANT-1" / "state.json"
    state = json.loads(state_path.read_text())
    state["raw_imports"] = [
        {"batch": "OLD", "imported_at": "2026-01-01T00:00:00+00:00", "rows": {}}
    ]
    state["source_rows"] = {
        "invoices": [{"import_batch_id": "OLD", "source_record_id": "INV-1"}],
        "customers": [{"import_batch_id": "NEW", "source_record_id": "CUST-1"}],
    }
    state["holds"] = [{"hold_id": "HOLD-1", "reason": "review", "active": True}]
    state_path.write_text(json.dumps(state))

    assert run(
        [
            "--workspace", str(workspace), "retention", "apply", "--tenant", "TENANT-1",
            "--as-of", "2026-10-03",
        ]
    ) == 2
    assert json.loads(state_path.read_text())["raw_imports"]

    state["holds"][0]["active"] = False
    state_path.write_text(json.dumps(state))
    assert run(
        [
            "--workspace", str(workspace), "retention", "apply", "--tenant", "TENANT-1",
            "--as-of", "2026-10-03",
        ]
    ) == 0
    retained_state = json.loads(state_path.read_text())
    assert retained_state["raw_imports"] == []
    assert retained_state["source_rows"]["invoices"] == []
    assert len(retained_state["source_rows"]["customers"]) == 1


def test_cli_case_outcome_and_metrics_are_persisted(tmp_path: Path, capsys):
    workspace = tmp_path / "workspace"
    run(["--workspace", str(workspace), "init", "--tenant", "TENANT-1"])
    run(
        [
            "--workspace",
            str(workspace),
            "case",
            "create",
            "--tenant",
            "TENANT-1",
            "--case",
            "CASE-1",
            "--customer",
            "CUST-1",
        ]
    )
    run(
        [
            "--workspace",
            str(workspace),
            "case",
            "show",
            "--tenant",
            "TENANT-1",
            "--case",
            "CASE-1",
        ]
    )
    run(
        [
            "--workspace",
            str(workspace),
            "outcome",
            "record",
            "--tenant",
            "TENANT-1",
            "--case",
            "CASE-1",
            "--outcome",
            "payment_received",
        ]
    )
    run(["--workspace", str(workspace), "metrics", "--tenant", "TENANT-1"])

    state = json.loads((workspace / "TENANT-1" / "state.json").read_text())
    assert state["cases"][0]["case_id"] == "CASE-1"
    assert state["outcomes"][0]["outcome"] == "payment_received"
    assert "cases=1" in capsys.readouterr().out


def test_cli_metrics_accepts_window_and_json_format(tmp_path: Path, capsys):
    workspace = tmp_path / "workspace"
    run(["--workspace", str(workspace), "init", "--tenant", "TENANT-1"])

    assert run(
        [
            "--workspace",
            str(workspace),
            "metrics",
            "--tenant",
            "TENANT-1",
            "--from",
            "2026-09-01",
            "--to",
            "2026-10-31",
            "--format",
            "json",
        ]
    ) == 0

    assert '"from": "2026-09-01"' in capsys.readouterr().out


def test_cli_metrics_persists_idempotent_weekly_snapshot(tmp_path: Path, capsys):
    workspace = tmp_path / "workspace"
    run(["--workspace", str(workspace), "init", "--tenant", "TENANT-1"])

    assert run(
        [
            "--workspace", str(workspace), "metrics", "--tenant", "TENANT-1",
            "--snapshot", "2026-09-30", "--format", "json",
        ]
    ) == 0
    assert run(
        [
            "--workspace", str(workspace), "metrics", "--tenant", "TENANT-1",
            "--snapshot", "2026-09-30", "--format", "json",
        ]
    ) == 0

    state = json.loads((workspace / "TENANT-1" / "state.json").read_text())
    assert len(state["snapshots"]) == 1
    assert state["snapshots"][0]["as_of"] == "2026-09-30"
    assert "snapshot" in capsys.readouterr().out


def test_cli_state_round_trip_preserves_workflow_statuses():
    store = WorkflowStore(tenant_id="TENANT-1", operator_id="pilot_operator")
    store.create_proposal(
        proposal_id="PROP-1",
        customer_id="CUST-1",
        policy_version="v1",
        evidence_fingerprint="evidence-1",
        action="draft_customer_follow_up",
    )
    store.mark_proposal_stale("PROP-1", new_evidence_fingerprint="evidence-2")
    store.record_promise(
        promise_id="PROMISE-1",
        customer_id="CUST-1",
        amount=Decimal("125000.00"),
        due_on="2026-10-15",
        source="phone_call",
    )
    store.transition_promise("PROMISE-1", "accepted")
    store.transition_promise("PROMISE-1", "broken")
    store.create_case(case_id="CASE-1", customer_id="CUST-1")
    store.transition_case("CASE-1", "open")
    store.assign_case("CASE-1", assignee_id="pilot_operator")
    store.transition_case("CASE-1", "in_progress")
    store.transition_case("CASE-1", "resolved")

    restored = _store_from_state(_state_from_store(store))

    assert restored.proposals()[0].status == "stale"
    assert restored.promises()[0].status == "broken"
    assert restored.cases()[0].status == "resolved"


def test_cli_supports_assignment_edits_rejection_reasons_and_partial_fulfilment(
    tmp_path: Path, capsys
):
    workspace = tmp_path / "workspace"
    run(["--workspace", str(workspace), "init", "--tenant", "TENANT-1"])
    run(
        [
            "--workspace", str(workspace), "case", "create", "--tenant", "TENANT-1",
            "--case", "CASE-1", "--customer", "CUST-1",
        ]
    )
    run(
        [
            "--workspace", str(workspace), "case", "transition", "--tenant", "TENANT-1",
            "--case", "CASE-1", "--status", "open",
        ]
    )
    run(
        [
            "--workspace", str(workspace), "case", "assign", "--tenant", "TENANT-1",
            "--case", "CASE-1", "--assignee", "operator-2",
        ]
    )
    run(
        [
            "--workspace", str(workspace), "proposal", "create", "--tenant", "TENANT-1",
            "--proposal", "PROP-1", "--customer", "CUST-1",
        ]
    )
    run(
        [
            "--workspace", str(workspace), "proposal", "edit", "--tenant", "TENANT-1",
            "--proposal", "PROP-1", "--action", "review_required", "--evidence", "e2",
        ]
    )
    run(
        [
            "--workspace", str(workspace), "proposal", "decide", "--tenant", "TENANT-1",
            "--proposal", "PROP-1", "--decision", "reject", "--reason", "not ready",
        ]
    )
    run(
        [
            "--workspace", str(workspace), "promise", "record", "--tenant", "TENANT-1",
            "--promise", "PROMISE-1", "--customer", "CUST-1", "--amount", "100.00",
            "--due", "2026-10-15",
        ]
    )
    run(
        [
            "--workspace", str(workspace), "promise", "transition", "--tenant", "TENANT-1",
            "--promise", "PROMISE-1", "--status", "accepted",
        ]
    )
    run(
        [
            "--workspace", str(workspace), "promise", "fulfil", "--tenant", "TENANT-1",
            "--promise", "PROMISE-1", "--amount", "40.00",
        ]
    )

    state = json.loads((workspace / "TENANT-1" / "state.json").read_text())
    assert state["cases"][0]["status"] == "assigned"
    assert state["cases"][0]["assignee_id"] == "operator-2"
    assert state["proposals"][0]["rejection_reason"] == "not ready"
    assert state["promises"][0]["status"] == "partial"
    assert state["promises"][0]["fulfilled_amount"] == "40.00"
    assert "partial" in capsys.readouterr().out


def test_cli_import_and_queue_rank_imported_customer_accounts(tmp_path: Path, capsys):
    workspace = tmp_path / "workspace"
    source = workspace / "input"
    source.mkdir(parents=True)
    common = "tenant_id,source_system,source_record_id,source_updated_at,import_batch_id"
    (source / "customers.csv").write_text(
        f"{common},source_customer_id,legal_name,status\n"
        "TENANT-1,erpnext_csv,CUST-1,2026-09-30T10:00:00+05:30,BATCH-1,CUST-1,Acme,active\n"
    )
    (source / "invoices.csv").write_text(
        f"{common},source_invoice_id,source_customer_id,invoice_date,due_date,amount_inr,status\n"
        "TENANT-1,erpnext_csv,INV-1,2026-09-30T10:00:00+05:30,BATCH-1,INV-1,CUST-1,2026-07-01,2026-08-01,125000.00,overdue\n"
    )
    (source / "payments.csv").write_text(
        f"{common},source_payment_id,payment_date,amount_inr,status\n"
        "TENANT-1,erpnext_csv,PAY-1,2026-09-30T10:00:00+05:30,BATCH-1,PAY-1,2026-09-01,25000.00,posted\n"
    )
    (source / "payment_allocations.csv").write_text(
        f"{common},source_payment_id,source_invoice_id,allocated_amount_inr\n"
        "TENANT-1,erpnext_csv,ALLOC-1,2026-09-30T10:00:00+05:30,BATCH-1,PAY-1,INV-1,25000.00\n"
    )
    (source / "credit_notes.csv").write_text(
        f"{common},source_credit_note_id,source_invoice_id,credit_date,amount_inr,status\n"
        "TENANT-1,erpnext_csv,CN-1,2026-09-30T10:00:00+05:30,BATCH-1,CN-1,INV-1,2026-08-15,0.00,posted\n"
    )
    (source / "contacts.csv").write_text(
        f"{common},source_contact_id,source_customer_id,display_name,role,email,phone,email_permission,whatsapp_permission,opted_out,permission_observed_at\n"
        "TENANT-1,erpnext_csv,CONTACT-1,2026-09-30T10:00:00+05:30,BATCH-1,CONTACT-1,CUST-1,Accounts Payable,AP,ap@example.com,+919999999999,eligible,unknown,false,2026-09-30T10:00:00+05:30\n"
    )
    (source / "disputes.csv").write_text(
        f"{common},source_dispute_id,source_customer_id,source_invoice_id,category,status,opened_at,resolved_at\n"
        "TENANT-1,erpnext_csv,DISP-1,2026-09-30T10:00:00+05:30,BATCH-1,DISP-1,CUST-1,INV-1,none,resolved,2026-08-01T10:00:00+05:30,2026-08-02T10:00:00+05:30\n"
    )

    assert run(
        [
            "--workspace",
            str(workspace),
            "import",
            "--tenant",
            "TENANT-1",
            "--batch",
            "BATCH-1",
            "--input",
            str(source),
        ]
    ) == 0
    assert run(
        [
            "--workspace",
            str(workspace),
            "import",
            "--tenant",
            "TENANT-1",
            "--batch",
            "BATCH-1",
            "--input",
            str(source),
        ]
    ) == 0
    assert run(
        [
            "--workspace",
            str(workspace),
            "queue",
            "--tenant",
            "TENANT-1",
            "--as-of",
            "2026-09-30",
        ]
    ) == 0

    output = capsys.readouterr().out
    assert "Acme" in output
    assert "100000.00" in output
    state = json.loads((workspace / "TENANT-1" / "state.json").read_text())
    assert len(state["imports"]) == 1
    assert all(len(rows) == 1 for rows in state["source_rows"].values())


def test_cli_workflow_mutations_preserve_imported_source_rows(tmp_path: Path, capsys):
    workspace = tmp_path / "workspace"
    source = workspace / "input"
    source.mkdir(parents=True)
    common = "tenant_id,source_system,source_record_id,source_updated_at,import_batch_id"
    (source / "customers.csv").write_text(
        f"{common},source_customer_id,legal_name,status\n"
        "TENANT-1,erpnext_csv,CUST-1,2026-09-30T10:00:00+05:30,BATCH-1,CUST-1,Acme,active\n"
    )
    (source / "invoices.csv").write_text(
        f"{common},source_invoice_id,source_customer_id,invoice_date,due_date,amount_inr,status\n"
        "TENANT-1,erpnext_csv,INV-1,2026-09-30T10:00:00+05:30,BATCH-1,INV-1,CUST-1,2026-07-01,2026-08-01,125000.00,overdue\n"
    )
    (source / "payments.csv").write_text(
        f"{common},source_payment_id,payment_date,amount_inr,status\n"
        "TENANT-1,erpnext_csv,PAY-1,2026-09-30T10:00:00+05:30,BATCH-1,PAY-1,2026-09-01,25000.00,posted\n"
    )
    (source / "payment_allocations.csv").write_text(
        f"{common},source_payment_id,source_invoice_id,allocated_amount_inr\n"
        "TENANT-1,erpnext_csv,ALLOC-1,2026-09-30T10:00:00+05:30,BATCH-1,PAY-1,INV-1,25000.00\n"
    )
    (source / "credit_notes.csv").write_text(
        f"{common},source_credit_note_id,source_invoice_id,credit_date,amount_inr,status\n"
        "TENANT-1,erpnext_csv,CN-1,2026-09-30T10:00:00+05:30,BATCH-1,CN-1,INV-1,2026-08-15,0.00,posted\n"
    )
    (source / "contacts.csv").write_text(
        f"{common},source_contact_id,source_customer_id,display_name,role,email,phone,email_permission,whatsapp_permission,opted_out,permission_observed_at\n"
        "TENANT-1,erpnext_csv,CONTACT-1,2026-09-30T10:00:00+05:30,BATCH-1,CONTACT-1,CUST-1,Accounts Payable,AP,ap@example.com,+919999999999,eligible,unknown,false,2026-09-30T10:00:00+05:30\n"
    )
    (source / "disputes.csv").write_text(
        f"{common},source_dispute_id,source_customer_id,source_invoice_id,category,status,opened_at,resolved_at\n"
        "TENANT-1,erpnext_csv,DISP-1,2026-09-30T10:00:00+05:30,BATCH-1,DISP-1,CUST-1,INV-1,none,resolved,2026-08-01T10:00:00+05:30,2026-08-02T10:00:00+05:30\n"
    )

    assert run(
        [
            "--workspace",
            str(workspace),
            "import",
            "--tenant",
            "TENANT-1",
            "--batch",
            "BATCH-1",
            "--input",
            str(source),
        ]
    ) == 0
    assert run(
        [
            "--workspace",
            str(workspace),
            "case",
            "create",
            "--tenant",
            "TENANT-1",
            "--case",
            "CASE-1",
            "--customer",
            "CUST-1",
        ]
    ) == 0
    assert run(
        [
            "--workspace",
            str(workspace),
            "promise",
            "record",
            "--tenant",
            "TENANT-1",
            "--promise",
            "PROMISE-1",
            "--customer",
            "CUST-1",
            "--amount",
            "125000.00",
            "--due",
            "2026-10-15",
        ]
    ) == 0
    assert run(
        [
            "--workspace",
            str(workspace),
            "queue",
            "--tenant",
            "TENANT-1",
            "--as-of",
            "2026-09-30",
        ]
    ) == 0

    assert "Acme" in capsys.readouterr().out
