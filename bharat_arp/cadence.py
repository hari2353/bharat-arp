"""Dunning cadence proposals — the category's core loop (Upflow/Chaser
sequences, Gaviti playbooks) reshaped to this repo's doctrine.

A deterministic ladder of follow-up steps per account: advance at most one
step per review, never into an ageing band the account has not reached,
pause while a promise to pay is live, stop when the account is paid or
ineligible. Every step is an approval-gated proposal — this module cannot
send, write, or mutate anything.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .decisioning import RankedAccount

POLICY_VERSION = "cadence-2026-11"


@dataclass(frozen=True)
class CadenceStep:
    name: str
    action: str
    min_overdue_days: int


CADENCE_STEPS: tuple[CadenceStep, ...] = (
    CadenceStep("gentle_reminder", "draft_customer_follow_up", 1),
    CadenceStep("firm_reminder", "draft_customer_follow_up", 15),
    CadenceStep("final_notice", "draft_escalation_review", 30),
    CadenceStep("owner_escalation", "draft_escalation_review", 45),
    CadenceStep("credit_hold_review", "credit_hold_review", 60),
)


@dataclass(frozen=True)
class CadenceState:
    customer_id: str
    step: int = 0                       # 0 = no cadence action issued yet
    last_action_on: date | None = None
    paused_until: date | None = None    # live promise to pay


@dataclass(frozen=True)
class CadenceProposal:
    customer_id: str
    action: str
    reason: str
    expected_outcome: str
    policy_version: str
    requires_approval: bool
    executes_side_effect: bool
    outstanding: Decimal
    step_index: int                     # 1-based position on the ladder
    step_name: str


def next_cadence_step(
    ranked: RankedAccount, state: CadenceState, *, as_of: date
) -> CadenceProposal | None:
    """The next cadence step for one account, or None when there is nothing
    safe to propose. Deterministic: `as_of` is an argument, never the clock."""
    if state.customer_id != ranked.customer_id:
        return None                     # a state from another account never advances this ladder
    if not ranked.eligible or ranked.outstanding <= 0 or ranked.overdue_days < 1:
        return None
    # the ladder chases undisputed money only; disputed lines are contained
    undisputed = ranked.outstanding - (ranked.disputed_outstanding or Decimal("0.00"))
    if undisputed <= 0:
        return None
    if state.paused_until is not None and state.paused_until > as_of:
        return None                     # a live promise outranks the ageing
    # advance at most one step; the terminal step re-issues in place
    index = min(state.step + 1, len(CADENCE_STEPS))
    step = CADENCE_STEPS[index - 1]
    if ranked.overdue_days < step.min_overdue_days:
        return None                     # not aged into this band yet
    reason = (
        f"customer={ranked.customer_id}; overdue_days={ranked.overdue_days}; "
        f"cadence step {index}/{len(CADENCE_STEPS)} {step.name} "
        f"(min_overdue_days={step.min_overdue_days}); "
        f"undisputed_outstanding_inr={undisputed:.2f}"
    )
    if ranked.disputed_outstanding:
        reason += f"; dispute_contained_inr={ranked.disputed_outstanding:.2f}"
    return CadenceProposal(
        customer_id=ranked.customer_id,
        action=step.action,
        reason=reason,
        expected_outcome="payment or a dated promise to pay",
        policy_version=POLICY_VERSION,
        requires_approval=True,
        executes_side_effect=False,
        outstanding=undisputed,
        step_index=index,
        step_name=step.name,
    )
