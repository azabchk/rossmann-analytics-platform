"""Validation reporting for ingestion pipeline runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import (
    IngestionRun,
    IngestionRunStatus,
    TableValidationResult,
    ValidationIssue,
)


@dataclass(slots=True)
class ValidationReport:
    """Formatted validation report for one ingestion run."""

    run_id: str
    status: str
    timestamp: str
    duration_seconds: float | None
    train_csv_path: str
    store_csv_path: str
    train_record_count: int
    store_record_count: int
    total_records: int
    total_valid: int
    total_errors: int
    total_warnings: int
    success_rate: float
    table_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    error_breakdown: dict[str, int] = field(default_factory=dict)
    warning_breakdown: dict[str, int] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert the report to Markdown for operator review."""

        lines = [
            "# Ingestion Validation Report",
            "",
            f"**Run ID**: {self.run_id}",
            f"**Status**: `{self.status}`",
            f"**Timestamp**: {self.timestamp}",
            "",
            (
                f"**Duration**: {self.duration_seconds:.2f} seconds"
                if self.duration_seconds is not None
                else "**Duration**: N/A"
            ),
            "",
            "## Input Summary",
            "",
            f"- **Train CSV**: {self.train_csv_path}",
            f"- **Store CSV**: {self.store_csv_path}",
            f"- **Train Records**: {self.train_record_count:,}",
            f"- **Store Records**: {self.store_record_count:,}",
            "",
            "## Validation Summary",
            "",
            f"- **Total Records**: {self.total_records:,}",
            f"- **Valid Records**: {self.total_valid:,}",
            f"- **Errors**: {self.total_errors:,}",
            f"- **Warnings**: {self.total_warnings:,}",
            f"- **Success Rate**: {self.success_rate:.2f}%",
            "",
        ]

        if self.error_breakdown:
            lines.extend(["### Errors by Type", ""])
            for issue_type, count in sorted(self.error_breakdown.items()):
                lines.append(f"- **{issue_type}**: {count:,}")
            lines.append("")

        if self.warning_breakdown:
            lines.extend(["### Warnings by Type", ""])
            for issue_type, count in sorted(self.warning_breakdown.items()):
                lines.append(f"- **{issue_type}**: {count:,}")
            lines.append("")

        if self.table_results:
            lines.extend(["## Detailed Results by Table", ""])
            for table_name, result in self.table_results.items():
                lines.extend(
                    [
                        f"### {table_name}",
                        "",
                        f"- **Total Records**: {result['total_records']:,}",
                        f"- **Valid Records**: {result['valid_records']:,}",
                        f"- **Errors**: {result['error_count']:,}",
                        f"- **Warnings**: {result['warning_count']:,}",
                    ]
                )

                if result.get("issues"):
                    lines.extend(["", "#### Errors", ""])
                    for issue in result["issues"][:10]:
                        lines.append(f"- {issue['message']}")
                    if len(result["issues"]) > 10:
                        lines.append(f"- ... and {len(result['issues']) - 10} more errors")
                    lines.append("")

                if result.get("warnings"):
                    lines.extend(["", "#### Warnings", ""])
                    for issue in result["warnings"][:10]:
                        lines.append(f"- {issue['message']}")
                    if len(result["warnings"]) > 10:
                        lines.append(f"- ... and {len(result['warnings']) - 10} more warnings")
                    lines.append("")

        lines.extend(["## Overall Status", ""])
        if self.status == IngestionRunStatus.COMPLETED.value:
            lines.append("The ingestion run completed successfully.")
        elif self.status == IngestionRunStatus.FAILED.value:
            lines.append("The ingestion run failed and requires operator attention.")
        else:
            lines.append(f"The ingestion run is currently in status `{self.status}`.")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "train_csv_path": self.train_csv_path,
            "store_csv_path": self.store_csv_path,
            "train_record_count": self.train_record_count,
            "store_record_count": self.store_record_count,
            "total_records": self.total_records,
            "total_valid": self.total_valid,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "success_rate": self.success_rate,
            "table_results": self.table_results,
            "error_breakdown": self.error_breakdown,
            "warning_breakdown": self.warning_breakdown,
        }


def create_validation_report(run: IngestionRun) -> ValidationReport:
    """Create a validation report from an ingestion run."""

    total_records = (
        sum(result.total_records for result in run.validation_results.values())
        or run.train_record_count + run.store_record_count
    )
    total_valid = sum(result.valid_records for result in run.validation_results.values())
    total_errors = sum(result.error_count for result in run.validation_results.values())
    total_warnings = sum(result.warning_count for result in run.validation_results.values())
    success_rate = (total_valid / total_records * 100) if total_records > 0 else 0.0

    error_breakdown: dict[str, int] = {}
    warning_breakdown: dict[str, int] = {}
    table_results: dict[str, dict[str, Any]] = {}

    for table_name, result in run.validation_results.items():
        table_results[table_name] = result.to_dict()
        for issue in result.issues:
            issue_type = issue.issue_type.value
            error_breakdown[issue_type] = error_breakdown.get(issue_type, 0) + 1
        for issue in result.warnings:
            issue_type = issue.issue_type.value
            warning_breakdown[issue_type] = warning_breakdown.get(issue_type, 0) + 1

    timestamp_source = run.completed_at or run.started_at or datetime.utcnow()
    return ValidationReport(
        run_id=run.run_id,
        status=run.status.value,
        timestamp=timestamp_source.isoformat(),
        duration_seconds=run.duration_seconds,
        train_csv_path=run.train_csv_path or "",
        store_csv_path=run.store_csv_path or "",
        train_record_count=run.train_record_count,
        store_record_count=run.store_record_count,
        total_records=total_records,
        total_valid=total_valid,
        total_errors=total_errors,
        total_warnings=total_warnings,
        success_rate=success_rate,
        table_results=table_results,
        error_breakdown=error_breakdown,
        warning_breakdown=warning_breakdown,
    )


def format_validation_issue(issue: ValidationIssue, include_details: bool = True) -> str:
    """Format a validation issue as operator-facing text."""

    base = f"[{issue.severity.value.upper()}] {issue.message}"

    if include_details:
        details = []
        if issue.table:
            details.append(f"table: {issue.table}")
        if issue.row_identifier:
            details.append(f"row: {issue.row_identifier}")
        if issue.field_name:
            details.append(f"field: {issue.field_name}")
        if details:
            base += f" ({', '.join(details)})"
    return base


def summarize_validation_results(results: list[TableValidationResult]) -> dict[str, Any]:
    """Summarize multiple table validation results."""

    total_records = sum(result.total_records for result in results)
    total_valid = sum(result.valid_records for result in results)
    total_errors = sum(result.error_count for result in results)
    total_warnings = sum(result.warning_count for result in results)

    error_types: dict[str, int] = {}
    warning_types: dict[str, int] = {}
    for result in results:
        for issue in result.issues:
            issue_type = issue.issue_type.value
            error_types[issue_type] = error_types.get(issue_type, 0) + 1
        for warning in result.warnings:
            issue_type = warning.issue_type.value
            warning_types[issue_type] = warning_types.get(issue_type, 0) + 1

    return {
        "total_records": total_records,
        "total_valid": total_valid,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "success_rate": (total_valid / total_records * 100) if total_records > 0 else 0.0,
        "error_types": error_types,
        "warning_types": warning_types,
    }
