"""Graduated autonomy gate — borrowed from SHAKE's "earned authority" idea.

An agent starts at `draft` level (drafts only, human approves). It earns
`suggest` after 3 successful outcomes, and `auto` after 5 more. Any failure
demotes one level; 2 consecutive failures drop back to `draft`. This mirrors
india-quant's live-plan/approve-plan/live-execute approval gate.

Rules:
- A `reversible` action may be auto-executed at `auto` level.
- An `irreversible` action (e.g. sending a collection notice) always needs
  human approval, regardless of level — "does it know which of its actions
  can't be undone?".
- A language model is never the source of a number; amounts come from code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AutonomyLevel(str, Enum):
    DRAFT = "draft"
    SUGGEST = "suggest"
    AUTO = "auto"


@dataclass
class AutonomyState:
    level: AutonomyLevel = AutonomyLevel.DRAFT
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0


PROMOTE_TO_SUGGEST = 3
PROMOTE_TO_AUTO = 5


def record_outcome(state: AutonomyState, success: bool) -> AutonomyState:
    """Update authority based on an action's outcome. Returns the same state."""
    if success:
        state.successes += 1
        state.consecutive_failures = 0
        if state.level == AutonomyLevel.DRAFT and state.successes >= PROMOTE_TO_SUGGEST:
            state.level = AutonomyLevel.SUGGEST
        elif state.level == AutonomyLevel.SUGGEST and state.successes >= (PROMOTE_TO_SUGGEST + PROMOTE_TO_AUTO):
            state.level = AutonomyLevel.AUTO
    else:
        state.failures += 1
        state.consecutive_failures += 1
        if state.consecutive_failures >= 2:
            state.level = AutonomyLevel.DRAFT
        elif state.level == AutonomyLevel.AUTO:
            state.level = AutonomyLevel.SUGGEST
        elif state.level == AutonomyLevel.SUGGEST:
            state.level = AutonomyLevel.DRAFT
    return state


def gate_action(state: AutonomyState, *, reversible: bool) -> tuple[bool, str]:
    """Return (auto_allowed, reason). auto_allowed=True means the agent may act
    without human approval."""
    if not reversible:
        return False, "irreversible action requires human approval"
    if state.level == AutonomyLevel.AUTO:
        return True, "auto: earned authority"
    if state.level == AutonomyLevel.SUGGEST:
        return False, "suggest: human approval required"
    return False, "draft: human approval required"

