import json
from pathlib import Path

from bharat_arp.cli import run


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
    assert [event["action"] for event in state["audit"]] == [
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

    output = tmp_path / "export"
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
