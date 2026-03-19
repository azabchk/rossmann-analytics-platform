"""Models for ingestion pipeline run state and metadata.

This module defines the data structures used to track ingestion runs,
validation results, and overall pipeline state.
"""

from dataclasses import dataclass, field
from datetime import datetime
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
    """Types of validation issues."""

    STRUCTURAL = "structural"  # Missing fields, wrong types
    LOGICAL = "logical"  # Business rule violations
    REFERENTIAL = "referential"  # Foreign key issues
    DUPLICATE = "duplicate"  # Duplicate records
    OUTLIER = "outlier"  # Extreme values


class ValidationSeverity(Enum):
    """Severity of validation issues."""

    ERROR = "error"  # Prevents ingestion from completing
    WARNING = "warning"  # May affect data quality but allows completion
    INFO = "info"  # Informational, does not affect validity


@dataclass
class ValidationIssue:
    """A single validation issue found during ingestion."""

    issue_type: ValidationIssueType
    severity: ValidationSeverity
    table: str  # Which table the issue was found in
    row_identifier: str | None  # How to identify the problematic row
    field_name: str | None  # Which field has the issue
    actual_value: Any  # The problematic value
    expected_value: str  # Description of what was expected
    message: str  # Human-readable description

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "table": self.table,
            "row_identifier": self.row_identifier,
            "field_name": self.field_name,
            "actual_value": str(self.actual_value),
            "expected_value": self.expected_value,
            "message": self.message,
        }


@dataclass
class TableValidationResult:
    """Validation results for a single table."""

    table_name: str
    total_records: int
    valid_records: int
    issues: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Whether there are any error-level issues."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        issue_count = sum(1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR)
        # If issues list is empty but total_records != valid_records, calculate from record counts
        if not self.issues and self.valid_records < self.total_records:
            issue_count = self.total_records - self.valid_records
        return issue_count

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return len(self.warnings)

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue to the appropriate list."""
        if issue.severity == ValidationSeverity.WARNING:
            self.warnings.append(issue)
        else:
            self.issues.append(issue)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "table_name": self.table_name,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [issue.to_dict() for issue in self.issues],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


@dataclass
class IngestionRun:
    """Metadata for a single ingestion pipeline run.

    Tracks the execution of an ingestion job including timing,
    status, validation results, and error information.
    """

    run_id: str = field(default_factory=lambda: str(uuid4()))
    status: IngestionRunStatus = IngestionRunStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None

    # Input information
    train_csv_path: str | None = None
    store_csv_path: str | None = None
    train_record_count: int = 0
    store_record_count: int = 0

    # Validation results
    validation_results: dict[str, TableValidationResult] = field(default_factory=dict)

    # Processing metrics
    records_normalized: int = 0
    records_loaded: int = 0
    records_failed: int = 0

    # Error handling
    error_message: str | None = None
    error_traceback: str | None = None

    # Metadata
    triggered_by: str | None = None  # User or system identifier
    parameters: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        """Mark the run as started."""
        self.status = IngestionRunStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self) -> None:
        """Mark the run as completed successfully."""
        self.status = IngestionRunStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    def fail(self, error_message: str, traceback: str | None = None) -> None:
        """Mark the run as failed."""
        self.status = IngestionRunStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.error_traceback = traceback
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    def cancel(self) -> None:
        """Mark the run as cancelled."""
        self.status = IngestionRunStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()

    def set_status(self, status: IngestionRunStatus) -> None:
        """Update the run status."""
        self.status = status

    def add_validation_result(self, result: TableValidationResult) -> None:
        """Add a validation result for a table."""
        self.validation_results[result.table_name] = result

    @property
    def has_validation_errors(self) -> bool:
        """Whether any table has validation errors."""
        return any(
            result.has_errors for result in self.validation_results.values()
        )

    @property
    def total_error_count(self) -> int:
        """Total count of validation errors across all tables."""
        return sum(result.error_count for result in self.validation_results.values())

    @property
    def total_warning_count(self) -> int:
        """Total count of warnings across all tables."""
        return sum(result.warning_count for result in self.validation_results.values())

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
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
                name: result.to_dict()
                for name, result in self.validation_results.items()
            },
        }


def create_ingestion_run(
    train_csv_path: str,
    store_csv_path: str,
    triggered_by: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> IngestionRun:
    """Create a new ingestion run with initial configuration.

    Args:
        train_csv_path: Path to the training CSV file
        store_csv_path: Path to the store CSV file
        triggered_by: User or system that triggered the run
        parameters: Additional parameters for the run

    Returns:
        New IngestionRun instance
    """
    return IngestionRun(
        train_csv_path=train_csv_path,
        store_csv_path=store_csv_path,
        triggered_by=triggered_by,
        parameters=parameters or {},
    )
