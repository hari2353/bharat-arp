"""DAG task orchestration (cross-pollinated from Airbnb/Airflow).

A simple directed acyclic graph of tasks with topological execution order
and status tracking. Pure Python, no scheduler dependency.
"""
from __future__ import annotations

from collections import deque


class DagTask:
    def __init__(self, task_id: str, deps: list[str] | None = None) -> None:
        if not task_id.strip():
            raise ValueError("task_id must be non-empty")
        self.task_id = task_id
        self.deps = list(deps or [])
        self.status = "pending"  # pending, running, success, failed

    def run(self, fn) -> None:
        self.status = "running"
        try:
            fn()
            self.status = "success"
        except Exception:
            self.status = "failed"
            raise


class SimpleDag:
    def __init__(self, tasks: list[DagTask]) -> None:
        ids = [t.task_id for t in tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate task ids")
        self.tasks = {t.task_id: t for t in tasks}
        self._order = self._topological_sort(tasks)

    def _topological_sort(self, tasks: list[DagTask]) -> list[str]:
        in_degree = {t.task_id: 0 for t in tasks}
        adj: dict[str, list[str]] = {t.task_id: [] for t in tasks}
        for t in tasks:
            for dep in t.deps:
                if dep not in self.tasks:
                    raise ValueError(f"unknown dependency: {dep}")
                adj[dep].append(t.task_id)
                in_degree[t.task_id] += 1
        queue = deque(sorted(tid for tid, deg in in_degree.items() if deg == 0))
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for child in sorted(adj[node]):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        if len(order) != len(tasks):
            raise ValueError("cycle detected in DAG")
        return order

    def execution_order(self) -> list[str]:
        return list(self._order)

    def run_all(self, fns: dict[str, object]) -> None:
        for tid in self._order:
            task = self.tasks[tid]
            if task.status != "pending":
                continue
            # check deps succeeded
            for dep in task.deps:
                if self.tasks[dep].status != "success":
                    task.status = "failed"
                    raise RuntimeError(f"dependency {dep} did not succeed")
            task.run(fns[tid])  # type: ignore

    def status_summary(self) -> dict[str, str]:
        return {tid: t.status for tid, t in self.tasks.items()}
