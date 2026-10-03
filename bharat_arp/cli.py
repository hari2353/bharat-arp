"""Offline CLI for the validation MVP."""

import argparse
import csv
import json
import re
import shutil
import sys
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from .decisioning import AccountExposure, CustomerAccount, rank_accounts
from .importing import validate_csv_text
from .metrics import AccountMeasurement, snapshot_pilot
from .normalization import NormalizedSourceStore
from .reconciliation import reconcile_invoice
from .reports import render_queue_csv, render_queue_html, render_queue_text
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
        elif args.command == "hold":
            _run_hold(args, state)
            _save_state(args.workspace, args.tenant, state)
        elif args.command == "retention":
            _run_retention(args, state)
            _save_state(args.workspace, args.tenant, state)
        elif args.command == "metrics":
            _run_metrics(args, state)
        elif args.command == "export":
            _append_state_audit(state, "command_export", "export")
            _export_state(args.workspace, args.tenant, state, args.output)
            print(f"exported tenant {args.tenant}")
        elif args.command == "purge":
            if not args.confirm:
                raise ValueError("purge requires --confirm")
            _purge(
                args.workspace,
                args.tenant,
                state,
                reason=args.reason or "operator_requested",
            )
            print(f"purged tenant {args.tenant}")
        if args.command not in {"purge", "export"}:
            _append_state_audit(state, f"command_{args.command}", args.command)
            _save_state(args.workspace, args.tenant, state)
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
    queue.add_argument("--format", choices=("text", "csv", "html"), default="text")

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
    decide.add_argument("--reason")
    edit = proposal_sub.add_parser("edit")
    edit.add_argument("--tenant", required=True)
    edit.add_argument("--proposal", required=True)
    edit.add_argument("--action", required=True)
    edit.add_argument("--evidence", required=True)

    promise = subparsers.add_parser("promise")
    promise_sub = promise.add_subparsers(dest="promise_command", required=True)
    record = promise_sub.add_parser("record")
    record.add_argument("--tenant", required=True)
    record.add_argument("--promise", required=True)
    record.add_argument("--customer")
    record.add_argument("--case")
    record.add_argument("--amount", required=True)
    record.add_argument("--due", required=True)
    promise_transition = promise_sub.add_parser("transition")
    promise_transition.add_argument("--tenant", required=True)
    promise_transition.add_argument("--promise", required=True)
    promise_transition.add_argument("--status", required=True)
    promise_transition.add_argument("--reason")
    fulfil = promise_sub.add_parser("fulfil")
    fulfil.add_argument("--tenant", required=True)
    fulfil.add_argument("--promise", required=True)
    fulfil.add_argument("--amount", required=True)
    fulfil.add_argument("--source", default="pilot_operator")

    case = subparsers.add_parser("case")
    case_sub = case.add_subparsers(dest="case_command", required=True)
    case_create = case_sub.add_parser("create")
    case_create.add_argument("--tenant", required=True)
    case_create.add_argument("--case", required=True)
    case_create.add_argument("--customer", required=True)
    case_show = case_sub.add_parser("show")
    case_show.add_argument("--tenant", required=True)
    case_show.add_argument("--case", required=True)
    case_transition = case_sub.add_parser("transition")
    case_transition.add_argument("--tenant", required=True)
    case_transition.add_argument("--case", required=True)
    case_transition.add_argument("--status", required=True)
    assign = case_sub.add_parser("assign")
    assign.add_argument("--tenant", required=True)
    assign.add_argument("--case", required=True)
    assign.add_argument("--assignee", required=True)

    outcome = subparsers.add_parser("outcome")
    outcome_sub = outcome.add_subparsers(dest="outcome_command", required=True)
    outcome_record = outcome_sub.add_parser("record")
    outcome_record.add_argument("--tenant", required=True)
    outcome_record.add_argument("--case", required=True)
    outcome_record.add_argument("--outcome", required=True)

    metrics = subparsers.add_parser("metrics")
    metrics.add_argument("--tenant", required=True)
    metrics.add_argument("--from", dest="from_date")
    metrics.add_argument("--to", dest="to_date")
    metrics.add_argument("--snapshot")
    metrics.add_argument("--format", choices=("text", "json"), default="text")

    export = subparsers.add_parser("export")
    export.add_argument("--tenant", required=True)
    export.add_argument("--output", type=Path, required=True)

    purge = subparsers.add_parser("purge")
    purge.add_argument("--tenant", required=True)
    purge.add_argument("--confirm", action="store_true")
    purge.add_argument("--reason")

    hold = subparsers.add_parser("hold")
    hold_sub = hold.add_subparsers(dest="hold_command", required=True)
    hold_add = hold_sub.add_parser("add")
    hold_add.add_argument("--tenant", required=True)
    hold_add.add_argument("--hold", required=True)
    hold_add.add_argument("--reason", required=True)
    hold_remove = hold_sub.add_parser("remove")
    hold_remove.add_argument("--tenant", required=True)
    hold_remove.add_argument("--hold", required=True)

    retention = subparsers.add_parser("retention")
    retention_sub = retention.add_subparsers(dest="retention_command", required=True)
    retention_apply = retention_sub.add_parser("apply")
    retention_apply.add_argument("--tenant", required=True)
    retention_apply.add_argument("--as-of", required=True)
    return parser


def _load_state(workspace: Path, tenant: str, operator: str) -> dict:
    tenant_dir = _tenant_dir(workspace, tenant)
    state_path = tenant_dir / "state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("tenant_id") != tenant:
            raise ValueError("tenant state does not match requested tenant")
        state.setdefault("schema_version", 2)
        state.setdefault("holds", [])
        state.setdefault("snapshots", [])
        return state
    return {
        "schema_version": 2,
        "tenant_id": tenant,
        "operator_id": operator,
        "proposals": [],
        "promises": [],
        "cases": [],
        "outcomes": [],
        "source_rows": {},
        "imports": [],
        "raw_imports": [],
        "audit": [],
        "holds": [],
        "snapshots": [],
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
            store.decide_proposal(
                proposal["proposal_id"],
                decision="reject",
                reason=proposal.get("rejection_reason") or "restored rejection",
            )
        elif proposal["status"] == "edited":
            store.edit_proposal(
                proposal["proposal_id"],
                action=proposal["action"],
                evidence_fingerprint=proposal["evidence_fingerprint"],
            )
        elif proposal["status"] == "stale":
            store.mark_proposal_stale(
                proposal["proposal_id"],
                new_evidence_fingerprint=proposal["evidence_fingerprint"],
            )
    for promise in state["promises"]:
        store.record_promise(
            promise_id=promise["promise_id"],
            customer_id=promise["customer_id"],
            amount=Decimal(promise["amount"]),
            due_on=promise["due_on"],
            source=promise["source"],
        )
        fulfilled_amount = Decimal(promise.get("fulfilled_amount", "0"))
        if fulfilled_amount:
            store.transition_promise(promise["promise_id"], "accepted")
            store.record_promise_fulfilment(
                promise["promise_id"], amount=fulfilled_amount, source="restored"
            )
            if promise["status"] in {"partial", "fulfilled"}:
                continue
        promise_paths = {
            "accepted": ("accepted",),
            "fulfilled": ("accepted", "fulfilled"),
            "broken": ("accepted", "broken"),
            "cancelled": ("accepted", "cancelled"),
            "rejected": ("rejected",),
            "partial": ("accepted",),
        }
        for status in promise_paths.get(promise["status"], ()):
            store.transition_promise(
                promise["promise_id"],
                status,
                cancellation_reason=promise.get("cancellation_reason")
                if status == "cancelled"
                else None,
            )
    for case in state.get("cases", []):
        store.create_case(case_id=case["case_id"], customer_id=case["customer_id"])
        case_paths = {
            "open": ("open",),
            "assigned": ("open", "assigned"),
            "in_progress": ("open", "assigned", "in_progress"),
            "resolved": ("open", "assigned", "in_progress", "resolved"),
            "closed": ("open", "assigned", "in_progress", "closed"),
            "reopened": ("open", "assigned", "in_progress", "resolved", "reopened"),
        }
        for status in case_paths.get(case["status"], ()):
            if status == "assigned":
                store.assign_case(
                    case["case_id"], assignee_id=case.get("assignee_id") or state["operator_id"]
                )
            else:
                store.transition_case(case["case_id"], status)
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


def _state_from_store(store: WorkflowStore, *, existing_state: dict | None = None) -> dict:
    state = {
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
        "audit": [
            {**asdict(event), "occurred_at": event.occurred_at.isoformat()}
            for event in store.audit_events()
        ],
    }
    if existing_state is not None:
        for key in (
            "source_rows", "imports", "raw_imports", "holds", "snapshots", "schema_version"
        ):
            if key in existing_state:
                state[key] = existing_state[key]
    return state


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
    elif args.proposal_command == "edit":
        store.edit_proposal(
            args.proposal, action=args.action, evidence_fingerprint=args.evidence
        )
    else:
        store.decide_proposal(
            args.proposal, decision=args.decision, reason=args.reason
        )
    preserved_state = state.copy()
    state.clear()
    state.update(_state_from_store(store, existing_state=preserved_state))
    if args.proposal_command == "create":
        print(f"proposal {args.proposal} created")
    elif args.proposal_command == "edit":
        print(f"proposal {args.proposal} edited")
    else:
        print(f"proposal {args.proposal} {args.decision}d")


def _run_promise(args: argparse.Namespace, state: dict) -> None:
    store = _store_from_state(state)
    if args.promise_command == "record":
        customer_id = args.customer
        if args.case:
            case = next(
                (item for item in store.cases() if item.case_id == args.case), None
            )
            if case is None:
                raise WorkflowError("case not found")
            customer_id = case.customer_id
        if not customer_id:
            raise ValueError("promise record requires --customer or --case")
        store.record_promise(
            promise_id=args.promise,
            customer_id=customer_id,
            amount=Decimal(args.amount),
            due_on=args.due,
            source="pilot_operator",
        )
    elif args.promise_command == "transition":
        store.transition_promise(
            args.promise, args.status, cancellation_reason=args.reason
        )
    else:
        store.record_promise_fulfilment(
            args.promise, amount=Decimal(args.amount), source=args.source
        )
    preserved_state = state.copy()
    state.clear()
    state.update(_state_from_store(store, existing_state=preserved_state))
    promise = next(item for item in store.promises() if item.promise_id == args.promise)
    print(f"promise {args.promise} status={promise.status}")


def _run_import(args: argparse.Namespace, state: dict) -> None:
    input_dir = _safe_child_path(args.workspace, args.input)
    if any(item.get("batch") == args.batch for item in state.get("imports", [])):
        print(f"batch {args.batch} already imported")
        return
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
        {
            "batch": args.batch,
            "summaries": summaries,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    state.setdefault("raw_imports", []).append(
        {"batch": args.batch, "imported_at": datetime.now(timezone.utc).isoformat()}
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
        if args.format == "csv":
            print("customer_id,legal_name,outstanding_inr,score,overdue_days,ageing_bucket,eligible,policy_version,explanation,missing_inputs")
        elif args.format == "html":
            print(render_queue_html(()), end="")
        else:
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
    if args.format == "csv":
        print(render_queue_csv(ranked), end="")
    elif args.format == "html":
        print(render_queue_html(ranked), end="")
    else:
        print(render_queue_text(ranked), end="")


def _run_case(args: argparse.Namespace, state: dict) -> None:
    store = _store_from_state(state)
    if args.case_command == "create":
        store.create_case(case_id=args.case, customer_id=args.customer)
        print(f"case {args.case} created")
    elif args.case_command == "transition":
        store.transition_case(args.case, args.status)
        print(f"case {args.case} transitioned to {args.status}")
    elif args.case_command == "assign":
        store.assign_case(args.case, assignee_id=args.assignee)
        print(f"case {args.case} assigned")
    else:
        case = next((item for item in store.cases() if item.case_id == args.case), None)
        if case is None:
            raise WorkflowError("case not found")
        print(f"case={case.case_id} customer={case.customer_id} status={case.status}")
    preserved_state = state.copy()
    state.clear()
    state.update(_state_from_store(store, existing_state=preserved_state))


def _run_outcome(args: argparse.Namespace, state: dict) -> None:
    store = _store_from_state(state)
    store.record_outcome(case_id=args.case, outcome=args.outcome)
    preserved_state = state.copy()
    state.clear()
    state.update(_state_from_store(store, existing_state=preserved_state))
    print(f"outcome recorded for case {args.case}")


def _run_hold(args: argparse.Namespace, state: dict) -> None:
    holds = state.setdefault("holds", [])
    if args.hold_command == "add":
        if any(item["hold_id"] == args.hold for item in holds):
            raise ValueError("legal hold already exists")
        holds.append({"hold_id": args.hold, "reason": args.reason, "active": True})
        _append_state_audit(state, "legal_hold_added", args.hold)
        print(f"legal hold {args.hold} added")
        return
    for hold in holds:
        if hold["hold_id"] == args.hold and hold["active"]:
            hold["active"] = False
            _append_state_audit(state, "legal_hold_removed", args.hold)
            print(f"legal hold {args.hold} removed")
            return
    raise ValueError("active legal hold not found")


def _run_retention(args: argparse.Namespace, state: dict) -> None:
    if args.retention_command != "apply":
        raise ValueError("unsupported retention operation")
    if any(item.get("active") for item in state.get("holds", [])):
        raise ValueError("tenant has active legal holds")
    cutoff = date.fromisoformat(args.as_of) - timedelta(days=90)
    retained = []
    expired_batches = []
    for item in state.get("raw_imports", []):
        if datetime.fromisoformat(item["imported_at"]).date() < cutoff:
            expired_batches.append(item["batch"])
        else:
            retained.append(item)
    state["raw_imports"] = retained
    for record_type, rows in state.get("source_rows", {}).items():
        state["source_rows"][record_type] = [
            row for row in rows if row.get("import_batch_id") not in expired_batches
        ]
    _append_state_audit(state, "retention_applied", ",".join(expired_batches) or "none")
    print(f"retention expired={len(expired_batches)}")


def _run_metrics(args: argparse.Namespace, state: dict) -> None:
    summary = {
        "tenant": args.tenant,
        "from": args.from_date,
        "to": args.to_date,
        "imports": len(state.get("imports", [])),
        "source_rows": sum(
            len(rows) for rows in state.get("source_rows", {}).values()
        ),
        "cases": len(state.get("cases", [])),
        "proposals": len(state.get("proposals", [])),
        "promises": len(state.get("promises", [])),
        "outcomes": len(state.get("outcomes", [])),
        "audit_events": len(state.get("audit", [])),
    }
    if args.snapshot:
        snapshot = _build_snapshot(args, state)
        snapshots = state.setdefault("snapshots", [])
        existing = next((item for item in snapshots if item["as_of"] == args.snapshot), None)
        if existing is None:
            snapshots.append(asdict(snapshot))
            existing = asdict(snapshot)
            _append_state_audit(state, "metrics_snapshot_created", args.snapshot)
            _save_state(args.workspace, args.tenant, state)
        summary["snapshot"] = existing
    if args.format == "json":
        print(json.dumps(summary, sort_keys=True, default=str))
        return
    window = ""
    if args.from_date or args.to_date:
        window = f" from={args.from_date or '-'} to={args.to_date or '-'}"
    print(
        f"tenant={args.tenant}{window} cases={summary['cases']} "
        f"proposals={summary['proposals']} promises={summary['promises']} "
        f"outcomes={summary['outcomes']} source_rows={summary['source_rows']}"
    )
    if args.snapshot:
        print(f"snapshot={args.snapshot}")


def _build_snapshot(args: argparse.Namespace, state: dict):
    as_of = date.fromisoformat(args.snapshot)
    source_store = NormalizedSourceStore(tenant_id=args.tenant)
    for record_type, rows in state.get("source_rows", {}).items():
        visible_rows = [
            row
            for row in rows
            if datetime.fromisoformat(row["source_updated_at"]).date() <= as_of
        ]
        result = source_store.upsert_rows(record_type, visible_rows)
        if result.errors:
            raise ValueError(f"stored source rows have {len(result.errors)} normalization errors")
    payments = list(source_store.current_records("payments"))
    allocations = list(source_store.current_records("payment_allocations"))
    credit_notes = list(source_store.current_records("credit_notes"))
    accounts: dict[str, list[AccountExposure]] = {}
    exceptions: dict[str, list[str]] = {}
    for invoice in source_store.current_records("invoices"):
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
    names = {
        item.ref.source_record_id: item.legal_name
        for item in source_store.current_records("customers")
    }
    open_disputes = {
        item.customer_id
        for item in source_store.current_records("disputes")
        if item.status == "open"
    }
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
        as_of=as_of,
        policy_version="v1",
    )
    priority_ids = {item.customer_id for item in ranked if item.score > 0}
    promise_by_customer = {
        item["customer_id"]: item["status"]
        for item in state.get("promises", [])
    }
    measurements = []
    for item in ranked:
        due_on = min(
            exposure.due_date
            for exposure in accounts[item.customer_id]
            if exposure.outstanding > 0
        ) if any(exposure.outstanding > 0 for exposure in accounts[item.customer_id]) else as_of
        customer_payments = [
            payment
            for payment in payments
            if payment.status == "posted"
            and payment.payment_date <= as_of
            and any(
                allocation.payment_id == payment.ref.source_record_id
                and allocation.invoice_id in {
                    exposure.invoice_id for exposure in accounts[item.customer_id]
                }
                for allocation in allocations
            )
        ]
        payment_amount = sum(
            (
                allocation.allocated_amount_inr
                for allocation in allocations
                if allocation.payment_id in {
                    payment.ref.source_record_id for payment in customer_payments
                }
                and allocation.invoice_id in {
                    exposure.invoice_id for exposure in accounts[item.customer_id]
                }
            ),
            Decimal("0.00"),
        )
        measurements.append(
            AccountMeasurement(
                customer_id=item.customer_id,
                opening_outstanding=item.outstanding,
                closing_outstanding=item.outstanding,
                priority=item.customer_id in priority_ids,
                decision_eligible=item.eligible,
                actioned_at=None,
                due_on=due_on,
                payment_received_at=max(
                    (payment.payment_date for payment in customer_payments),
                    default=None,
                ),
                payment_amount=payment_amount,
                payment_in_flight=any(
                    payment.status == "pending"
                    and any(
                        allocation.payment_id == payment.ref.source_record_id
                        and allocation.invoice_id in {
                            exposure.invoice_id
                            for exposure in accounts[item.customer_id]
                        }
                        for allocation in allocations
                    )
                    for payment in payments
                    if payment.payment_date <= as_of
                ),
                promise_status=promise_by_customer.get(item.customer_id),
            )
        )
    for case in state.get("cases", []):
        if case["customer_id"] not in accounts:
            measurements.append(
                AccountMeasurement(
                    customer_id=case["customer_id"],
                    opening_outstanding=Decimal("0.00"),
                    closing_outstanding=Decimal("0.00"),
                    priority=False,
                    decision_eligible=False,
                    actioned_at=None,
                    due_on=as_of,
                    payment_received_at=None,
                    payment_amount=Decimal("0.00"),
                    payment_in_flight=False,
                    promise_status=promise_by_customer.get(case["customer_id"]),
                )
            )
    return snapshot_pilot(args.tenant, as_of=as_of, measurements=measurements)


def _export_state(workspace: Path, tenant: str, state: dict, output: Path) -> None:
    output = _safe_child_path(workspace, output)
    output_root = output.resolve()
    if output_root != workspace.resolve() and (output_root / "state.json").exists():
        raise ValueError("export output cannot be an existing tenant directory")
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

    _write_records_csv(
        output_root / "source_rows.csv",
        ("record_type", "row_number", "field", "value"),
        (
            (record_type, row_number, field, value)
            for record_type, rows in sorted(state.get("source_rows", {}).items())
            for row_number, row in enumerate(rows, start=1)
            for field, value in sorted(row.items())
        ),
    )
    _write_records_csv(
        output_root / "workflow.csv",
        ("record_type", "record_id", "customer_id", "status", "details"),
        _workflow_export_rows(state),
    )
    _write_records_csv(
        output_root / "holds.csv",
        ("hold_id", "reason", "active"),
        (
            (item["hold_id"], item["reason"], item["active"])
            for item in state.get("holds", [])
        ),
    )
    _write_records_csv(
        output_root / "snapshots.csv",
        ("tenant_id", "as_of", "metric", "value"),
        (
            (tenant, snapshot.get("as_of", ""), metric, value)
            for snapshot in state.get("snapshots", [])
            for metric, value in sorted(snapshot.items())
            if metric not in {"tenant_id", "as_of"}
        ),
    )


def _write_records_csv(path: Path, fields: tuple[str, ...], rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fields)
        for row in rows:
            writer.writerow(_neutralize_csv_value(str(value)) for value in row)


def _workflow_export_rows(state: dict):
    for record_type in ("cases", "proposals", "promises", "outcomes"):
        for item in state.get(record_type, []):
            identifier = next(
                (item[key] for key in ("case_id", "proposal_id", "promise_id") if key in item),
                item.get("case_id", ""),
            )
            yield (
                record_type,
                identifier,
                item.get("customer_id", ""),
                item.get("status", item.get("outcome", "")),
                json.dumps(item, sort_keys=True, default=str),
            )


def _neutralize_csv_value(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _purge(workspace: Path, tenant: str, state: dict, *, reason: str) -> None:
    tenant_dir = _tenant_dir(workspace, tenant)
    if not tenant_dir.exists():
        return
    active_holds = [item for item in state.get("holds", []) if item.get("active")]
    if active_holds:
        raise ValueError("tenant has active legal holds")
    if tenant_dir.parent != workspace.resolve():
        raise ValueError("tenant path is outside workspace")
    purged = json.loads(json.dumps(state, default=str))
    purged["tenant_id"] = f"DELETED-{tenant}"
    purged["purge"] = {
        "reason": reason,
        "operator_id": state.get("operator_id", "unknown"),
        "occurred_at": datetime.now().astimezone().isoformat(),
    }
    purged["source_rows"] = {}
    purged["imports"] = []
    purged["proposals"] = []
    purged["promises"] = []
    purged["cases"] = []
    purged["outcomes"] = []
    purged["snapshots"] = []
    purged["holds"] = []
    purged["audit"] = [
        {
            **event,
            "tenant_id": f"DELETED-{tenant}",
            "actor_id": f"DELETED-ACTOR-{state.get('operator_id', 'unknown')}",
            "object_id": "DELETED-OBJECT",
        }
        for event in state.get("audit", [])
    ]
    purged["audit"].append(
        {
            "sequence": len(purged["audit"]) + 1,
            "tenant_id": f"DELETED-{tenant}",
            "actor_id": f"DELETED-ACTOR-{state.get('operator_id', 'unknown')}",
            "action": "tenant_purged",
            "object_id": "DELETED-OBJECT",
            "occurred_at": purged["purge"]["occurred_at"],
        }
    )
    shutil.rmtree(tenant_dir)
    purge_root = workspace.resolve() / ".purged"
    purge_root.mkdir(parents=True, exist_ok=True)
    (purge_root / f"{tenant}.json").write_text(
        json.dumps(purged, indent=2, sort_keys=True), encoding="utf-8"
    )


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


def _append_state_audit(state: dict, action: str, object_id: str) -> None:
    audit = state.setdefault("audit", [])
    audit.append(
        {
            "sequence": len(audit) + 1,
            "tenant_id": state["tenant_id"],
            "actor_id": state["operator_id"],
            "action": action,
            "object_id": object_id,
            "occurred_at": datetime.now().astimezone().isoformat(),
        }
    )


if __name__ == "__main__":
    raise SystemExit(run())
