"""Main ingestion pipeline entry point.

This module provides the run_ingestion function that orchestrates the
entire data ingestion pipeline from reading raw files through validation,
transformation, and loading into operational tables.
"""

import logging
import os
from pathlib import Path
from typing import Any

from ..ingest import read_train_csv, read_store_csv
from ..quality import validate_sales_records, validate_store_records
from ..transform import normalize_sales, normalize_stores, map_sales_columns, map_store_columns
from ..load import load_operational_tables, clear_staging_tables
from .models import (
    IngestionRun,
    IngestionRunStatus,
    TableValidationResult,
    ValidationIssue,
    ValidationIssueType,
    ValidationSeverity,
)
from .persist_ingestion_run import (
    create_ingestion_run_db,
    update_ingestion_run_db,
    save_validation_results_db,
)
from .reporting import create_validation_report

logger = logging.getLogger(__name__)


def run_ingestion(
    train_csv_path: str,
    store_csv_path: str,
    database_url: str,
    use_staging: bool = True,
    upsert: bool = True,
    triggered_by: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> IngestionRun:
    """Run the complete data ingestion pipeline.

    Pipeline stages:
    1. Create run record in database
    2. Read raw CSV files
    3. Validate data quality
    4. Normalize and clean data
    5. Load into database tables
    6. Update run status and save results

    Args:
        train_csv_path: Path to the train.csv file
        store_csv_path: Path to the store.csv file
        database_url: Database connection URL
        use_staging: If True, use staging tables before promotion
        upsert: If True, perform upsert. If False, insert only.
        triggered_by: User or system that triggered the run
        parameters: Additional pipeline parameters

    Returns:
        IngestionRun with final status and results

    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If validation fails critically
        Exception: If pipeline execution fails
    """
    # Create run instance
    run = IngestionRun(
        train_csv_path=train_csv_path,
        store_csv_path=store_csv_path,
        triggered_by=triggered_by,
        parameters=parameters or {},
    )

    # Initial persist
    create_ingestion_run_db(run, database_url)

    try:
        # STAGE 1: START
        run.start()
        update_ingestion_run_db(run, database_url)
        logger.info(f"Starting ingestion run {run.run_id}")

        # STAGE 2: READ
        run.set_status(IngestionRunStatus.RUNNING)
        update_ingestion_run_db(run, database_url)
        logger.info("Reading raw CSV files...")

        train_df = read_train_csv(train_csv_path)
        store_df = read_store_csv(store_csv_path)

        run.train_record_count = len(train_df)
        run.store_record_count = len(store_df)
        update_ingestion_run_db(run, database_url)
        logger.info(f"Read {run.train_record_count} sales records, {run.store_record_count} store records")

        # STAGE 3: VALIDATE
        run.set_status(IngestionRunStatus.VALIDATING)
        update_ingestion_run_db(run, database_url)
        logger.info("Validating data quality...")

        sales_validation = validate_sales_records(train_df, strict=False)
        store_validation = validate_store_records(store_df, strict=False)

        # Convert validation results to TableValidationResult format
        sales_result = _convert_sales_validation(sales_validation, run.train_record_count)
        store_result = _convert_store_validation(store_validation, run.store_record_count)

        run.add_validation_result(sales_result)
        run.add_validation_result(store_result)

        # Save validation results
        save_validation_results_db(
            run.run_id,
            run.validation_results,
            database_url,
        )

        # Check for critical errors
        if sales_result.has_errors or store_result.has_errors:
            error_msg = f"Validation failed with {run.total_error_count} errors"
            logger.error(error_msg)
            run.fail(error_msg)
            update_ingestion_run_db(run, database_url)
            raise ValueError(error_msg)

        # Log warnings if any
        if run.total_warning_count > 0:
            logger.warning(f"Validation completed with {run.total_warning_count} warnings")

        # STAGE 4: TRANSFORM
        run.set_status(IngestionRunStatus.TRANSFORMING)
        update_ingestion_run_db(run, database_url)
        logger.info("Normalizing and cleaning data...")

        normalized_sales = normalize_sales(train_df)
        normalized_stores = normalize_stores(store_df)

        # Map to operational column names
        operational_sales = map_sales_columns(normalized_sales)
        operational_stores = map_store_columns(normalized_stores)

        run.records_normalized = len(operational_sales) + len(operational_stores)
        update_ingestion_run_db(run, database_url)

        # STAGE 5: LOAD
        run.set_status(IngestionRunStatus.LOADING)
        update_ingestion_run_db(run, database_url)
        logger.info("Loading data into database...")

        # Clear staging tables if using staging
        if use_staging:
            clear_staging_tables(database_url)

        # Load data
        load_results = load_operational_tables(
            sales_df=operational_sales,
            stores_df=operational_stores,
            database_url=database_url,
            use_staging=use_staging,
            upsert=upsert,
        )

        run.records_loaded = (
            load_results["sales_loaded"] + load_results["stores_loaded"]
        )
        update_ingestion_run_db(run, database_url)

        logger.info(
            f"Loaded {run.records_loaded} records "
            f"({load_results['sales_loaded']} sales, {load_results['stores_loaded']} stores)"
        )

        # STAGE 6: COMPLETE
        run.complete()
        update_ingestion_run_db(run, database_url)
        logger.info(f"Ingestion run {run.run_id} completed successfully")

        return run

    except Exception as e:
        logger.exception(f"Ingestion run {run.run_id} failed: {e}")
        run.fail(str(e))
        update_ingestion_run_db(run, database_url)
        raise


def _convert_sales_validation(
    validation_result: Any,
    total_records: int,
) -> TableValidationResult:
    """Convert sales validation result to TableValidationResult format.

    Args:
        validation_result: SalesValidationResult from validate_sales_records
        total_records: Total number of records

    Returns:
        TableValidationResult for database persistence
    """
    issues = []
    warnings = []

    for issue in validation_result.issues:
        issues.append(
            ValidationIssue(
                issue_type=_map_sales_issue_type(issue.issue_type),
                severity=ValidationSeverity.ERROR,
                table="sales",
                row_identifier=str(issue.record_index),
                field_name=issue.field_name,
                actual_value=issue.actual_value,
                expected_value=issue.expected,
                message=_format_issue_message(issue),
            )
        )

    for warning in validation_result.warnings:
        warnings.append(
            ValidationIssue(
                issue_type=_map_sales_issue_type(warning.issue_type),
                severity=ValidationSeverity.WARNING,
                table="sales",
                row_identifier=str(warning.record_index),
                field_name=warning.field_name,
                actual_value=warning.actual_value,
                expected_value=warning.expected,
                message=_format_issue_message(warning),
            )
        )

    return TableValidationResult(
        table_name="sales",
        total_records=total_records,
        valid_records=validation_result.valid_records,
        issues=issues,
        warnings=warnings,
    )


def _convert_store_validation(
    validation_result: Any,
    total_records: int,
) -> TableValidationResult:
    """Convert store validation result to TableValidationResult format.

    Args:
        validation_result: StoreValidationResult from validate_store_records
        total_records: Total number of records

    Returns:
        TableValidationResult for database persistence
    """
    issues = []
    warnings = []

    for issue in validation_result.issues:
        issues.append(
            ValidationIssue(
                issue_type=_map_store_issue_type(issue.issue_type),
                severity=ValidationSeverity.ERROR,
                table="stores",
                row_identifier=str(issue.store_id),
                field_name=issue.field_name,
                actual_value=issue.actual_value,
                expected_value=issue.expected,
                message=_format_store_issue_message(issue),
            )
        )

    for warning in validation_result.warnings:
        warnings.append(
            ValidationIssue(
                issue_type=_map_store_issue_type(warning.issue_type),
                severity=ValidationSeverity.WARNING,
                table="stores",
                row_identifier=str(warning.store_id),
                field_name=warning.field_name,
                actual_value=warning.actual_value,
                expected_value=warning.expected,
                message=_format_store_issue_message(warning),
            )
        )

    return TableValidationResult(
        table_name="stores",
        total_records=total_records,
        valid_records=validation_result.valid_records,
        issues=issues,
        warnings=warnings,
    )


def _map_sales_issue_type(issue_type: Any) -> ValidationIssueType:
    """Map sales validation issue type to common ValidationIssueType.

    Args:
        issue_type: SalesValidationIssueType enum

    Returns:
        ValidationIssueType
    """
    from ..quality.validate_sales_records import SalesValidationIssueType

    type_mapping = {
        SalesValidationIssueType.MISSING_REQUIRED_FIELD: ValidationIssueType.STRUCTURAL,
        SalesValidationIssueType.INVALID_DATE_RANGE: ValidationIssueType.STRUCTURAL,
        SalesValidationIssueType.INVALID_DAY_OF_WEEK: ValidationIssueType.STRUCTURAL,
        SalesValidationIssueType.NEGATIVE_SALES: ValidationIssueType.LOGICAL,
        SalesValidationIssueType.NEGATIVE_CUSTOMERS: ValidationIssueType.LOGICAL,
        SalesValidationIssueType.INVALID_OPEN_FLAG: ValidationIssueType.STRUCTURAL,
        SalesValidationIssueType.INVALID_PROMO_FLAG: ValidationIssueType.STRUCTURAL,
        SalesValidationIssueType.INVALID_HOLIDAY_FLAG: ValidationIssueType.STRUCTURAL,
        SalesValidationIssueType.SALES_WHEN_CLOSED: ValidationIssueType.LOGICAL,
        SalesValidationIssueType.CUSTOMERS_WHEN_CLOSED: ValidationIssueType.LOGICAL,
        SalesValidationIssueType.ZERO_SALES_WHEN_OPEN: ValidationIssueType.LOGICAL,
        SalesValidationIssueType.EXTREME_OUTLIER: ValidationIssueType.OUTLIER,
        SalesValidationIssueType.DUPLICATE_RECORD: ValidationIssueType.DUPLICATE,
    }

    return type_mapping.get(issue_type, ValidationIssueType.LOGICAL)


def _map_store_issue_type(issue_type: Any) -> ValidationIssueType:
    """Map store validation issue type to common ValidationIssueType.

    Args:
        issue_type: StoreValidationIssueType enum

    Returns:
        ValidationIssueType
    """
    from ..quality.validate_store_records import StoreValidationIssueType

    type_mapping = {
        StoreValidationIssueType.MISSING_REQUIRED_FIELD: ValidationIssueType.STRUCTURAL,
        StoreValidationIssueType.INVALID_STORE_TYPE: ValidationIssueType.STRUCTURAL,
        StoreValidationIssueType.INVALID_ASSORTMENT: ValidationIssueType.STRUCTURAL,
        StoreValidationIssueType.NEGATIVE_COMPETITION_DISTANCE: ValidationIssueType.LOGICAL,
        StoreValidationIssueType.INVALID_PROMO2_FLAG: ValidationIssueType.STRUCTURAL,
        StoreValidationIssueType.INVALID_COMPETITION_OPEN_MONTH: ValidationIssueType.STRUCTURAL,
        StoreValidationIssueType.INVALID_PROMO2_SINCE_WEEK: ValidationIssueType.STRUCTURAL,
        StoreValidationIssueType.INCOMPLETE_PROMO2_DATES: ValidationIssueType.LOGICAL,
        StoreValidationIssueType.INCOMPLETE_COMPETITION_DATES: ValidationIssueType.LOGICAL,
        StoreValidationIssueType.INCOMPLETE_PROMO_INTERVAL: ValidationIssueType.LOGICAL,
        StoreValidationIssueType.PROMO2_INTERVAL_MISMATCH: ValidationIssueType.LOGICAL,
        StoreValidationIssueType.DUPLICATE_STORE_ID: ValidationIssueType.DUPLICATE,
    }

    return type_mapping.get(issue_type, ValidationIssueType.LOGICAL)


def _format_issue_message(issue: Any) -> str:
    """Format a validation issue message.

    Args:
        issue: Validation issue object

    Returns:
        Formatted message string
    """
    field = f" in {issue.field_name}" if issue.field_name else ""
    return f"{issue.issue_type.value}{field}: {issue.expected}, got {issue.actual_value}"


def _format_store_issue_message(issue: Any) -> str:
    """Format a store validation issue message.

    Args:
        issue: Validation issue object

    Returns:
        Formatted message string
    """
    field = f" in {issue.field_name}" if issue.field_name else ""
    store = f" Store {issue.store_id}" if issue.store_id else ""
    return f"{issue.issue_type.value}{store}{field}: {issue.expected}, got {issue.actual_value}"


def main():
    """Command-line entry point for running ingestion.

    Expects environment variables:
    - DATABASE_URL: PostgreSQL connection URL
    - TRAIN_CSV_PATH: Path to train.csv
    - STORE_CSV_PATH: Path to store.csv
    - USE_STAGING: (optional) Whether to use staging tables (default: true)
    - TRIGGERED_BY: (optional) User or system triggering the run
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get configuration from environment
    database_url = os.getenv("DATABASE_URL")
    train_csv_path = os.getenv("TRAIN_CSV_PATH")
    store_csv_path = os.getenv("STORE_CSV_PATH")
    use_staging = os.getenv("USE_STAGING", "true").lower() == "true"
    triggered_by = os.getenv("TRIGGERED_BY", "cli")

    # Validate required environment variables
    if not all([database_url, train_csv_path, store_csv_path]):
        logger.error(
            "Missing required environment variables: "
            "DATABASE_URL, TRAIN_CSV_PATH, STORE_CSV_PATH"
        )
        return 1

    # Run ingestion
    try:
        run = run_ingestion(
            train_csv_path=train_csv_path,
            store_csv_path=store_csv_path,
            database_url=database_url,
            use_staging=use_staging,
            triggered_by=triggered_by,
        )

        # Generate and log report
        report = create_validation_report(run)
        logger.info("\n" + report.to_markdown())

        return 0 if run.status == IngestionRunStatus.COMPLETED else 1

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
