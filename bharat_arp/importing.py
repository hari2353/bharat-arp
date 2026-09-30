"""Validate CSV input before any financial normalization or decisioning."""

import csv
from datetime import datetime
from io import StringIO

from .contracts import COMMON_FIELDS, REQUIRED_FIELDS, CsvError, CsvValidationResult


MAX_ROWS = 100_000
MAX_BYTES = 10 * 1024 * 1024
MAX_FIELD_LENGTH = 4096


def validate_csv_text(
    record_type: str,
    text: str,
    *,
    tenant_id: str,
    import_batch_id: str,
) -> CsvValidationResult:
    """Validate one UTF-8-decoded contract file without leaking row values."""
    errors: list[CsvError] = []
    rows: list[dict[str, str]] = []
    seen_identity: set[tuple[str, str, str, str]] = set()

    required_fields = REQUIRED_FIELDS.get(record_type)
    if required_fields is None:
        return CsvValidationResult(
            record_type=record_type,
            rows=(),
            errors=(CsvError(None, "unsupported_record_type", "Unsupported CSV record type."),),
        )

    if len(text.encode("utf-8")) > MAX_BYTES:
        return CsvValidationResult(
            record_type=record_type,
            rows=(),
            errors=(CsvError(None, "file_too_large", "CSV file exceeds the size limit."),),
        )

    reader = csv.DictReader(StringIO(text, newline=""))
    headers = reader.fieldnames
    if not headers:
        return CsvValidationResult(
            record_type=record_type,
            rows=(),
            errors=(CsvError(None, "missing_header", "CSV header is required."),),
        )

    if len(headers) != len(set(headers)):
        errors.append(CsvError(None, "duplicate_header", "CSV contains duplicate headers."))
    unknown_headers = set(headers) - set(required_fields)
    if unknown_headers:
        errors.append(CsvError(None, "unknown_header", "CSV contains unknown headers."))
    missing_headers = set(required_fields) - set(headers)
    if missing_headers:
        errors.append(CsvError(None, "missing_header", "CSV is missing required headers."))
    header_errors = tuple(errors)
    if missing_headers or len(headers) != len(set(headers)):
        return CsvValidationResult(record_type, (), tuple(errors))

    for row_number, row in enumerate(reader, start=2):
        if row_number - 1 > MAX_ROWS:
            errors.append(CsvError(row_number, "row_limit_exceeded", "CSV exceeds the row limit."))
            break
        if None in row:
            errors.append(CsvError(row_number, "malformed_row", "CSV row has too many fields."))
            continue
        values = {key: value or "" for key, value in row.items()}
        if any(len(value) > MAX_FIELD_LENGTH for value in values.values()):
            errors.append(CsvError(row_number, "field_too_large", "CSV field exceeds the size limit."))
            continue
        if values["tenant_id"] != tenant_id:
            errors.append(CsvError(row_number, "tenant_mismatch", "CSV tenant does not match the configured tenant."))
            continue
        if values["import_batch_id"] != import_batch_id:
            errors.append(CsvError(row_number, "batch_mismatch", "CSV batch does not match the configured batch."))
            continue
        timestamp_valid = True
        try:
            datetime.fromisoformat(values["source_updated_at"])
        except ValueError:
            timestamp_valid = False
            errors.append(CsvError(row_number, "invalid_timestamp", "source_updated_at must be ISO-8601."))
        required_values_valid = not any(not values[field].strip() for field in required_fields)
        if not required_values_valid:
            errors.append(CsvError(row_number, "missing_required_value", "CSV row has a missing required value."))
        if not timestamp_valid or not required_values_valid:
            continue

        identity = (
            values["tenant_id"],
            values["source_system"],
            values["source_record_id"],
            record_type[:-1] if record_type.endswith("s") else record_type,
        )
        if identity in seen_identity:
            errors.append(CsvError(row_number, "duplicate_identity", "CSV source identity is duplicated."))
            continue
        seen_identity.add(identity)
        rows.append(values)

    if header_errors:
        return CsvValidationResult(record_type, (), tuple(errors))
    if errors:
        return CsvValidationResult(record_type, (), tuple(errors))
    return CsvValidationResult(record_type, tuple(rows), ())
