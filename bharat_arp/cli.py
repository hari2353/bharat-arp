"""Offline CLI for the validation MVP."""

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .decisioning import AccountExposure, CustomerAccount, rank_accounts
from .importing import validate_csv_text
from .normalization import NormalizedSourceStore
from .reconciliation import reconcile_invoice
from .workflow import AuditEvent, WorkflowError, WorkflowStore


TENANT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def run(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if not TENANT_PATTERN.fullmatch(args.tenant):
            raise ValueError("invalid tenant")
        state = _load_state(args.workspace, args.tenant, args.operator)
        if args.command == "init":
            _save_state(args.workspace, args.tenant, state)
            print(f"initialized tenant {args.tenant}")
        elif args.command == "queue":
            _run_queue(args, state)
        elif args.command == "import":
            _run_import(args, state)
            _save_state(args.workspace, args.tenant, state)
        elif args.command == "proposal":
            _run_proposal(args, state)
            _save_state(args.workspace, args.tenant, state)
        elif args.command == "case":
            _run_case(args, state)
            _save_state(args.workspace, args.tenant, state)
        elif args.command == "promise":
            _run_promise(args, state)
            _save_state(args.workspace, args.tenant, state)
        elif args.command == "outcome":
            _run_outcome(args, state)
            _save_state(args.workspace, args.tenant, state)
        elif args.command == "metrics":
            print(
                f"tenant={args.tenant} cases={len(state.get('cases', []))} "
                f"outcomes={len(state.get('outcomes', []))}"
            )
        elif args.command == "export":
            _export_state(args.workspace, args.tenant, state, args.output)
            print(f"exported tenant {args.tenant}")
        elif args.command == "purge":
            if not args.confirm:
                raise ValueError("purge requires --confirm")
            _purge(args.workspace, args.tenant)
            print(f"purged tenant {args.tenant}")
        return 0
    except (ValueError, WorkflowError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bharat-arp")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--operator", default="pilot_operator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--tenant", required=True)

    queue = subparsers.add_parser("queue")
    queue.add_argument("--tenant", required=True)
    queue.add_argument("--as-of", default="2026-09-30")

    import_command = subparsers.add_parser("import")
    import_command.add_argument("--tenant", required=True)
    import_command.add_argument("--batch", required=True)
    import_command.add_argument("--input", type=Path, required=True)

    for command in ():
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--tenant", required=True)

    proposal = subparsers.add_parser("proposal")
    proposal_sub = proposal.add_subparsers(dest="proposal_command", required=True)
    create = proposal_sub.add_parser("create")
    create.add_argument("--tenant", required=True)
    create.add_argument("--proposal", required=True)
    create.add_argument("--customer", required=True)
    decide = proposal_sub.add_parser("decide")
    decide.add_argument("--tenant", required=True)
    decide.add_argument("--proposal", required=True)
    decide.add_argument("--decision", choices=("approve", "reject"), required=True)

    promise = subparsers.add_parser("promise")
    promise_sub = promise.add_subparsers(dest="promise_command", required=True)
    record = promise_sub.add_parser("record")
    record.add_argument("--tenant", required=True)
    record.add_argument("--promise", required=True)
    record.add_argument("--customer", required=True)
    record.add_argument("--amount", required=True)
    record.add_argument("--due", required=True)

    case = subparsers.add_parser("case")
    case_sub = case.add_subparsers(dest="case_command", required=True)
    case_create = case_sub.add_parser("create")
    case_create.add_argument("--tenant", required=True)
    case_create.add_argument("--case", required=True)
    case_create.add_argument("--customer", required=True)
    case_show = case_sub.add_parser("show")
    case_show.add_argument("--tenant", required=True)
    case_show.add_argument("--case", required=True)

    outcome = subparsers.add_parser("outcome")
    outcome_sub = outcome.add_subparsers(dest="outcome_command", required=True)
    outcome_record = outcome_sub.add_parser("record")
    outcome_record.add_argument("--tenant", required=True)
    outcome_record.add_argument("--case", required=True)
    outcome_record.add_argument("--outcome", required=True)

    metrics = subparsers.add_parser("metrics")
    metrics.add_argument("--tenant", required=True)

    export = subparsers.add_parser("export")
    export.add_argument("--tenant", required=True)
    export.add_argument("--output", type=Path, required=True)

    purge = subparsers.add_parser("purge")
    purge.add_argument("--tenant", required=True)
    purge.add_argument("--confirm", action="store_true")
    return parser


def _load_state(workspace: Path, tenant: str, operator: str) -> dict:
    tenant_dir = _tenant_dir(workspace, tenant)
    state_path = tenant_dir / "state.json"
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {
        "tenant_id": tenant,
        "operator_id": operator,
        "proposals": [],
        "promises": [],
        "cases": [],
        "outcomes": [],
        "source_rows": {},
        "imports": [],
        "audit": [],
    }


def _save_state(workspace: Path, tenant: str, state: dict) -> None:
    tenant_dir = _tenant_dir(workspace, tenant)
    tenant_dir.mkdir(parents=True, exist_ok=True)
    state_path = tenant_dir / "state.json"
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    temporary.replace(state_path)


def _store_from_state(state: dict) -> WorkflowStore:
    store = WorkflowStore(tenant_id=state["tenant_id"], operator_id=state["operator_id"])
    for proposal in state["proposals"]:
        store.create_proposal(
            proposal_id=proposal["proposal_id"],
            customer_id=proposal["customer_id"],
            policy_version=proposal["policy_version"],
            evidence_fingerprint=proposal["evidence_fingerprint"],
            action=proposal["action"],
        )
        if proposal["status"] == "approved":
            store.decide_proposal(proposal["proposal_id"], decision="approve")
        elif proposal["status"] == "rejected":
            store.decide_proposal(proposal["proposal_id"], decision="reject")
    for promise in state["promises"]:
        store.record_promise(
            promise_id=promise["promise_id"],
            customer_id=promise["customer_id"],
            amount=Decimal(promise["amount"]),
            due_on=promise["due_on"],
            source=promise["source"],
        )
    for case in state.get("cases", []):
        store.create_case(case_id=case["case_id"], customer_id=case["customer_id"])
        if case["status"] != "new":
            store.transition_case(case["case_id"], case["status"])
    for outcome in state.get("outcomes", []):
        store.record_outcome(case_id=outcome["case_id"], outcome=outcome["outcome"])
    store._events.clear()
    store.restore_audit_events(
        tuple(
            AuditEvent(
                sequence=event["sequence"],
                tenant_id=event["tenant_id"],
                actor_id=event["actor_id"],
                action=event["action"],
                object_id=event["object_id"],
                occurred_at=datetime.fromisoformat(event["occurred_at"]),
            )
            for event in state["audit"]
        )
    )
    return store


def _state_from_store(store: WorkflowStore) -> dict:
    return {
        "tenant_id": store.tenant_id,
        "operator_id": store.operator_id,
        "proposals": [
            {**asdict(item), "executes_side_effect": False}
            for item in store.proposals()
        ],
        "promises": [
            {**asdict(item), "amount": str(item.amount)} for item in store.promises()
        ],
        "cases": [asdict(item) for item in store.cases()],
        "outcomes": [asdict(item) for item in store.outcomes()],
        "audit": [asdict(event) for event in store.audit_events()],
    }


def _run_proposal(args: argparse.Namespace, state: dict) -> None:
    store = _store_from_state(state)
    if args.proposal_command == "create":
        store.create_proposal(
            proposal_id=args.proposal,
            customer_id=args.customer,
            policy_version="v1",
            evidence_fingerprint="manual",
            action="draft_customer_follow_up",
        )
    else:
        store.decide_proposal(args.proposal, decision=args.decision)
    state.clear()
    state.update(_state_from_store(store))
    if args.proposal_command == "create":
        print(f"proposal {args.proposal} created")
    else:
        print(f"proposal {args.proposal} {args.decision}d")


def _run_promise(args: argparse.Namespace, state: dict) -> None:
    store = _store_from_state(state)
    store.record_promise(
        promise_id=args.promise,
        customer_id=args.customer,
        amount=Decimal(args.amount),
        due_on=args.due,
        source="pilot_operator",
    )
    state.clear()
    state.update(_state_from_store(store))
    print(f"promise {args.promise} recorded")


def _run_import(args: argparse.Namespace, state: dict) -> None:
    input_dir = _safe_child_path(args.workspace, args.input)
    record_types = (
        "customers",
        "contacts",
        "invoices",
        "payments",
        "payment_allocations",
        "credit_notes",
        "disputes",
    )
    source_rows = state.setdefault("source_rows", {})
    summaries = []
    for record_type in record_types:
        path = input_dir / f"{record_type}.csv"
        if not path.is_file():
            raise ValueError(f"missing import file: {path.name}")
        result = validate_csv_text(
            record_type,
            path.read_text(encoding="utf-8-sig"),
            tenant_id=args.tenant,
            import_batch_id=args.batch,
        )
        if result.errors:
            raise ValueError(f"{record_type} has {len(result.errors)} validation errors")
        source_rows.setdefault(record_type, []).extend(result.rows)
        summaries.append({"record_type": record_type, "rows": len(result.rows)})
    state.setdefault("imports", []).append(
        {"batch": args.batch, "summaries": summaries}
    )
    state.setdefault("audit", []).append(
        {
            "sequence": len(state["audit"]) + 1,
            "tenant_id": args.tenant,
            "actor_id": state["operator_id"],
            "action": "source_batch_imported",
            "object_id": args.batch,
            "occurred_at": datetime.now().astimezone().isoformat(),
        }
    )
    print(f"imported batch {args.batch}")


def _run_queue(args: argparse.Namespace, state: dict) -> None:
    source_rows = state.get("source_rows", {})
    if not source_rows:
        print(f"tenant={args.tenant} queue=empty")
        return
    store = NormalizedSourceStore(tenant_id=args.tenant)
    for record_type, rows in source_rows.items():
        result = store.upsert_rows(record_type, rows)
        if result.errors:
            raise ValueError(f"stored source rows have {len(result.errors)} normalization errors")
    invoices = store.current_records("invoices")
    payments = list(store.current_records("payments"))
    allocations = list(store.current_records("payment_allocations"))
    credit_notes = list(store.current_records("credit_notes"))
    disputes = list(store.current_records("disputes"))
    names = {
        item.ref.source_record_id: item.legal_name
        for item in store.current_records("customers")
    }
    accounts: dict[str, list[AccountExposure]] = {}
    exceptions: dict[str, list[str]] = {}
    for invoice in invoices:
        result = reconcile_invoice(
            invoice,
            payments=payments,
            allocations=allocations,
            credit_notes=credit_notes,
        )
        accounts.setdefault(invoice.customer_id, []).append(
            AccountExposure(
                invoice_id=invoice.ref.source_record_id,
                outstanding=result.outstanding,
                due_date=invoice.due_date,
                reconciliation_state=result.state,
            )
        )
        exceptions.setdefault(invoice.customer_id, []).extend(result.exceptions)
    open_disputes = {item.customer_id for item in disputes if item.status == "open"}
    ranked = rank_accounts(
        [
            CustomerAccount(
                customer_id=customer_id,
                legal_name=names.get(customer_id, customer_id),
                exposures=tuple(exposures),
                unresolved_dispute=customer_id in open_disputes,
                data_quality_exceptions=tuple(sorted(set(exceptions.get(customer_id, [])))),
            )
            for customer_id, exposures in accounts.items()
        ],
        as_of=date.fromisoformat(args.as_of),
        policy_version="v1",
    )
    for item in ranked:
        print(
            f"customer={item.legal_name} outstanding={item.outstanding:.2f} "
            f"score={item.score:.2f} bucket={item.ageing_bucket} "
            f"eligible={str(item.eligible).lower()}"
        )


def _run_case(args: argparse.Namespace, state: dict) -> None:
    store = _store_from_state(state)
    if args.case_command == "create":
        store.create_case(case_id=args.case, customer_id=args.customer)
        print(f"case {args.case} created")
    else:
        case = next((item for item in store.cases() if item.case_id == args.case), None)
        if case is None:
            raise WorkflowError("case not found")
        print(f"case={case.case_id} customer={case.customer_id} status={case.status}")
    state.clear()
    state.update(_state_from_store(store))


def _run_outcome(args: argparse.Namespace, state: dict) -> None:
    store = _store_from_state(state)
    store.record_outcome(case_id=args.case, outcome=args.outcome)
    state.clear()
    state.update(_state_from_store(store))
    print(f"outcome recorded for case {args.case}")


def _export_state(workspace: Path, tenant: str, state: dict, output: Path) -> None:
    output_root = output.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    state_path = output_root / "state.json"
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True, default=str), encoding="utf-8")
    audit_path = output_root / "audit.csv"
    with audit_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("sequence", "tenant_id", "actor_id", "action", "object_id", "occurred_at"))
        writer.writeheader()
        for event in state["audit"]:
            writer.writerow(
                {
                    key: _neutralize_csv_value(str(value))
                    for key, value in event.items()
                }
            )


def _neutralize_csv_value(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _purge(workspace: Path, tenant: str) -> None:
    tenant_dir = _tenant_dir(workspace, tenant)
    if not tenant_dir.exists():
        return
    if tenant_dir.parent != workspace.resolve():
        raise ValueError("tenant path is outside workspace")
    for path in tenant_dir.iterdir():
        if path.is_file() and path.name == "state.json":
            path.unlink()
    tenant_dir.rmdir()


def _tenant_dir(workspace: Path, tenant: str) -> Path:
    root = workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    candidate = (root / tenant).resolve()
    if candidate.parent != root:
        raise ValueError("tenant path is outside workspace")
    return candidate


def _safe_child_path(workspace: Path, path: Path) -> Path:
    root = workspace.resolve()
    candidate = path.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path is outside workspace")
    return candidate


if __name__ == "__main__":
    raise SystemExit(run())
