from bharat_arp.importing import validate_csv_text


COMMON = (
    "tenant_id,source_system,source_record_id,source_updated_at,import_batch_id"
)


def csv_text(rows: str, *, extra_headers: str = "") -> str:
    return (
        f"{COMMON},source_customer_id,legal_name,status{extra_headers}\n"
        f"{rows}"
    )


def test_valid_customer_csv_preserves_rows_without_exposing_values_in_errors():
    result = validate_csv_text(
        "customers",
        csv_text(
            "TENANT-1,erpnext_csv,CUST-1,2026-09-30T10:00:00+05:30,BATCH-1,"
            "CUST-1,Sharma Engineering,active\n"
        ),
        tenant_id="TENANT-1",
        import_batch_id="BATCH-1",
    )

    assert result.rows == (
        {
            "tenant_id": "TENANT-1",
            "source_system": "erpnext_csv",
            "source_record_id": "CUST-1",
            "source_updated_at": "2026-09-30T10:00:00+05:30",
            "import_batch_id": "BATCH-1",
            "source_customer_id": "CUST-1",
            "legal_name": "Sharma Engineering",
            "status": "active",
        },
    )
    assert result.errors == ()


def test_mismatched_tenant_is_rejected_with_redacted_row_error():
    result = validate_csv_text(
        "customers",
        csv_text(
            "OTHER-TENANT,erpnext_csv,CUST-1,2026-09-30T10:00:00+05:30,BATCH-1,"
            "CUST-1,Secret Customer Name,active\n"
        ),
        tenant_id="TENANT-1",
        import_batch_id="BATCH-1",
    )

    assert result.rows == ()
    assert result.errors[0].row_number == 2
    assert result.errors[0].code == "tenant_mismatch"
    assert "Secret Customer Name" not in result.errors[0].message


def test_unknown_headers_and_duplicate_identity_are_rejected():
    text = csv_text(
        "TENANT-1,erpnext_csv,CUST-1,2026-09-30T10:00:00+05:30,BATCH-1,"
        "CUST-1,Customer One,active\n"
        "TENANT-1,erpnext_csv,CUST-1,2026-09-30T10:00:00+05:30,BATCH-1,"
        "CUST-1,Customer One,active\n",
        extra_headers=",unexpected",
    ).replace("active\n", "active,ignored\n")

    result = validate_csv_text(
        "customers",
        text,
        tenant_id="TENANT-1",
        import_batch_id="BATCH-1",
    )

    assert result.rows == ()
    assert {error.code for error in result.errors} == {
        "unknown_header",
        "duplicate_identity",
    }


def test_invalid_timestamp_and_missing_required_value_are_reported():
    result = validate_csv_text(
        "customers",
        csv_text("TENANT-1,erpnext_csv,CUST-1,not-a-time,BATCH-1,, ,active\n"),
        tenant_id="TENANT-1",
        import_batch_id="BATCH-1",
    )

    assert result.rows == ()
    assert {error.code for error in result.errors} == {
        "invalid_timestamp",
        "missing_required_value",
    }


def test_duplicate_header_is_rejected_before_rows_are_parsed():
    result = validate_csv_text(
        "customers",
        f"{COMMON},source_customer_id,legal_name,status,status\n",
        tenant_id="TENANT-1",
        import_batch_id="BATCH-1",
    )

    assert result.rows == ()
    assert result.errors[0].code == "duplicate_header"
