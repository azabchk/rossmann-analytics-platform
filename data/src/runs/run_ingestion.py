"""Repeatable entrypoint for the Rossmann ingestion pipeline."""

from __future__ import annotations

import logging
import os
import traceback
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from ..ingest import read_store_csv, read_train_csv
from ..load import clear_staging_tables, load_operational_tables, promote_staging_to_base
from ..quality import validate_sales_records, validate_store_records
from ..transform import map_sales_columns, map_store_columns, normalize_sales, normalize_stores
from .models import (
    IngestionRun,
    IngestionRunStatus,
    TableValidationResult,
    ValidationIssue,
    ValidationIssueType,
    ValidationSeverity,
    create_ingestion_run,
)
from .persist_ingestion_run import (
    create_ingestion_run_db,
    save_validation_results_db,
    update_ingestion_run_db,
)
from .reporting import create_validation_report

logger = logging.getLogger(__name__)


def _sales_issue_type_to_generic(value: str) -> ValidationIssueType:
    if value in {
        "missing_required_field",
        "invalid_date_range",
        "invalid_day_of_week",
        "invalid_open_flag",
        "invalid_promo_flag",
        "invalid_school_holiday_flag",
        "invalid_state_holiday",
    }:
        return ValidationIssueType.STRUCTURAL
    if value == "duplicate_record":
        return ValidationIssueType.DUPLICATE
    if value == "extreme_outlier":
        return ValidationIssueType.OUTLIER
    return ValidationIssueType.LOGICAL


def _store_issue_type_to_generic(value: str) -> ValidationIssueType:
    if value == "missing_required_field":
        return ValidationIssueType.STRUCTURAL
    if value == "duplicate_store_id":
        return ValidationIssueType.DUPLICATE
    return ValidationIssueType.LOGICAL


def _to_table_validation_result(
    table_name: str,
    validation_result: Any,
    mapper: Callable[[str], ValidationIssueType],
) -> TableValidationResult:
    result = TableValidationResult(
        table_name=table_name,
        total_records=validation_result.total_records,
        valid_records=validation_result.valid_records,
    )

    for issue in validation_result.issues:
        result.add_issue(
            ValidationIssue(
                issue_type=mapper(issue.issue_type.value),
                severity=ValidationSeverity.ERROR,
                table=table_name,
                row_identifier=str(issue.record_index),
                field_name=issue.field_name,
                actual_value=issue.actual_value,
                expected_value=issue.expected,
                message=issue.message,
            )
        )

    for warning in validation_result.warnings:
        result.add_issue(
            ValidationIssue(
                issue_type=mapper(warning.issue_type.value),
                severity=ValidationSeverity.WARNING,
                table=table_name,
                row_identifier=str(warning.record_index),
                field_name=warning.field_name,
                actual_value=warning.actual_value,
                expected_value=warning.expected,
                message=warning.message,
            )
        )

    return result


def _append_missing_store_references(
    sales_result: TableValidationResult,
    train_df: pd.DataFrame,
    store_df: pd.DataFrame,
) -> None:
    sales_store_ids = pd.to_numeric(train_df["Store"], errors="coerce")
    known_store_ids = set(pd.to_numeric(store_df["Store"], errors="coerce").dropna().astype(int).tolist())
    missing_rows = train_df[sales_store_ids.notna() & ~sales_store_ids.isin(known_store_ids)]

    for _, row in missing_rows.iterrows():
        sales_result.add_issue(
            ValidationIssue(
                issue_type=ValidationIssueType.REFERENTIAL,
                severity=ValidationSeverity.ERROR,
                table=sales_result.table_name,
                row_identifier=f"store={int(row['Store'])};date={row['Date']}",
                field_name="Store",
                actual_value=row.get("Store"),
                expected_value="store id present in store.csv",
                message=(
                    "referential_integrity_violation: expected sales record store id to "
                    "exist in store metadata"
                ),
            )
        )
        sales_result.decrement_valid_records()


def _persist_run_snapshot(run: IngestionRun, database_url: str) -> None:
    update_ingestion_run_db(run, database_url)


def _parse_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def run_ingestion(
    train_csv_path: str,
    store_csv_path: str,
    database_url: str,
    use_staging: bool = True,
    upsert: bool = True,
    promote_after_staging: bool = True,
    triggered_by: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> IngestionRun:
    """Run the full ingestion workflow from CSV read to operational load."""

    merged_parameters = {
        "use_staging": use_staging,
        "upsert": upsert,
        "promote_after_staging": promote_after_staging,
    }
    if parameters:
        merged_parameters.update(parameters)

    run = create_ingestion_run(
        train_csv_path=train_csv_path,
        store_csv_path=store_csv_path,
        triggered_by=triggered_by,
        parameters=merged_parameters,
    )
    create_ingestion_run_db(run, database_url)

    try:
        run.start()
        _persist_run_snapshot(run, database_url)

        train_df = read_train_csv(train_csv_path)
        store_df = read_store_csv(store_csv_path)
        run.train_record_count = len(train_df)
        run.store_record_count = len(store_df)
        _persist_run_snapshot(run, database_url)

        run.set_status(IngestionRunStatus.VALIDATING)
        _persist_run_snapshot(run, database_url)

        sales_validation = validate_sales_records(train_df, strict=False)
        store_validation = validate_store_records(store_df, strict=False)

        sales_result = _to_table_validation_result(
            "sales_records",
            sales_validation,
            _sales_issue_type_to_generic,
        )
        store_result = _to_table_validation_result(
            "stores",
            store_validation,
            _store_issue_type_to_generic,
        )
        _append_missing_store_references(sales_result, train_df, store_df)

        run.add_validation_result(sales_result)
        run.add_validation_result(store_result)
        save_validation_results_db(run.run_id, run.validation_results, database_url)

        if run.has_validation_errors:
            message = f"Validation failed with {run.total_error_count} error(s)"
            run.fail(message)
            run.parameters["validation_report"] = create_validation_report(run).to_dict()
            _persist_run_snapshot(run, database_url)
            raise ValueError(message)

        run.parameters["validation_report"] = create_validation_report(run).to_dict()
        _persist_run_snapshot(run, database_url)

        run.set_status(IngestionRunStatus.TRANSFORMING)
        _persist_run_snapshot(run, database_url)

        normalized_sales = map_sales_columns(normalize_sales(train_df))
        normalized_stores = map_store_columns(normalize_stores(store_df))
        run.records_normalized = len(normalized_sales) + len(normalized_stores)
        _persist_run_snapshot(run, database_url)

        run.set_status(IngestionRunStatus.LOADING)
        _persist_run_snapshot(run, database_url)

        if use_staging:
            clear_staging_tables(database_url)

        load_result = load_operational_tables(
            sales_df=normalized_sales,
            stores_df=normalized_stores,
            database_url=database_url,
            use_staging=use_staging,
            upsert=upsert,
        )

        if use_staging and promote_after_staging:
            promotion_result = promote_staging_to_base(database_url)
            run.parameters["load_summary"] = {
                "staging_load": load_result,
                "promotion": promotion_result,
            }
            run.records_loaded = (
                promotion_result["sales_promoted"] + promotion_result["stores_promoted"]
            )
        else:
            run.parameters["load_summary"] = {"direct_load": load_result}
            run.records_loaded = load_result["sales_loaded"] + load_result["stores_loaded"]

        run.records_failed = max(
            (run.train_record_count + run.store_record_count) - run.records_loaded,
            0,
        )
        run.complete()
        run.parameters["validation_report"] = create_validation_report(run).to_dict()
        _persist_run_snapshot(run, database_url)
        return run

    except Exception as exc:
        if run.status not in {IngestionRunStatus.FAILED, IngestionRunStatus.CANCELLED}:
            run.fail(str(exc), traceback.format_exc())
            _persist_run_snapshot(run, database_url)
        raise


def main() -> None:
    """CLI entrypoint for local operator execution."""

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

    train_csv_path = os.getenv("ROSSMANN_TRAIN_PATH") or os.getenv("TRAIN_CSV_PATH")
    store_csv_path = os.getenv("ROSSMANN_STORE_PATH") or os.getenv("STORE_CSV_PATH")
    database_url = os.getenv("DATABASE_URL")

    if not train_csv_path or not store_csv_path or not database_url:
        raise SystemExit(
            "ROSSMANN_TRAIN_PATH/TRAIN_CSV_PATH, "
            "ROSSMANN_STORE_PATH/STORE_CSV_PATH, and DATABASE_URL are required"
        )

    run = run_ingestion(
        train_csv_path=str(Path(train_csv_path)),
        store_csv_path=str(Path(store_csv_path)),
        database_url=database_url,
        use_staging=_parse_bool_env("USE_STAGING", True),
        upsert=_parse_bool_env("UPSERT", True),
        promote_after_staging=_parse_bool_env("PROMOTE_AFTER_STAGING", True),
        triggered_by=os.getenv("TRIGGERED_BY"),
    )
    logger.info("Ingestion completed with run_id=%s status=%s", run.run_id, run.status.value)


if __name__ == "__main__":
    main()
