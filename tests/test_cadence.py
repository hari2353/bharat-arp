"""Dunning cadence proposals — Upflow/Chaser's core loop, reshaped to this
repo's doctrine: a deterministic ladder of follow-up steps per account,
advancing at most one step per review, pausing on a live promise, stopping
on payment. Every step is an approval-gated proposal; nothing is sent."""
from datetime import date
from decimal import Decimal

from bharat_arp.cadence import CADENCE_STEPS, CadenceState, next_cadence_step
from bharat_arp.decisioning import RankedAccount


def ranked(overdue_days=10, outstanding="125000.00", eligible=True):
    return RankedAccount(
        customer_id="CUST-1", legal_name="Acme", score=Decimal("100.00"),
        outstanding=Decimal(outstanding), overdue_days=overdue_days,
        ageing_bucket="1_29", eligible=eligible, policy_version="v1",
        explanation="outstanding_inr=125000.00", missing_inputs=(),
    )


# ---------------------------------------------------------------- ladder
def test_first_step_is_a_gentle_reminder_once_overdue():
    p = next_cadence_step(ranked(overdue_days=3), CadenceState("CUST-1"),
                          as_of=date(2026, 9, 30))
    assert p.step_name == "gentle_reminder"
    assert p.action == "draft_customer_follow_up"
    assert p.requires_approval is True and p.executes_side_effect is False
    assert p.policy_version == "cadence-2026-11"


def test_ladder_advanges_one_step_per_call_regardless_of_ageing():
    state = CadenceState("CUST-1")
    p1 = next_cadence_step(ranked(overdue_days=90), state, as_of=date(2026, 9, 30))
    assert p1.step_name == "gentle_reminder"
    state2 = CadenceState("CUST-1", step=1)
    p2 = next_cadence_step(ranked(overdue_days=90), state2, as_of=date(2026, 9, 30))
    assert p2.step_name == "firm_reminder"


def test_ageing_gate_blocks_steps_the_account_has_not_aged_into():
    state = CadenceState("CUST-1", step=1)           # next: firm (>=15d)
    p = next_cadence_step(ranked(overdue_days=10), state, as_of=date(2026, 9, 30))
    assert p is None                                  # too early to firm up


def test_terminal_step_is_idempotent():
    state = CadenceState("CUST-1", step=len(CADENCE_STEPS))
    p = next_cadence_step(ranked(overdue_days=200), state, as_of=date(2026, 9, 30))
    assert p.step_index == len(CADENCE_STEPS)
    assert p.step_name == CADENCE_STEPS[-1].name       # stays, never beyond


def test_step_names_and_thresholds_are_the_documented_ladder():
    assert [(s.name, s.min_overdue_days) for s in CADENCE_STEPS] == [
        ("gentle_reminder", 1), ("firm_reminder", 15), ("final_notice", 30),
        ("owner_escalation", 45), ("credit_hold_review", 60),
    ]


# ---------------------------------------------------------------- stops
def test_live_promise_pauses_the_cadence_even_as_ageing_grows():
    state = CadenceState("CUST-1", step=2, paused_until=date(2026, 10, 15))
    p = next_cadence_step(ranked(overdue_days=90), state, as_of=date(2026, 10, 1))
    assert p is None                                   # promise beats ageing


def test_expired_promise_restarts_the_cadence_at_the_same_step():
    state = CadenceState("CUST-1", step=2, paused_until=date(2026, 9, 1))
    p = next_cadence_step(ranked(overdue_days=90), state, as_of=date(2026, 9, 30))
    assert p is not None and p.step_index == 3         # resumes, no restart


def test_paid_or_ineligible_account_yields_nothing():
    assert next_cadence_step(ranked(eligible=False), CadenceState("CUST-1"),
                             as_of=date(2026, 9, 30)) is None
    assert next_cadence_step(ranked(outstanding="0.00"), CadenceState("CUST-1"),
                             as_of=date(2026, 9, 30)) is None


def test_not_yet_overdue_account_yields_nothing():
    assert next_cadence_step(ranked(overdue_days=0), CadenceState("CUST-1"),
                             as_of=date(2026, 9, 30)) is None


# ---------------------------------------------------------------- evidence
def test_proposal_carries_its_evidence():
    p = next_cadence_step(ranked(overdue_days=20), CadenceState("CUST-1", step=1),
                          as_of=date(2026, 9, 30))
    assert "CUST-1" in p.reason and "20" in p.reason    # customer + ageing
    assert p.policy_version == "cadence-2026-11"


def test_cadence_chases_only_undisputed_exposure():
    """120k outstanding with 70k on disputed lines: the follow-up proposal
    chases 50k and its evidence says what was contained."""
    account = RankedAccount(
        customer_id="CUST-1", legal_name="Acme", score=Decimal("100.00"),
        outstanding=Decimal("120000.00"), overdue_days=10,
        ageing_bucket="1_29", eligible=True, policy_version="v1",
        explanation="outstanding_inr=120000.00", missing_inputs=(),
        disputed_outstanding=Decimal("70000.00"),
    )
    p = next_cadence_step(account, CadenceState("CUST-1"), as_of=date(2026, 9, 30))
    assert p.outstanding == Decimal("50000.00")
    assert "dispute_contained_inr=70000.00" in p.reason


def test_cadence_state_for_a_different_account_is_rejected():
    """A state applied to the wrong account must not silently advance that
    account's ladder (review minor #7)."""
    from bharat_arp.cadence import CadenceState
    r = ranked()
    wrong = CadenceState("CUST-OTHER")
    assert next_cadence_step(r, wrong, as_of=date(2026, 9, 30)) is None
