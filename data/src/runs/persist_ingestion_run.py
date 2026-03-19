"""Persistence for ingestion run metadata.

This module handles saving and retrieving ingestion run metadata
from the database, including validation results and issues.
"""

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..load import get_db_connection
from .models import (
    IngestionRun,
    IngestionRunStatus,
    TableValidationResult,
    ValidationIssue,
    ValidationIssueType,
    ValidationSeverity,
)
from .reporting import create_validation_report

logger = logging.getLogger(__name__)


def create_ingestion_run_db(
    run: IngestionRun,
    database_url: str,
) -> str:
    """Create a new ingestion run record in the database.

    Args:
        run: The ingestion run to persist
        database_url: Database connection URL

    Returns:
        The run_id of the created record

    Raises:
        SQLAlchemyError: If database operation fails
    """
    engine = get_db_connection(database_url)

    try:
        with engine.connect() as conn:
            query = text("""
                INSERT INTO internal.ingestion_runs (
                    run_id, status, train_csv_path, store_csv_path,
                    train_record_count, store_record_count,
                    triggered_by, parameters,
                    started_at, completed_at, duration_seconds,
                    records_normalized, records_loaded, records_failed,
                    error_message, error_traceback,
                    has_validation_errors, total_error_count, total_warning_count
                ) VALUES (
                    :run_id, :status, :train_csv_path, :store_csv_path,
                    :train_record_count, :store_record_count,
                    :triggered_by, :parameters::jsonb,
                    :started_at, :completed_at, :duration_seconds,
                    :records_normalized, :records_loaded, :records_failed,
                    :error_message, :error_traceback,
                    :has_validation_errors, :total_error_count, :total_warning_count
                )
            """)

            conn.execute(query, {
                "run_id": run.run_id,
                "status": run.status.value,
                "train_csv_path": run.train_csv_path,
                "store_csv_path": run.store_csv_path,
                "train_record_count": run.train_record_count,
                "store_record_count": run.store_record_count,
                "triggered_by": run.triggered_by,
                "parameters": json.dumps(run.parameters),
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "duration_seconds": run.duration_seconds,
                "records_normalized": run.records_normalized,
                "records_loaded": run.records_loaded,
                "records_failed": run.records_failed,
                "error_message": run.error_message,
                "error_traceback": run.error_traceback,
                "has_validation_errors": run.has_validation_errors,
                "total_error_count": run.total_error_count,
                "total_warning_count": run.total_warning_count,
            })
            conn.commit()

            logger.info(f"Created ingestion run {run.run_id}")
            return run.run_id

    except SQLAlchemyError as e:
        logger.error(f"Error creating ingestion run: {e}")
        raise
    finally:
        engine.dispose()


def update_ingestion_run_db(
    run: IngestionRun,
    database_url: str,
) -> bool:
    """Update an existing ingestion run record.

    Args:
        run: The ingestion run with updated values
        database_url: Database connection URL

    Returns:
        True if update successful, False otherwise

    Raises:
        SQLAlchemyError: If database operation fails
    """
    engine = get_db_connection(database_url)

    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE internal.ingestion_runs
                SET status = :status,
                    train_csv_path = :train_csv_path,
                    store_csv_path = :store_csv_path,
                    train_record_count = :train_record_count,
                    store_record_count = :store_record_count,
                    parameters = :parameters::jsonb,
                    completed_at = :completed_at,
                    duration_seconds = :duration_seconds,
                    records_normalized = :records_normalized,
                    records_loaded = :records_loaded,
                    records_failed = :records_failed,
                    error_message = :error_message,
                    error_traceback = :error_traceback,
                    has_validation_errors = :has_validation_errors,
                    total_error_count = :total_error_count,
                    total_warning_count = :total_warning_count
                WHERE run_id = :run_id
            """)

            result = conn.execute(query, {
                "run_id": run.run_id,
                "status": run.status.value,
                "train_csv_path": run.train_csv_path,
                "store_csv_path": run.store_csv_path,
                "train_record_count": run.train_record_count,
                "store_record_count": run.store_record_count,
                "parameters": json.dumps(run.parameters),
                "completed_at": run.completed_at,
                "duration_seconds": run.duration_seconds,
                "records_normalized": run.records_normalized,
                "records_loaded": run.records_loaded,
                "records_failed": run.records_failed,
                "error_message": run.error_message,
                "error_traceback": run.error_traceback,
                "has_validation_errors": run.has_validation_errors,
                "total_error_count": run.total_error_count,
                "total_warning_count": run.total_warning_count,
            })
            conn.commit()

            logger.debug(f"Updated ingestion run {run.run_id}")
            return result.rowcount > 0

    except SQLAlchemyError as e:
        logger.error(f"Error updating ingestion run {run.run_id}: {e}")
        raise
    finally:
        engine.dispose()


def save_validation_results_db(
    run_id: str,
    validation_results: dict[str, TableValidationResult],
    database_url: str,
) -> int:
    """Save validation results for an ingestion run.

    Args:
        run_id: The ingestion run ID
        validation_results: Dictionary of table names to validation results
        database_url: Database connection URL

    Returns:
        Number of validation issues saved

    Raises:
        SQLAlchemyError: If database operation fails
    """
    engine = get_db_connection(database_url)
    total_issues = 0

    try:
        with engine.connect() as conn:
            for table_name, result in validation_results.items():
                # Save aggregated result
                result_query = text("""
                    INSERT INTO internal.ingestion_validation_results (
                        result_id, run_id, table_name,
                        total_records, valid_records,
                        error_count, warning_count,
                        issues, warnings
                    ) VALUES (
                        gen_random_uuid(), :run_id, :table_name,
                        :total_records, :valid_records,
                        :error_count, :warning_count,
                        :issues::jsonb, :warnings::jsonb
                    )
                    ON CONFLICT (run_id, table_name) DO UPDATE SET
                        total_records = EXCLUDED.total_records,
                        valid_records = EXCLUDED.valid_records,
                        error_count = EXCLUDED.error_count,
                        warning_count = EXCLUDED.warning_count,
                        issues = EXCLUDED.issues,
                        warnings = EXCLUDED.warnings
                    RETURNING result_id
                """)

                result_row = conn.execute(result_query, {
                    "run_id": run_id,
                    "table_name": table_name,
                    "total_records": result.total_records,
                    "valid_records": result.valid_records,
                    "error_count": result.error_count,
                    "warning_count": result.warning_count,
                    "issues": json.dumps([issue.to_dict() for issue in result.issues]),
                    "warnings": json.dumps([issue.to_dict() for issue in result.warnings]),
                }).fetchone()

                result_id = result_row[0]

                # Save individual issues
                all_issues = result.issues + result.warnings
                for issue in all_issues:
                    issue_query = text("""
                        INSERT INTO internal.ingestion_validation_issues (
                            issue_id, result_id, run_id,
                            issue_type, severity, table_name,
                            row_identifier, field_name,
                            actual_value, expected_value, message
                        ) VALUES (
                            gen_random_uuid(), :result_id, :run_id,
                            :issue_type, :severity, :table_name,
                            :row_identifier, :field_name,
                            :actual_value, :expected_value, :message
                        )
                    """)

                    conn.execute(issue_query, {
                        "result_id": result_id,
                        "run_id": run_id,
                        "issue_type": issue.issue_type.value,
                        "severity": issue.severity.value,
                        "table_name": table_name,
                        "row_identifier": issue.row_identifier,
                        "field_name": issue.field_name,
                        "actual_value": str(issue.actual_value),
                        "expected_value": issue.expected_value,
                        "message": issue.message,
                    })
                    total_issues += 1

            conn.commit()
            logger.info(f"Saved {total_issues} validation issues for run {run_id}")
            return total_issues

    except SQLAlchemyError as e:
        logger.error(f"Error saving validation results for run {run_id}: {e}")
        raise
    finally:
        engine.dispose()


def get_ingestion_run_db(
    run_id: str,
    database_url: str,
) -> dict[str, Any] | None:
    """Retrieve an ingestion run from the database.

    Args:
        run_id: The ingestion run ID
        database_url: Database connection URL

    Returns:
        Dictionary containing run data, or None if not found
    """
    engine = get_db_connection(database_url)

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT * FROM internal.ingestion_runs
                WHERE run_id = :run_id
            """)

            result = conn.execute(query, {"run_id": run_id}).fetchone()

            if result is None:
                return None

            # Convert to dictionary
            columns = [col[0] for col in result._metadata.keys]
            return dict(zip(columns, result))

    except SQLAlchemyError as e:
        logger.error(f"Error retrieving ingestion run {run_id}: {e}")
        raise
    finally:
        engine.dispose()


def list_ingestion_runs_db(
    database_url: str,
    limit: int = 50,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """List ingestion runs from the database.

    Args:
        database_url: Database connection URL
        limit: Maximum number of runs to return
        status: Filter by status if provided

    Returns:
        List of dictionaries containing run data
    """
    engine = get_db_connection(database_url)

    try:
        with engine.connect() as conn:
            base_query = """
                SELECT * FROM internal.ingestion_runs
            """
            params: dict[str, Any] = {}

            if status:
                base_query += " WHERE status = :status"
                params["status"] = status

            base_query += " ORDER BY started_at DESC LIMIT :limit"
            params["limit"] = limit

            query = text(base_query)
            results = conn.execute(query, params).fetchall()

            # Convert to list of dictionaries
            columns = [col[0] for col in results[0]._metadata.keys] if results else []
            return [dict(zip(columns, result)) for result in results]

    except SQLAlchemyError as e:
        logger.error(f"Error listing ingestion runs: {e}")
        raise
    finally:
        engine.dispose()
