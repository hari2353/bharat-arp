"""Normalize validated CSV rows with idempotent source identity semantics."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .contracts import CsvError
from .models import (
    CreditNote,
    Dispute,
    InvoiceRecord,
    Payment,
    PaymentAllocation,
    SourceRef,
)


@dataclass(frozen=True)
class CustomerRecord:
    ref: SourceRef
    legal_name: str
    status: str


@dataclass(frozen=True)
class ContactRecord:
    ref: SourceRef
    customer_id: str
    display_name: str
    role: str
    email: str
    phone: str
    email_permission: str
    whatsapp_permission: str
    opted_out: bool
    permission_observed_at: datetime | None


@dataclass(frozen=True)
class DisputeRecord:
    ref: SourceRef
    customer_id: str
    invoice_id: str
    category: str
    status: str
    opened_at: datetime
    resolved_at: datetime | None


@dataclass(frozen=True)
class NormalizationResult:
    created: int
    updated: int
    unchanged: int
    errors: tuple[CsvError, ...]


@dataclass(frozen=True)
class _Version:
    value: Any
    fingerprint: tuple[tuple[str, str], ...]


def _parse_date(value: str, field: str, errors: list[CsvError]) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(CsvError(None, "invalid_date", f"{field} must be ISO-8601 date."))
        return None


def _parse_datetime(value: str, field: str, errors: list[CsvError]) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        errors.append(CsvError(None, "invalid_timestamp", f"{field} must be ISO-8601."))
        return None


def _parse_amount(value: str, errors: list[CsvError]) -> Decimal | None:
    try:
        amount = Decimal(value)
    except InvalidOperation:
        errors.append(CsvError(None, "invalid_amount", "Amount must be a decimal value."))
        return None
    if not amount.is_finite() or amount.as_tuple().exponent < -2:
        errors.append(CsvError(None, "invalid_amount", "Amount must have at most two decimals."))
        return None
    return amount


def _bool(value: str, errors: list[CsvError]) -> bool | None:
    if value in {"true", "false"}:
        return value == "true"
    errors.append(CsvError(None, "invalid_boolean", "Boolean must be true or false."))
    return None


def _source_ref(record_type: str, row: dict[str, str]) -> SourceRef:
    return SourceRef(
        tenant_id=row["tenant_id"],
        source_system=row["source_system"],
        source_record_id=row["source_record_id"],
        record_type=record_type,
        source_updated_at=datetime.fromisoformat(row["source_updated_at"]),
        import_batch_id=row["import_batch_id"],
    )


def _normalize(record_type: str, row: dict[str, str]) -> tuple[Any | None, tuple[CsvError, ...]]:
    errors: list[CsvError] = []
    try:
        ref = _source_ref(record_type[:-1] if record_type.endswith("s") else record_type, row)
    except (KeyError, ValueError):
        return None, (CsvError(None, "invalid_source_ref", "Source provenance is invalid."),)

    if record_type == "customers":
        return CustomerRecord(ref, row["legal_name"], row["status"]), ()
    if record_type == "contacts":
        permission_observed_at = (
            _parse_datetime(row["permission_observed_at"], "permission_observed_at", errors)
            if row["permission_observed_at"]
            else None
        )
        opted_out = _bool(row["opted_out"], errors)
        if errors or opted_out is None:
            return None, tuple(errors)
        return ContactRecord(
            ref,
            row["source_customer_id"],
            row["display_name"],
            row["role"],
            row["email"],
            row["phone"],
            row["email_permission"],
            row["whatsapp_permission"],
            opted_out,
            permission_observed_at,
        ), ()
    if record_type == "invoices":
        invoice_date = _parse_date(row["invoice_date"], "invoice_date", errors)
        due_date = _parse_date(row["due_date"], "due_date", errors)
        amount = _parse_amount(row["amount_inr"], errors)
        if errors or invoice_date is None or due_date is None or amount is None:
            return None, tuple(errors)
        return InvoiceRecord(ref, row["source_customer_id"], invoice_date, due_date, amount, row["status"]), ()
    if record_type == "payments":
        payment_date = _parse_date(row["payment_date"], "payment_date", errors)
        amount = _parse_amount(row["amount_inr"], errors)
        if errors or payment_date is None or amount is None:
            return None, tuple(errors)
        return Payment(ref, payment_date, amount, row["status"]), ()
    if record_type == "payment_allocations":
        amount = _parse_amount(row["allocated_amount_inr"], errors)
        if errors or amount is None:
            return None, tuple(errors)
        return PaymentAllocation(
            ref, row["source_payment_id"], row["source_invoice_id"], amount
        ), ()
    if record_type == "credit_notes":
        credit_date = _parse_date(row["credit_date"], "credit_date", errors)
        amount = _parse_amount(row["amount_inr"], errors)
        if errors or credit_date is None or amount is None:
            return None, tuple(errors)
        return CreditNote(ref, row["source_invoice_id"], amount, row["status"]), ()
    if record_type == "disputes":
        opened_at = _parse_datetime(row["opened_at"], "opened_at", errors)
        resolved_at = (
            _parse_datetime(row["resolved_at"], "resolved_at", errors)
            if row["resolved_at"]
            else None
        )
        if errors or opened_at is None:
            return None, tuple(errors)
        return Dispute(
            ref,
            row["source_customer_id"],
            row["source_invoice_id"],
            row["category"],
            row["status"],
            opened_at,
            resolved_at,
        ), ()
    return None, (CsvError(None, "unsupported_record_type", "Unsupported record type."),)


class NormalizedSourceStore:
    """Small local source store; persistence is intentionally a later slice."""

    def __init__(self, *, tenant_id: str = "TENANT-1") -> None:
        self.tenant_id = tenant_id
        self._history: dict[tuple[str, str, str, str], list[_Version]] = {}

    def upsert_rows(self, record_type: str, rows: list[dict[str, str]]) -> NormalizationResult:
        created = updated = unchanged = 0
        errors: list[CsvError] = []
        for row in rows:
            if row.get("tenant_id") != self.tenant_id:
                errors.append(CsvError(None, "tenant_mismatch", "Row tenant does not match the store."))
                continue
            value, row_errors = _normalize(record_type, row)
            if row_errors or value is None:
                errors.extend(row_errors)
                continue
            key = value.ref.identity
            fingerprint = tuple(sorted((key, str(item)) for key, item in row.items()))
            versions = self._history.setdefault(key, [])
            if versions and versions[-1].fingerprint == fingerprint:
                unchanged += 1
            elif versions:
                versions.append(_Version(value, fingerprint))
                updated += 1
            else:
                versions.append(_Version(value, fingerprint))
                created += 1
        return NormalizationResult(created, updated, unchanged, tuple(errors))

    def current_records(self, record_type: str) -> tuple[Any, ...]:
        normalized_type = record_type[:-1] if record_type.endswith("s") else record_type
        return tuple(
            versions[-1].value
            for key, versions in self._history.items()
            if key[3] == normalized_type
        )

    def history(self, record_type: str, source_record_id: str) -> tuple[Any, ...]:
        normalized_type = record_type[:-1] if record_type.endswith("s") else record_type
        return tuple(
            version.value
            for key, versions in self._history.items()
            if key[2] == source_record_id and key[3] == normalized_type
            for version in versions
        )
