"""Deterministic, formula-safe reports for the offline validation CLI."""

import csv
import html
from io import StringIO
from typing import Iterable

from .decisioning import RankedAccount


QUEUE_FIELDS = (
    "customer_id",
    "legal_name",
    "outstanding_inr",
    "score",
    "overdue_days",
    "ageing_bucket",
    "eligible",
    "policy_version",
    "explanation",
    "missing_inputs",
)


def queue_rows(ranked: Iterable[RankedAccount]) -> list[dict[str, str]]:
    return [
        {
            "customer_id": item.customer_id,
            "legal_name": item.legal_name,
            "outstanding_inr": f"{item.outstanding:.2f}",
            "score": f"{item.score:.2f}",
            "overdue_days": str(item.overdue_days),
            "ageing_bucket": item.ageing_bucket,
            "eligible": str(item.eligible).lower(),
            "policy_version": item.policy_version,
            "explanation": item.explanation,
            "missing_inputs": ",".join(item.missing_inputs),
        }
        for item in ranked
    ]


def render_queue_text(ranked: Iterable[RankedAccount]) -> str:
    rows = queue_rows(ranked)
    if not rows:
        return "queue=empty\n"
    return "".join(
        "customer={legal_name} outstanding={outstanding_inr} score={score} "
        "bucket={ageing_bucket} eligible={eligible} risks={missing_inputs}\n".format(
            **row
        )
        for row in rows
    )


def render_queue_csv(ranked: Iterable[RankedAccount]) -> str:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=QUEUE_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in queue_rows(ranked):
        writer.writerow({key: _neutralize(str(row[key])) for key in QUEUE_FIELDS})
    return output.getvalue()


def render_queue_html(ranked: Iterable[RankedAccount]) -> str:
    rows = queue_rows(ranked)
    headers = "".join(f"<th>{html.escape(field)}</th>" for field in QUEUE_FIELDS)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{html.escape(row[field])}</td>" for field in QUEUE_FIELDS)
        + "</tr>"
        for row in rows
    )
    return (
        "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
        "<title>Bharat ARP queue</title><body><main>"
        "<h1>Collection queue</h1><table><thead><tr>"
        + headers
        + "</tr></thead><tbody>"
        + body
        + "</tbody></table></main></body></html>\n"
    )


def _neutralize(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
