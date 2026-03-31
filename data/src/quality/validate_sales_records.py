"""Validation rules for Rossmann sales records."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


class SalesValidationIssueType(Enum):
    """Types of validation issues found in sales records."""

    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_DATE_RANGE = "invalid_date_range"
    INVALID_DAY_OF_WEEK = "invalid_day_of_week"
    DAY_OF_WEEK_MISMATCH = "day_of_week_mismatch"
    NEGATIVE_SALES = "negative_sales"
    NEGATIVE_CUSTOMERS = "negative_customers"
    INVALID_OPEN_FLAG = "invalid_open_flag"
    INVALID_PROMO_FLAG = "invalid_promo_flag"
    INVALID_SCHOOL_HOLIDAY_FLAG = "invalid_school_holiday_flag"
    INVALID_STATE_HOLIDAY = "invalid_state_holiday"
    SALES_WHEN_CLOSED = "sales_when_closed"
    CUSTOMERS_WHEN_CLOSED = "customers_when_closed"
    ZERO_SALES_WHEN_OPEN = "zero_sales_when_open"
    EXTREME_OUTLIER = "extreme_outlier"
    DUPLICATE_RECORD = "duplicate_record"


@dataclass(slots=True)
class SalesValidationIssue:
    """A single validation issue detected in ``train.csv``."""

    issue_type: SalesValidationIssueType
    record_index: int
    field_name: str | None
    actual_value: Any
    expected: str
    severity: str = "error"

    @property
    def message(self) -> str:
        field = f" field={self.field_name}" if self.field_name else ""
        return (
            f"{self.issue_type.value}: row={self.record_index}{field} "
            f"expected {self.expected}, got {self.actual_value}"
        )


@dataclass(slots=True)
class SalesValidationResult:
    """Validation summary for Rossmann sales records."""

    total_records: int
    valid_records: int
    issues: list[SalesValidationIssue] = field(default_factory=list)
    warnings: list[SalesValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.issues)

    @property
    def error_count(self) -> int:
        return len(self.issues)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def error_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.error_count / self.total_records) * 100


def _normalize_state_holiday(value: Any) -> str | None:
    if pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"0.0", "0"}:
        return "0"
    return normalized or None


def validate_sales_records(
    df: pd.DataFrame,
    strict: bool = True,
    check_outliers: bool = True,
) -> SalesValidationResult:
    """Validate Rossmann ``train.csv`` records."""

    del strict  # The caller decides whether warnings and errors are fatal.

    issues: list[SalesValidationIssue] = []
    warnings: list[SalesValidationIssue] = []
    error_rows: set[int] = set()

    min_date = pd.Timestamp("2013-01-01")
    max_date = pd.Timestamp("2015-12-31")
    valid_state_holidays = {"0", "a", "b", "c"}

    def add_issue(
        record_index: int,
        issue_type: SalesValidationIssueType,
        field_name: str | None,
        actual_value: Any,
        expected: str,
        severity: str = "error",
    ) -> None:
        issue = SalesValidationIssue(
            issue_type=issue_type,
            record_index=record_index,
            field_name=field_name,
            actual_value=actual_value,
            expected=expected,
            severity=severity,
        )
        if severity == "warning":
            warnings.append(issue)
            return
        issues.append(issue)
        error_rows.add(record_index)

    for idx, row in df.iterrows():
        row_index = int(idx)

        store_value = row.get("Store")
        if pd.isna(store_value):
            add_issue(
                row_index,
                SalesValidationIssueType.MISSING_REQUIRED_FIELD,
                "Store",
                None,
                "non-null positive integer store id",
            )

        date_value = row.get("Date")
        if pd.isna(date_value):
            add_issue(
                row_index,
                SalesValidationIssueType.MISSING_REQUIRED_FIELD,
                "Date",
                None,
                "parseable non-null date",
            )
        elif date_value < min_date or date_value > max_date:
            add_issue(
                row_index,
                SalesValidationIssueType.INVALID_DATE_RANGE,
                "Date",
                date_value,
                f"date between {min_date.date()} and {max_date.date()}",
            )

        day_of_week = row.get("DayOfWeek")
        if pd.isna(day_of_week):
            add_issue(
                row_index,
                SalesValidationIssueType.MISSING_REQUIRED_FIELD,
                "DayOfWeek",
                None,
                "integer between 1 and 7",
            )
        elif int(day_of_week) not in range(1, 8):
            add_issue(
                row_index,
                SalesValidationIssueType.INVALID_DAY_OF_WEEK,
                "DayOfWeek",
                day_of_week,
                "integer between 1 and 7",
            )
        elif pd.notna(date_value) and int(day_of_week) != date_value.isoweekday():
            add_issue(
                row_index,
                SalesValidationIssueType.DAY_OF_WEEK_MISMATCH,
                "DayOfWeek",
                day_of_week,
                f"weekday matching {date_value.date()}",
            )

        sales = row.get("Sales")
        if pd.isna(sales):
            add_issue(
                row_index,
                SalesValidationIssueType.MISSING_REQUIRED_FIELD,
                "Sales",
                None,
                "non-null sales value",
            )
        elif float(sales) < 0:
            add_issue(
                row_index,
                SalesValidationIssueType.NEGATIVE_SALES,
                "Sales",
                sales,
                "non-negative sales value",
            )

        customers = row.get("Customers")
        if pd.notna(customers) and float(customers) < 0:
            add_issue(
                row_index,
                SalesValidationIssueType.NEGATIVE_CUSTOMERS,
                "Customers",
                customers,
                "non-negative customer count",
            )

        open_flag = row.get("Open")
        if pd.isna(open_flag):
            add_issue(
                row_index,
                SalesValidationIssueType.MISSING_REQUIRED_FIELD,
                "Open",
                None,
                "0 or 1",
            )
        elif int(open_flag) not in (0, 1):
            add_issue(
                row_index,
                SalesValidationIssueType.INVALID_OPEN_FLAG,
                "Open",
                open_flag,
                "0 or 1",
            )

        promo_flag = row.get("Promo")
        if pd.isna(promo_flag):
            add_issue(
                row_index,
                SalesValidationIssueType.MISSING_REQUIRED_FIELD,
                "Promo",
                None,
                "0 or 1",
            )
        elif int(promo_flag) not in (0, 1):
            add_issue(
                row_index,
                SalesValidationIssueType.INVALID_PROMO_FLAG,
                "Promo",
                promo_flag,
                "0 or 1",
            )

        school_holiday = row.get("SchoolHoliday")
        if pd.isna(school_holiday):
            add_issue(
                row_index,
                SalesValidationIssueType.MISSING_REQUIRED_FIELD,
                "SchoolHoliday",
                None,
                "0 or 1",
            )
        elif int(school_holiday) not in (0, 1):
            add_issue(
                row_index,
                SalesValidationIssueType.INVALID_SCHOOL_HOLIDAY_FLAG,
                "SchoolHoliday",
                school_holiday,
                "0 or 1",
            )

        state_holiday = _normalize_state_holiday(row.get("StateHoliday"))
        if state_holiday not in valid_state_holidays:
            add_issue(
                row_index,
                SalesValidationIssueType.INVALID_STATE_HOLIDAY,
                "StateHoliday",
                row.get("StateHoliday"),
                "one of 0, a, b, c",
            )

        if pd.notna(open_flag) and int(open_flag) == 0:
            if pd.notna(sales) and float(sales) > 0:
                add_issue(
                    row_index,
                    SalesValidationIssueType.SALES_WHEN_CLOSED,
                    "Sales",
                    sales,
                    "0 when store is closed",
                )
            if pd.notna(customers) and float(customers) > 0:
                add_issue(
                    row_index,
                    SalesValidationIssueType.CUSTOMERS_WHEN_CLOSED,
                    "Customers",
                    customers,
                    "0 when store is closed",
                )
        elif pd.notna(open_flag) and int(open_flag) == 1 and pd.notna(sales) and float(sales) == 0:
            add_issue(
                row_index,
                SalesValidationIssueType.ZERO_SALES_WHEN_OPEN,
                "Sales",
                sales,
                "non-zero sales when store is open",
                severity="warning",
            )

        if check_outliers and pd.notna(sales) and float(sales) > 40000:
            add_issue(
                row_index,
                SalesValidationIssueType.EXTREME_OUTLIER,
                "Sales",
                sales,
                "daily sales below the configured outlier threshold",
                severity="warning",
            )

    duplicates = df[df.duplicated(subset=["Store", "Date"], keep="first")]
    for idx, row in duplicates.iterrows():
        row_index = int(idx)
        add_issue(
            row_index,
            SalesValidationIssueType.DUPLICATE_RECORD,
            "Store/Date",
            f"{row.get('Store')}/{row.get('Date')}",
            "unique store/date combination",
        )

    valid_records = max(len(df) - len(error_rows), 0)
    return SalesValidationResult(
        total_records=len(df),
        valid_records=valid_records,
        issues=issues,
        warnings=warnings,
    )
