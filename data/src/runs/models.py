"""Run-state and validation models for the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class IngestionRunStatus(Enum):
    """Status of an ingestion pipeline run."""

    PENDING = "pending"
    RUNNING = "running"
    VALIDATING = "validating"
    TRANSFORMING = "transforming"
    LOADING = "loading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationIssueType(Enum):
    """Generic validation issue categories for cross-table reporting."""

    STRUCTURAL = "structural"
    LOGICAL = "logical"
    REFERENTIAL = "referential"
    DUPLICATE = "duplicate"
    OUTLIER = "outlier"


class ValidationSeverity(Enum):
    """Severity of validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(slots=True)
class ValidationIssue:
    """A single validation issue found during ingestion."""

    issue_type: ValidationIssueType
    severity: ValidationSeverity
    table: str
    row_identifier: str | None
    field_name: str | None
    actual_value: Any
    expected_value: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "table": self.table,
            "row_identifier": self.row_identifier,
            "field_name": self.field_name,
            "actual_value": None if self.actual_value is None else str(self.actual_value),
            "expected_value": self.expected_value,
            "message": self.message,
        }


@dataclass(slots=True)
class TableValidationResult:
    """Validation outcome for a single logical table."""

    table_name: str
    total_records: int
    valid_records: int
    issues: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def add_issue(self, issue: ValidationIssue) -> None:
        if issue.severity == ValidationSeverity.WARNING:
            self.warnings.append(issue)
            return
        self.issues.append(issue)

    def decrement_valid_records(self, count: int = 1) -> None:
        self.valid_records = max(self.valid_records - count, 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_name": self.table_name,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [issue.to_dict() for issue in self.issues],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


@dataclass(slots=True)
class IngestionRun:
    """Metadata and execution state for one ingestion run."""

    run_id: str = field(default_factory=lambda: str(uuid4()))
    status: IngestionRunStatus = IngestionRunStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None

    train_csv_path: str | None = None
    store_csv_path: str | None = None
    train_record_count: int = 0
    store_record_count: int = 0

    validation_results: dict[str, TableValidationResult] = field(default_factory=dict)

    records_normalized: int = 0
    records_loaded: int = 0
    records_failed: int = 0

    error_message: str | None = None
    error_traceback: str | None = None

    triggered_by: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        self.status = IngestionRunStatus.RUNNING
        self.started_at = datetime.now(UTC)

    def complete(self) -> None:
        self.status = IngestionRunStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    def fail(self, error_message: str, traceback: str | None = None) -> None:
        self.status = IngestionRunStatus.FAILED
        self.completed_at = datetime.now(UTC)
        self.error_message = error_message
        self.error_traceback = traceback
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    def cancel(self) -> None:
        self.status = IngestionRunStatus.CANCELLED
        self.completed_at = datetime.now(UTC)
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    def set_status(self, status: IngestionRunStatus) -> None:
        self.status = status

    def add_validation_result(self, result: TableValidationResult) -> None:
        self.validation_results[result.table_name] = result

    @property
    def has_validation_errors(self) -> bool:
        return any(result.has_errors for result in self.validation_results.values())

    @property
    def total_error_count(self) -> int:
        return sum(result.error_count for result in self.validation_results.values())

    @property
    def total_warning_count(self) -> int:
        return sum(result.warning_count for result in self.validation_results.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "train_csv_path": self.train_csv_path,
            "store_csv_path": self.store_csv_path,
            "train_record_count": self.train_record_count,
            "store_record_count": self.store_record_count,
            "records_normalized": self.records_normalized,
            "records_loaded": self.records_loaded,
            "records_failed": self.records_failed,
            "error_message": self.error_message,
            "error_traceback": self.error_traceback,
            "triggered_by": self.triggered_by,
            "parameters": self.parameters,
            "has_validation_errors": self.has_validation_errors,
            "total_error_count": self.total_error_count,
            "total_warning_count": self.total_warning_count,
            "validation_results": {
                table_name: result.to_dict()
                for table_name, result in self.validation_results.items()
            },
        }


def create_ingestion_run(
    train_csv_path: str,
    store_csv_path: str,
    triggered_by: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> IngestionRun:
    """Create a new ingestion run with immutable input references."""

    return IngestionRun(
        train_csv_path=train_csv_path,
        store_csv_path=store_csv_path,
        triggered_by=triggered_by,
        parameters=parameters or {},
    )
