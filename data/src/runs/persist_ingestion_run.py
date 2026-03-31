"""Persistence helpers for ingestion run metadata."""

from __future__ import annotations

import json
import logging
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..load import get_db_connection
from .models import IngestionRun, TableValidationResult

logger = logging.getLogger(__name__)


def _serialize_json(value: object) -> str:
    return json.dumps(value, default=str)


def _run_row(run: IngestionRun) -> dict[str, object]:
    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "train_csv_path": run.train_csv_path,
        "store_csv_path": run.store_csv_path,
        "train_record_count": run.train_record_count,
        "store_record_count": run.store_record_count,
        "records_normalized": run.records_normalized,
        "records_loaded": run.records_loaded,
        "records_failed": run.records_failed,
        "error_message": run.error_message,
        "error_traceback": run.error_traceback,
        "triggered_by": run.triggered_by,
        "parameters": _serialize_json(run.parameters),
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "duration_seconds": run.duration_seconds,
        "has_validation_errors": run.has_validation_errors,
        "total_error_count": run.total_error_count,
        "total_warning_count": run.total_warning_count,
    }


def create_ingestion_run_db(run: IngestionRun, database_url: str) -> str:
    """Insert the initial ingestion run record."""

    engine = get_db_connection(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO internal.ingestion_runs (
                        run_id,
                        status,
                        train_csv_path,
                        store_csv_path,
                        train_record_count,
                        store_record_count,
                        records_normalized,
                        records_loaded,
                        records_failed,
                        error_message,
                        error_traceback,
                        triggered_by,
                        parameters,
                        started_at,
                        completed_at,
                        duration_seconds,
                        has_validation_errors,
                        total_error_count,
                        total_warning_count
                    ) VALUES (
                        :run_id,
                        :status,
                        :train_csv_path,
                        :store_csv_path,
                        :train_record_count,
                        :store_record_count,
                        :records_normalized,
                        :records_loaded,
                        :records_failed,
                        :error_message,
                        :error_traceback,
                        :triggered_by,
                        CAST(:parameters AS jsonb),
                        :started_at,
                        :completed_at,
                        :duration_seconds,
                        :has_validation_errors,
                        :total_error_count,
                        :total_warning_count
                    )
                    """
                ),
                _run_row(run),
            )
        return run.run_id
    except SQLAlchemyError as exc:
        logger.error("Failed creating ingestion run metadata: %s", exc)
        raise
    finally:
        engine.dispose()


def update_ingestion_run_db(run: IngestionRun, database_url: str) -> bool:
    """Update an existing ingestion run record."""

    engine = get_db_connection(database_url)
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text(
                    """
                    UPDATE internal.ingestion_runs
                    SET
                        status = :status,
                        train_csv_path = :train_csv_path,
                        store_csv_path = :store_csv_path,
                        train_record_count = :train_record_count,
                        store_record_count = :store_record_count,
                        records_normalized = :records_normalized,
                        records_loaded = :records_loaded,
                        records_failed = :records_failed,
                        error_message = :error_message,
                        error_traceback = :error_traceback,
                        triggered_by = :triggered_by,
                        parameters = CAST(:parameters AS jsonb),
                        started_at = :started_at,
                        completed_at = :completed_at,
                        duration_seconds = :duration_seconds,
                        has_validation_errors = :has_validation_errors,
                        total_error_count = :total_error_count,
                        total_warning_count = :total_warning_count,
                        updated_at = timezone('utc', now())
                    WHERE run_id = :run_id
                    """
                ),
                _run_row(run),
            )
        return bool(result.rowcount)
    except SQLAlchemyError as exc:
        logger.error("Failed updating ingestion run %s: %s", run.run_id, exc)
        raise
    finally:
        engine.dispose()


def save_validation_results_db(
    run_id: str,
    validation_results: dict[str, TableValidationResult],
    database_url: str,
) -> int:
    """Persist aggregated and detailed validation results for a run."""

    engine = get_db_connection(database_url)
    saved_issue_count = 0
    try:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM internal.ingestion_validation_issues WHERE run_id = :run_id"),
                {"run_id": run_id},
            )
            connection.execute(
                text("DELETE FROM internal.ingestion_validation_results WHERE run_id = :run_id"),
                {"run_id": run_id},
            )

            for table_name, result in validation_results.items():
                result_id = str(uuid4())
                connection.execute(
                    text(
                        """
                        INSERT INTO internal.ingestion_validation_results (
                            result_id,
                            run_id,
                            table_name,
                            total_records,
                            valid_records,
                            error_count,
                            warning_count,
                            issues,
                            warnings
                        ) VALUES (
                            :result_id,
                            :run_id,
                            :table_name,
                            :total_records,
                            :valid_records,
                            :error_count,
                            :warning_count,
                            CAST(:issues AS jsonb),
                            CAST(:warnings AS jsonb)
                        )
                        """
                    ),
                    {
                        "result_id": result_id,
                        "run_id": run_id,
                        "table_name": table_name,
                        "total_records": result.total_records,
                        "valid_records": result.valid_records,
                        "error_count": result.error_count,
                        "warning_count": result.warning_count,
                        "issues": _serialize_json([issue.to_dict() for issue in result.issues]),
                        "warnings": _serialize_json([issue.to_dict() for issue in result.warnings]),
                    },
                )

                for issue in result.issues + result.warnings:
                    connection.execute(
                        text(
                            """
                            INSERT INTO internal.ingestion_validation_issues (
                                issue_id,
                                result_id,
                                run_id,
                                issue_type,
                                severity,
                                table_name,
                                row_identifier,
                                field_name,
                                actual_value,
                                expected_value,
                                message
                            ) VALUES (
                                :issue_id,
                                :result_id,
                                :run_id,
                                :issue_type,
                                :severity,
                                :table_name,
                                :row_identifier,
                                :field_name,
                                :actual_value,
                                :expected_value,
                                :message
                            )
                            """
                        ),
                        {
                            "issue_id": str(uuid4()),
                            "result_id": result_id,
                            "run_id": run_id,
                            "issue_type": issue.issue_type.value,
                            "severity": issue.severity.value,
                            "table_name": table_name,
                            "row_identifier": issue.row_identifier,
                            "field_name": issue.field_name,
                            "actual_value": None if issue.actual_value is None else str(issue.actual_value),
                            "expected_value": issue.expected_value,
                            "message": issue.message,
                        },
                    )
                    saved_issue_count += 1
        return saved_issue_count
    except SQLAlchemyError as exc:
        logger.error("Failed saving validation results for run %s: %s", run_id, exc)
        raise
    finally:
        engine.dispose()
