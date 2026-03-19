"""Validation rules for sales records from train.csv.

This module defines structural and logical validation rules for the sales
training data. It identifies data quality issues such as missing values,
outliers, and logical inconsistencies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


class SalesValidationIssueType(Enum):
    """Types of validation issues found in sales records."""

    # Missing data
    MISSING_REQUIRED_FIELD = "missing_required_field"

    # Invalid values
    INVALID_DATE_RANGE = "invalid_date_range"
    INVALID_DAY_OF_WEEK = "invalid_day_of_week"
    NEGATIVE_SALES = "negative_sales"
    NEGATIVE_CUSTOMERS = "negative_customers"
    INVALID_OPEN_FLAG = "invalid_open_flag"
    INVALID_PROMO_FLAG = "invalid_promo_flag"
    INVALID_HOLIDAY_FLAG = "invalid_holiday_flag"

    # Logical inconsistencies
    SALES_WHEN_CLOSED = "sales_when_closed"
    CUSTOMERS_WHEN_CLOSED = "customers_when_closed"
    ZERO_SALES_WHEN_OPEN = "zero_sales_when_open"

    # Data quality
    EXTREME_OUTLIER = "extreme_outlier"
    DUPLICATE_RECORD = "duplicate_record"


@dataclass
class SalesValidationIssue:
    """A validation issue found in sales records."""

    issue_type: SalesValidationIssueType
    record_index: int
    field_name: str | None
    actual_value: Any
    expected: str
    severity: str = "error"  # "error", "warning", "info"

    @property
    def message(self) -> str:
        """Human-readable message for this issue."""
        field_str = f" in {self.field_name}" if self.field_name else ""
        return f"{self.issue_type.value}{field_str}: {self.expected}, got {self.actual_value}"


@dataclass
class SalesValidationResult:
    """Result of validating sales records."""

    total_records: int
    valid_records: int
    issues: list[SalesValidationIssue] = field(default_factory=list)
    warnings: list[SalesValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Whether there are any validation errors."""
        return len(self.issues) > 0

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return len(self.issues)

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return len(self.warnings)

    @property
    def error_rate(self) -> float:
        """Percentage of records with errors."""
        if self.total_records == 0:
            return 0.0
        return len(self.issues) / self.total_records * 100


def validate_sales_records(
    df: pd.DataFrame,
    strict: bool = True,
    check_outliers: bool = True,
) -> SalesValidationResult:
    """Validate sales records from train.csv.

    Args:
        df: DataFrame containing sales records
        strict: If True, fail on any error. If False, only warn.
        check_outliers: If True, check for extreme outlier values

    Returns:
        SalesValidationResult with validation issues
    """
    issues: list[SalesValidationIssue] = []
    warnings: list[SalesValidationIssue] = []

    for idx, row in df.iterrows():
        # Check for missing required fields
        if pd.isna(row.get("Store")):
            issues.append(
                SalesValidationIssue(
                    issue_type=SalesValidationIssueType.MISSING_REQUIRED_FIELD,
                    record_index=idx,
                    field_name="Store",
                    actual_value=None,
                    expected="Non-null integer store ID",
                )
            )

        if pd.isna(row.get("Date")):
            issues.append(
                SalesValidationIssue(
                    issue_type=SalesValidationIssueType.MISSING_REQUIRED_FIELD,
                    record_index=idx,
                    field_name="Date",
                    actual_value=None,
                    expected="Non-null date",
                )
            )

        # Validate date range (dataset covers 2013-2015)
        date_val = row.get("Date")
        if pd.notna(date_val):
            min_date = pd.Timestamp("2013-01-01")
            max_date = pd.Timestamp("2015-12-31")
            if date_val < min_date or date_val > max_date:
                issues.append(
                    SalesValidationIssue(
                        issue_type=SalesValidationIssueType.INVALID_DATE_RANGE,
                        record_index=idx,
                        field_name="Date",
                        actual_value=date_val,
                        expected=f"Date between {min_date} and {max_date}",
                    )
                )

        # Validate day of week
        dow = row.get("DayOfWeek")
        if pd.notna(dow) and (dow < 1 or dow > 7):
            issues.append(
                SalesValidationIssue(
                    issue_type=SalesValidationIssueType.INVALID_DAY_OF_WEEK,
                    record_index=idx,
                    field_name="DayOfWeek",
                    actual_value=dow,
                    expected="Integer between 1 and 7",
                )
            )

        # Check for negative values
        sales = row.get("Sales")
        if pd.notna(sales) and sales < 0:
            issues.append(
                SalesValidationIssue(
                    issue_type=SalesValidationIssueType.NEGATIVE_SALES,
                    record_index=idx,
                    field_name="Sales",
                    actual_value=sales,
                    expected="Non-negative integer",
                )
            )

        customers = row.get("Customers")
        if pd.notna(customers) and customers < 0:
            issues.append(
                SalesValidationIssue(
                    issue_type=SalesValidationIssueType.NEGATIVE_CUSTOMERS,
                    record_index=idx,
                    field_name="Customers",
                    actual_value=customers,
                    expected="Non-negative integer",
                )
            )

        # Validate flag fields
        open_flag = row.get("Open")
        if pd.notna(open_flag) and open_flag not in (0, 1):
            issues.append(
                SalesValidationIssue(
                    issue_type=SalesValidationIssueType.INVALID_OPEN_FLAG,
                    record_index=idx,
                    field_name="Open",
                    actual_value=open_flag,
                    expected="0 or 1",
                )
            )

        promo = row.get("Promo")
        if pd.notna(promo) and promo not in (0, 1):
            issues.append(
                SalesValidationIssue(
                    issue_type=SalesValidationIssueType.INVALID_PROMO_FLAG,
                    record_index=idx,
                    field_name="Promo",
                    actual_value=promo,
                    expected="0 or 1",
                )
            )

        school_holiday = row.get("SchoolHoliday")
        if pd.notna(school_holiday) and school_holiday not in (0, 1):
            issues.append(
                SalesValidationIssue(
                    issue_type=SalesValidationIssueType.INVALID_HOLIDAY_FLAG,
                    record_index=idx,
                    field_name="SchoolHoliday",
                    actual_value=school_holiday,
                    expected="0 or 1",
                )
            )

        # Check logical inconsistencies
        if pd.notna(open_flag) and open_flag == 0:
            if pd.notna(sales) and sales > 0:
                issues.append(
                    SalesValidationIssue(
                        issue_type=SalesValidationIssueType.SALES_WHEN_CLOSED,
                        record_index=idx,
                        field_name="Sales",
                        actual_value=sales,
                        expected="0 when store is closed",
                    )
                )
            if pd.notna(customers) and customers > 0:
                issues.append(
                    SalesValidationIssue(
                        issue_type=SalesValidationIssueType.CUSTOMERS_WHEN_CLOSED,
                        record_index=idx,
                        field_name="Customers",
                        actual_value=customers,
                        expected="0 when store is closed",
                    )
                )

        # Check for zero sales when store is open (potential data quality issue)
        if pd.notna(open_flag) and open_flag == 1:
            if pd.notna(sales) and sales == 0:
                warnings.append(
                    SalesValidationIssue(
                        issue_type=SalesValidationIssueType.ZERO_SALES_WHEN_OPEN,
                        record_index=idx,
                        field_name="Sales",
                        actual_value=0,
                        expected="Non-zero when store is open",
                        severity="warning",
                    )
                )

        # Check for extreme outliers
        if check_outliers and pd.notna(sales) and sales > 40000:
            warnings.append(
                SalesValidationIssue(
                    issue_type=SalesValidationIssueType.EXTREME_OUTLIER,
                    record_index=idx,
                    field_name="Sales",
                    actual_value=sales,
                    expected="Sales < 40000 (reasonable daily sales)",
                    severity="warning",
                )
            )

    # Check for duplicate records
    duplicates = df[df.duplicated(subset=["Store", "Date"], keep=False)]
    if not duplicates.empty:
        for idx in duplicates.index:
            issues.append(
                SalesValidationIssue(
                    issue_type=SalesValidationIssueType.DUPLICATE_RECORD,
                    record_index=idx,
                    field_name="Store/Date",
                    actual_value=f"{df.loc[idx, 'Store']}/{df.loc[idx, 'Date']}",
                    expected="Unique combination of Store and Date",
                )
            )

    return SalesValidationResult(
        total_records=len(df),
        valid_records=len(df) - len(issues),
        issues=issues,
        warnings=warnings,
    )


def get_sales_validation_rules() -> dict[str, str]:
    """Get the validation rules applied to sales records.

    Returns:
        Dictionary describing validation rules
    """
    return {
        "Store": "Required, must be non-null integer",
        "Date": "Required, must be valid date between 2013-01-01 and 2015-12-31",
        "DayOfWeek": "Must be integer between 1 and 7",
        "Sales": "Non-negative integer, check for outliers (>40000)",
        "Customers": "Non-negative integer",
        "Open": "Must be 0 or 1, if 0 then Sales and Customers must be 0",
        "Promo": "Must be 0 or 1",
        "SchoolHoliday": "Must be 0 or 1",
        "Store + Date": "Must be unique combination (no duplicates)",
    }
