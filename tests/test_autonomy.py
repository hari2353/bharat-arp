from bharat_arp.autonomy import AutonomyState, AutonomyLevel, record_outcome, gate_action


def test_starts_at_draft():
    s = AutonomyState()
    assert s.level == AutonomyLevel.DRAFT
    assert gate_action(s, reversible=True) == (False, "draft: human approval required")


def test_promotes_to_suggest_after_3_successes():
    s = AutonomyState()
    for _ in range(3):
        record_outcome(s, True)
    assert s.level == AutonomyLevel.SUGGEST


def test_promotes_to_auto_after_8_successes():
    s = AutonomyState()
    for _ in range(8):
        record_outcome(s, True)
    assert s.level == AutonomyLevel.AUTO
    assert gate_action(s, reversible=True) == (True, "auto: earned authority")


def test_irreversible_needs_approval_even_at_auto():
    s = AutonomyState()
    for _ in range(8):
        record_outcome(s, True)
    assert gate_action(s, reversible=False) == (False, "irreversible action requires human approval")


def test_failure_demotes():
    s = AutonomyState()
    for _ in range(8):
        record_outcome(s, True)
    assert s.level == AutonomyLevel.AUTO
    record_outcome(s, False)
    assert s.level == AutonomyLevel.SUGGEST


def test_two_consecutive_failures_drop_to_draft():
    s = AutonomyState()
    for _ in range(8):
        record_outcome(s, True)
    record_outcome(s, False)
    record_outcome(s, False)
    assert s.level == AutonomyLevel.DRAFT

