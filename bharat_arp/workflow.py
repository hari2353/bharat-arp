"""Validation-mode workflow state and append-only audit events."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


class WorkflowError(ValueError):
    pass


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    tenant_id: str
    actor_id: str
    action: str
    object_id: str
    occurred_at: datetime


@dataclass(frozen=True)
class WorkflowProposal:
    proposal_id: str
    customer_id: str
    policy_version: str
    evidence_fingerprint: str
    action: str
    status: str
    requires_approval: bool
    executes_side_effect: bool
    rejection_reason: str | None = None


@dataclass(frozen=True)
class PromiseToPay:
    promise_id: str
    customer_id: str
    amount: Decimal
    due_on: str
    source: str
    status: str
    fulfilled_amount: Decimal = Decimal("0.00")
    fulfilment_source: str | None = None
    cancellation_reason: str | None = None

    @property
    def remaining_amount(self) -> Decimal:
        return max(self.amount - self.fulfilled_amount, Decimal("0.00"))


@dataclass(frozen=True)
class CollectionCase:
    case_id: str
    customer_id: str
    status: str
    assignee_id: str | None = None


@dataclass(frozen=True)
class CollectionOutcome:
    case_id: str
    outcome: str


class WorkflowStore:
    def __init__(self, *, tenant_id: str, operator_id: str) -> None:
        self.tenant_id = tenant_id
        self.operator_id = operator_id
        self._proposals: dict[str, WorkflowProposal] = {}
        self._promises: dict[str, PromiseToPay] = {}
        self._cases: dict[str, CollectionCase] = {}
        self._outcomes: list[CollectionOutcome] = []
        self._events: list[AuditEvent] = []

    def _audit(self, action: str, object_id: str) -> None:
        self._events.append(
            AuditEvent(
                sequence=len(self._events) + 1,
                tenant_id=self.tenant_id,
                actor_id=self.operator_id,
                action=action,
                object_id=object_id,
                occurred_at=datetime.now(timezone.utc),
            )
        )

    def create_proposal(
        self,
        *,
        proposal_id: str,
        customer_id: str,
        policy_version: str,
        evidence_fingerprint: str,
        action: str,
    ) -> WorkflowProposal:
        if proposal_id in self._proposals:
            raise WorkflowError("proposal already exists")
        proposal = WorkflowProposal(
            proposal_id=proposal_id,
            customer_id=customer_id,
            policy_version=policy_version,
            evidence_fingerprint=evidence_fingerprint,
            action=action,
            status="proposed",
            requires_approval=True,
            executes_side_effect=False,
        )
        self._proposals[proposal_id] = proposal
        self._audit("proposal_created", proposal_id)
        return proposal

    def mark_proposal_stale(self, proposal_id: str, *, new_evidence_fingerprint: str) -> None:
        proposal = self._get_proposal(proposal_id)
        if proposal.status != "proposed":
            raise WorkflowError("only proposed proposals can become stale")
        self._proposals[proposal_id] = WorkflowProposal(
            **{**proposal.__dict__, "status": "stale", "evidence_fingerprint": new_evidence_fingerprint}
        )
        self._audit("proposal_staled", proposal_id)

    def decide_proposal(
        self, proposal_id: str, *, decision: str, reason: str | None = None
    ) -> WorkflowProposal:
        proposal = self._get_proposal(proposal_id)
        if proposal.status not in {"proposed", "edited"}:
            raise WorkflowError(f"proposal is not in a decidable state: {proposal.status}")
        if decision not in {"approve", "reject"}:
            raise WorkflowError("unsupported proposal decision")
        if decision == "reject" and not reason:
            raise WorkflowError("rejection reason is required")
        status = "approved" if decision == "approve" else "rejected"
        updated = WorkflowProposal(
            **{
                **proposal.__dict__,
                "status": status,
                "rejection_reason": reason if decision == "reject" else None,
            }
        )
        self._proposals[proposal_id] = updated
        self._audit(f"proposal_{status}", proposal_id)
        return updated

    def edit_proposal(
        self, proposal_id: str, *, action: str, evidence_fingerprint: str
    ) -> WorkflowProposal:
        proposal = self._get_proposal(proposal_id)
        if proposal.status not in {"proposed", "edited"}:
            raise WorkflowError("only proposed proposals can be edited")
        updated = WorkflowProposal(
            **{
                **proposal.__dict__,
                "action": action,
                "evidence_fingerprint": evidence_fingerprint,
                "status": "edited",
            }
        )
        self._proposals[proposal_id] = updated
        self._audit("proposal_edited", proposal_id)
        return updated

    def record_promise(
        self,
        *,
        promise_id: str,
        customer_id: str,
        amount: Decimal,
        due_on: str,
        source: str,
    ) -> PromiseToPay:
        if promise_id in self._promises:
            raise WorkflowError("promise already exists")
        if amount <= 0:
            raise WorkflowError("promise amount must be positive")
        promise = PromiseToPay(promise_id, customer_id, amount, due_on, source, "proposed")
        self._promises[promise_id] = promise
        self._audit("promise_recorded", promise_id)
        return promise

    def create_case(self, *, case_id: str, customer_id: str) -> CollectionCase:
        if case_id in self._cases:
            raise WorkflowError("case already exists")
        case = CollectionCase(case_id, customer_id, "new")
        self._cases[case_id] = case
        self._audit("case_created", case_id)
        return case

    def assign_case(self, case_id: str, *, assignee_id: str) -> CollectionCase:
        case = self._cases.get(case_id)
        if case is None:
            raise WorkflowError("case not found")
        if case.status != "open":
            raise WorkflowError("only open cases can be assigned")
        if not assignee_id.strip():
            raise WorkflowError("assignee is required")
        updated = CollectionCase(case.case_id, case.customer_id, "assigned", assignee_id)
        self._cases[case_id] = updated
        self._audit("case_assigned", case_id)
        return updated

    def transition_case(self, case_id: str, status: str) -> CollectionCase:
        case = self._cases.get(case_id)
        if case is None:
            raise WorkflowError("case not found")
        valid = {
            "new": {"open"},
            "open": {"assigned"},
            "assigned": {"in_progress"},
            "in_progress": {"resolved", "closed"},
            "resolved": {"reopened"},
            "closed": {"reopened"},
            "reopened": {"open"},
        }
        if status not in valid.get(case.status, set()):
            raise WorkflowError("invalid case transition")
        assignee_id = None if status == "reopened" else case.assignee_id
        updated = CollectionCase(case.case_id, case.customer_id, status, assignee_id)
        self._cases[case_id] = updated
        self._audit(f"case_{status}", case_id)
        return updated

    def record_outcome(self, *, case_id: str, outcome: str) -> CollectionOutcome:
        if case_id not in self._cases:
            raise WorkflowError("case not found")
        if not outcome.strip():
            raise WorkflowError("outcome is required")
        recorded = CollectionOutcome(case_id, outcome)
        self._outcomes.append(recorded)
        self._audit("outcome_recorded", case_id)
        return recorded

    def transition_promise(
        self, promise_id: str, status: str, *, cancellation_reason: str | None = None
    ) -> PromiseToPay:
        promise = self._promises.get(promise_id)
        if promise is None:
            raise WorkflowError("promise not found")
        valid = {
            "proposed": {"accepted", "rejected"},
            "accepted": {"fulfilled", "broken", "cancelled"},
            "partial": {"fulfilled", "broken", "cancelled"},
        }
        if status not in valid.get(promise.status, set()):
            raise WorkflowError("invalid promise transition")
        if status == "cancelled" and not cancellation_reason:
            raise WorkflowError("cancellation reason is required")
        updated = PromiseToPay(
            **{
                **promise.__dict__,
                "status": status,
                "cancellation_reason": cancellation_reason
                if status == "cancelled"
                else promise.cancellation_reason,
            }
        )
        self._promises[promise_id] = updated
        self._audit(f"promise_{status}", promise_id)
        return updated

    def record_promise_fulfilment(
        self, promise_id: str, *, amount: Decimal, source: str
    ) -> PromiseToPay:
        promise = self._promises.get(promise_id)
        if promise is None:
            raise WorkflowError("promise not found")
        if promise.status not in {"accepted", "partial"}:
            raise WorkflowError("promise is not open for fulfilment")
        if amount <= 0 or amount > promise.remaining_amount:
            raise WorkflowError("fulfilment amount exceeds remaining promise")
        fulfilled_amount = promise.fulfilled_amount + amount
        status = "fulfilled" if fulfilled_amount == promise.amount else "partial"
        updated = PromiseToPay(
            **{
                **promise.__dict__,
                "fulfilled_amount": fulfilled_amount,
                "fulfilment_source": source,
                "status": status,
            }
        )
        self._promises[promise_id] = updated
        self._audit(f"promise_{status}", promise_id)
        return updated

    def _get_proposal(self, proposal_id: str) -> WorkflowProposal:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise WorkflowError("proposal not found")
        return proposal

    def audit_events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def restore_audit_events(self, events: tuple[AuditEvent, ...]) -> None:
        """Restore persisted audit history without replaying domain mutations."""
        if self._events:
            raise WorkflowError("audit history must be restored before new events")
        self._events.extend(events)

    def proposals(self) -> tuple[WorkflowProposal, ...]:
        return tuple(self._proposals.values())

    def promises(self) -> tuple[PromiseToPay, ...]:
        return tuple(self._promises.values())

    def cases(self) -> tuple[CollectionCase, ...]:
        return tuple(self._cases.values())

    def outcomes(self) -> tuple[CollectionOutcome, ...]:
        return tuple(self._outcomes)
