from bharat_arp.dag import DagTask, SimpleDag


def test_topological_order():
    t1 = DagTask("extract")
    t2 = DagTask("transform", deps=["extract"])
    t3 = DagTask("load", deps=["transform"])
    dag = SimpleDag([t3, t1, t2])
    assert dag.execution_order() == ["extract", "transform", "load"]


def test_run_all_executes_in_order():
    t1 = DagTask("a")
    t2 = DagTask("b", deps=["a"])
    dag = SimpleDag([t1, t2])
    calls = []
    dag.run_all({"a": lambda: calls.append("a"), "b": lambda: calls.append("b")})
    assert calls == ["a", "b"]
    assert dag.status_summary() == {"a": "success", "b": "success"}


def test_cycle_detected():
    t1 = DagTask("a", deps=["b"])
    t2 = DagTask("b", deps=["a"])
    try:
        SimpleDag([t1, t2])
    except ValueError:
        pass
    else:
        raise AssertionError("cycle accepted")


def test_unknown_dependency():
    t1 = DagTask("a", deps=["missing"])
    try:
        SimpleDag([t1])
    except ValueError:
        pass
    else:
        raise AssertionError("unknown dep accepted")


def test_duplicate_task_ids():
    try:
        SimpleDag([DagTask("a"), DagTask("a")])
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate accepted")


def test_failed_dependency_blocks():
    t1 = DagTask("a")
    t2 = DagTask("b", deps=["a"])
    dag = SimpleDag([t1, t2])
    try:
        dag.run_all(
            {
                "a": lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                "b": lambda: None,
            }
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")
    assert dag.tasks["a"].status == "failed"
