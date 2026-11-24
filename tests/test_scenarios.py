from bharat_arp.scenarios import run_scenarios


def test_all_safe():
    out = run_scenarios([("a", lambda: None), ("b", lambda: None)], deadline_s=10)
    assert out["safe"] == 2 and out["safe_rate"] == 1.0


def test_deadline_miss():
    ticks = iter([0.0, 2.0, 2.0, 2.5])
    out = run_scenarios(
        [("slow", lambda: None)], deadline_s=1, clock=lambda: next(ticks)
    )
    assert out["scenarios"][0]["success"] is True
    assert out["safe"] == 0
    assert "deadline" in out["failures"][0]["detail"]


def test_exception_is_failure():
    out = run_scenarios(
        [("boom", lambda: (_ for _ in ()).throw(RuntimeError("x")))], deadline_s=10
    )
    assert out["safe"] == 0
    assert "error: x" in out["failures"][0]["detail"]


def test_invalid_inputs():
    for scenarios, deadline in (
        ([], 1),
        ([("", lambda: None)], 1),
        ([("a", lambda: None)], 0),
    ):
        try:
            run_scenarios(scenarios, deadline_s=deadline)
        except ValueError:
            continue
        raise AssertionError("invalid input accepted")
