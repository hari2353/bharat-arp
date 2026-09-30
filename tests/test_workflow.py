from decimal import Decimal

import pytest

from bharat_arp.workflow import WorkflowStore, WorkflowError


def test_approval_records_audit_event_and_never_executes_side_effect():
    store = WorkflowStore(tenant_id="TENANT-1", operator_id="operator-1")
    proposal = store.create_proposal(
        proposal_id="PROP-1",
        customer_id="CUST-1",
        policy_version="v1",
        evidence_fingerprint="evidence-1",
        action="draft_customer_follow_up",
    )

    approved = store.decide_proposal("PROP-1", decision="approve")

    assert approved.status == "approved"
    assert approved.executes_side_effect is False
    assert store.audit_events()[0].action == "proposal_created"
    assert store.audit_events()[-1].action == "proposal_approved"


def test_stale_proposal_cannot_be_approved():
    store = WorkflowStore(tenant_id="TENANT-1", operator_id="operator-1")
    store.create_proposal(
        proposal_id="PROP-1",
        customer_id="CUST-1",
        policy_version="v1",
        evidence_fingerprint="evidence-1",
        action="draft_customer_follow_up",
    )

    store.mark_proposal_stale("PROP-1", new_evidence_fingerprint="evidence-2")

    with pytest.raises(WorkflowError, match="stale"):
        store.decide_proposal("PROP-1", decision="approve")


def test_promise_to_pay_can_be_recorded_without_proposal():
    store = WorkflowStore(tenant_id="TENANT-1", operator_id="operator-1")

    promise = store.record_promise(
        promise_id="PROMISE-1",
        customer_id="CUST-1",
        amount=Decimal("125000.00"),
        due_on="2026-10-15",
        source="phone_call",
    )

    assert promise.status == "proposed"
    assert promise.amount == Decimal("125000.00")
    assert store.audit_events()[-1].action == "promise_recorded"


def test_invalid_promise_transition_does_not_mutate_state():
    store = WorkflowStore(tenant_id="TENANT-1", operator_id="operator-1")
    store.record_promise(
        promise_id="PROMISE-1",
        customer_id="CUST-1",
        amount=Decimal("125000.00"),
        due_on="2026-10-15",
        source="phone_call",
    )

    with pytest.raises(WorkflowError, match="transition"):
        store.transition_promise("PROMISE-1", "fulfilled")

    assert store.promises()[0].status == "proposed"


def test_collection_case_follows_open_progress_and_resolution_lifecycle():
    store = WorkflowStore(tenant_id="TENANT-1", operator_id="operator-1")

    case = store.create_case(case_id="CASE-1", customer_id="CUST-1")
    assert case.status == "new"

    store.transition_case("CASE-1", "open")
    store.transition_case("CASE-1", "in_progress")
    resolved = store.transition_case("CASE-1", "resolved")

    assert resolved.status == "resolved"
    assert store.audit_events()[-1].action == "case_resolved"


def test_invalid_case_transition_does_not_mutate_state():
    store = WorkflowStore(tenant_id="TENANT-1", operator_id="operator-1")
    store.create_case(case_id="CASE-1", customer_id="CUST-1")

    with pytest.raises(WorkflowError, match="case transition"):
        store.transition_case("CASE-1", "resolved")

    assert store.cases()[0].status == "new"
