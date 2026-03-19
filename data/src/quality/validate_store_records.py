"""Validation rules for store records from store.csv.

This module defines structural and logical validation rules for store
metadata. It identifies data quality issues such as missing values,
invalid categorical values, and inconsistent competition/promotion data.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


class StoreValidationIssueType(Enum):
    """Types of validation issues found in store records."""

    # Missing data
    MISSING_REQUIRED_FIELD = "missing_required_field"

    # Invalid categorical values
    INVALID_STORE_TYPE = "invalid_store_type"
    INVALID_ASSORTMENT = "invalid_assortment"

    # Invalid numeric values
    NEGATIVE_COMPETITION_DISTANCE = "negative_competition_distance"
    INVALID_PROMO2_FLAG = "invalid_promo2_flag"
    INVALID_COMPETITION_OPEN_MONTH = "invalid_competition_open_month"
    INVALID_PROMO2_SINCE_WEEK = "invalid_promo2_since_week"

    # Logical inconsistencies
    INCOMPLETE_PROMO2_DATES = "incomplete_promo2_dates"
    INCOMPLETE_COMPETITION_DATES = "incomplete_competition_dates"
    INCOMPLETE_PROMO_INTERVAL = "incomplete_promo_interval"
    PROMO2_INTERVAL_MISMATCH = "promo2_interval_mismatch"

    # Data quality
    DUPLICATE_STORE_ID = "duplicate_store_id"


@dataclass
class StoreValidationIssue:
    """A validation issue found in store records."""

    issue_type: StoreValidationIssueType
    record_index: int
    store_id: int | None
    field_name: str | None
    actual_value: Any
    expected: str
    severity: str = "error"  # "error", "warning", "info"

    @property
    def message(self) -> str:
        """Human-readable message for this issue."""
        field_str = f" in {self.field_name}" if self.field_name else ""
        store_str = f" Store {self.store_id}" if self.store_id else ""
        return f"{self.issue_type.value}{store_str}{field_str}: {self.expected}, got {self.actual_value}"


@dataclass
class StoreValidationResult:
    """Result of validating store records."""

    total_records: int
    valid_records: int
    issues: list[StoreValidationIssue] = field(default_factory=list)
    warnings: list[StoreValidationIssue] = field(default_factory=list)

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


def validate_store_records(
    df: pd.DataFrame,
    strict: bool = True,
) -> StoreValidationResult:
    """Validate store records from store.csv.

    Args:
        df: DataFrame containing store records
        strict: If True, fail on any error. If False, only warn.

    Returns:
        StoreValidationResult with validation issues
    """
    issues: list[StoreValidationIssue] = []
    warnings: list[StoreValidationIssue] = []

    VALID_STORE_TYPES = {"a", "b", "c", "d"}
    VALID_ASSORTMENTS = {"a", "b", "c"}

    for idx, row in df.iterrows():
        store_id = row.get("Store")

        # Check for missing required fields
        if pd.isna(store_id):
            issues.append(
                StoreValidationIssue(
                    issue_type=StoreValidationIssueType.MISSING_REQUIRED_FIELD,
                    record_index=idx,
                    store_id=None,
                    field_name="Store",
                    actual_value=None,
                    expected="Non-null integer store ID",
                )
            )
            # Skip to next row if store_id is missing
            continue

        # Validate store type
        store_type = row.get("StoreType")
        if pd.notna(store_type) and store_type not in VALID_STORE_TYPES:
            issues.append(
                StoreValidationIssue(
                    issue_type=StoreValidationIssueType.INVALID_STORE_TYPE,
                    record_index=idx,
                    store_id=int(store_id) if pd.notna(store_id) else None,
                    field_name="StoreType",
                    actual_value=store_type,
                    expected=f"One of {VALID_STORE_TYPES}",
                )
            )
            # Skip to next row if store type is invalid
            continue

        # Validate assortment
        assortment = row.get("Assortment")
        if pd.notna(assortment) and assortment not in VALID_ASSORTMENTS:
            issues.append(
                StoreValidationIssue(
                    issue_type=StoreValidationIssueType.INVALID_ASSORTMENT,
                    record_index=idx,
                    store_id=int(store_id) if pd.notna(store_id) else None,
                    field_name="Assortment",
                    actual_value=assortment,
                    expected=f"One of {VALID_ASSORTMENTS}",
            )
        )

        # Check for negative competition distance
        comp_dist = row.get("CompetitionDistance")
        if pd.notna(comp_dist) and comp_dist < 0:
            issues.append(
                StoreValidationIssue(
                    issue_type=StoreValidationIssueType.NEGATIVE_COMPETITION_DISTANCE,
                    record_index=idx,
                    store_id=int(store_id) if pd.notna(store_id) else None,
                    field_name="CompetitionDistance",
                    actual_value=comp_dist,
                    expected="Non-negative float",
            )
        )

        # Validate Promo2 flag
        promo2 = row.get("Promo2")
        if pd.notna(promo2) and promo2 not in (0, 1):
            issues.append(
                StoreValidationIssue(
                    issue_type=StoreValidationIssueType.INVALID_PROMO2_FLAG,
                    record_index=idx,
                    store_id=int(store_id) if pd.notna(store_id) else None,
                    field_name="Promo2",
                    actual_value=promo2,
                    expected="0 or 1",
            )
        )

        # Validate competition open month
        comp_month = row.get("CompetitionOpenSinceMonth")
        if pd.notna(comp_month):
            if (comp_month < 1 or comp_month > 12):
                issues.append(
                    StoreValidationIssue(
                        issue_type=StoreValidationIssueType.INVALID_COMPETITION_OPEN_MONTH,
                        record_index=idx,
                        store_id=int(store_id) if pd.notna(store_id) else None,
                        field_name="CompetitionOpenSinceMonth",
                        actual_value=comp_month,
                        expected="Integer between 1 and 12",
                    )
                )
            else:
                # Check for incomplete competition dates
                comp_year = row.get("CompetitionOpenSinceYear")
                if pd.notna(comp_year):
                    issues.append(
                        StoreValidationIssue(
                            issue_type=StoreValidationIssueType.INCOMPLETE_COMPETITION_DATES,
                            record_index=idx,
                            store_id=int(store_id) if pd.notna(store_id) else None,
                            field_name="CompetitionOpenSinceYear",
                            actual_value=None,
                            expected="Required when CompetitionOpenSinceMonth is set",
                    )
                )

        # Validate Promo2 dates
        if pd.notna(promo2) and promo2 == 1:
            promo2_since_week = row.get("Promo2SinceWeek")
            promo2_since_year = row.get("Promo2SinceYear")

            if pd.isna(promo2_since_week) or pd.isna(promo2_since_year):
                issues.append(
                    StoreValidationIssue(
                        issue_type=StoreValidationIssueType.INCOMPLETE_PROMO2_DATES,
                        record_index=idx,
                        store_id=int(store_id) if pd.notna(store_id) else None,
                        field_name="Promo2SinceWeek/Promo2SinceYear",
                        actual_value=f"{promo2_since_week}/{promo2_since_year}",
                        expected="Both Promo2SinceWeek and Promo2SinceYear required when Promo2=1",
                    )
                )

    # Check for duplicate store IDs
    store_ids = df["Store"].dropna().tolist()
    seen_ids = set()
    for idx, row in df.iterrows():
        store_id = row.get("Store")
        if pd.notna(store_id) and store_id in seen_ids:
            issues.append(
                StoreValidationIssue(
                    issue_type=StoreValidationIssueType.DUPLICATE_STORE_ID,
                    record_index=idx,
                    store_id=int(store_id),
                    field_name="Store",
                    actual_value=store_id,
                    expected="Unique store ID",
                )
            )
        seen_ids.add(store_id)

    return StoreValidationResult(
        total_records=len(df),
        valid_records=len(df) - len(issues),
        issues=issues,
        warnings=warnings,
    )


def get_store_validation_rules() -> dict[str, str]:
    """Get the validation rules applied to store records.

    Returns:
        Dictionary describing validation rules
    """
    return {
        "Store": "Required, must be non-null integer",
        "StoreType": f"Must be one of {VALID_STORE_TYPES}",
        "Assortment": f"Must be one of {VALID_ASSORTMENTS}",
        "CompetitionDistance": "Non-negative float (meters)",
        "CompetitionOpenSinceMonth": "Integer between 1 and 12",
        "CompetitionOpenSinceYear": "Should be provided if CompetitionOpenSinceMonth is set",
        "Promo2": "Must be 0 or 1",
        "Promo2SinceWeek": "Required when Promo2=1",
        "Promo2SinceYear": "Required when Promo2=1",
        "PromoInterval": "Should be provided when Promo2=1",
    }
