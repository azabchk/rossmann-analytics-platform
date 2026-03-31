"""Validation rules for Rossmann store metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


class StoreValidationIssueType(Enum):
    """Types of validation issues found in store records."""

    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_STORE_TYPE = "invalid_store_type"
    INVALID_ASSORTMENT = "invalid_assortment"
    NEGATIVE_COMPETITION_DISTANCE = "negative_competition_distance"
    INVALID_PROMO2_FLAG = "invalid_promo2_flag"
    INVALID_COMPETITION_OPEN_MONTH = "invalid_competition_open_month"
    INCOMPLETE_COMPETITION_DATES = "incomplete_competition_dates"
    INVALID_PROMO2_SINCE_WEEK = "invalid_promo2_since_week"
    INCOMPLETE_PROMO2_DATES = "incomplete_promo2_dates"
    INVALID_PROMO_INTERVAL = "invalid_promo_interval"
    INCOMPLETE_PROMO_INTERVAL = "incomplete_promo_interval"
    PROMO2_INTERVAL_MISMATCH = "promo2_interval_mismatch"
    DUPLICATE_STORE_ID = "duplicate_store_id"


@dataclass(slots=True)
class StoreValidationIssue:
    """A single validation issue detected in ``store.csv``."""

    issue_type: StoreValidationIssueType
    record_index: int
    store_id: int | None
    field_name: str | None
    actual_value: Any
    expected: str
    severity: str = "error"

    @property
    def message(self) -> str:
        location = f" store={self.store_id}" if self.store_id is not None else ""
        field = f" field={self.field_name}" if self.field_name else ""
        return (
            f"{self.issue_type.value}:{location}{field} "
            f"expected {self.expected}, got {self.actual_value}"
        )


@dataclass(slots=True)
class StoreValidationResult:
    """Validation summary for Rossmann store records."""

    total_records: int
    valid_records: int
    issues: list[StoreValidationIssue] = field(default_factory=list)
    warnings: list[StoreValidationIssue] = field(default_factory=list)

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


def _normalize_text(value: Any, uppercase: bool = False) -> str | None:
    if pd.isna(value):
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized.upper() if uppercase else normalized.lower()


def _normalize_promo_interval(value: Any) -> tuple[str | None, bool]:
    if pd.isna(value):
        return None, True

    normalized = str(value).strip()
    if not normalized or normalized == "0":
        return None, True

    allowed_months = {
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sept",
        "Oct",
        "Nov",
        "Dec",
    }
    parts = [part.strip().title() for part in normalized.split(",") if part.strip()]
    if not parts or any(part not in allowed_months for part in parts):
        return normalized, False
    return ",".join(parts), True


def validate_store_records(
    df: pd.DataFrame,
    strict: bool = True,
) -> StoreValidationResult:
    """Validate Rossmann ``store.csv`` records."""

    del strict  # The caller determines whether warnings are tolerated.

    issues: list[StoreValidationIssue] = []
    warnings: list[StoreValidationIssue] = []
    error_rows: set[int] = set()

    valid_store_types = {"a", "b", "c", "d"}
    valid_assortments = {"a", "b", "c"}

    for idx, row in df.iterrows():
        record_index = int(idx)
        raw_store_id = row.get("Store")
        store_id = int(raw_store_id) if pd.notna(raw_store_id) else None

        def add_issue(
            issue_type: StoreValidationIssueType,
            field_name: str | None,
            actual_value: Any,
            expected: str,
            severity: str = "error",
        ) -> None:
            issue = StoreValidationIssue(
                issue_type=issue_type,
                record_index=record_index,
                store_id=store_id,
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

        if store_id is None:
            add_issue(
                StoreValidationIssueType.MISSING_REQUIRED_FIELD,
                "Store",
                None,
                "non-null positive integer store id",
            )
            continue

        store_type = _normalize_text(row.get("StoreType"))
        if store_type is None:
            add_issue(
                StoreValidationIssueType.MISSING_REQUIRED_FIELD,
                "StoreType",
                None,
                "store type is required",
            )
        elif store_type not in valid_store_types:
            add_issue(
                StoreValidationIssueType.INVALID_STORE_TYPE,
                "StoreType",
                row.get("StoreType"),
                "one of a, b, c, d",
            )

        assortment = _normalize_text(row.get("Assortment"))
        if assortment is None:
            add_issue(
                StoreValidationIssueType.MISSING_REQUIRED_FIELD,
                "Assortment",
                None,
                "assortment is required",
            )
        elif assortment not in valid_assortments:
            add_issue(
                StoreValidationIssueType.INVALID_ASSORTMENT,
                "Assortment",
                row.get("Assortment"),
                "one of a, b, c",
            )

        competition_distance = row.get("CompetitionDistance")
        if pd.notna(competition_distance) and float(competition_distance) < 0:
            add_issue(
                StoreValidationIssueType.NEGATIVE_COMPETITION_DISTANCE,
                "CompetitionDistance",
                competition_distance,
                "non-negative numeric distance",
            )

        competition_month = row.get("CompetitionOpenSinceMonth")
        competition_year = row.get("CompetitionOpenSinceYear")
        if pd.notna(competition_month):
            if int(competition_month) < 1 or int(competition_month) > 12:
                add_issue(
                    StoreValidationIssueType.INVALID_COMPETITION_OPEN_MONTH,
                    "CompetitionOpenSinceMonth",
                    competition_month,
                    "integer between 1 and 12",
                )
            if pd.isna(competition_year):
                add_issue(
                    StoreValidationIssueType.INCOMPLETE_COMPETITION_DATES,
                    "CompetitionOpenSinceYear",
                    competition_year,
                    "year is required when competition month is provided",
                )
        elif pd.notna(competition_year):
            add_issue(
                StoreValidationIssueType.INCOMPLETE_COMPETITION_DATES,
                "CompetitionOpenSinceMonth",
                competition_month,
                "month is required when competition year is provided",
            )

        promo2 = row.get("Promo2")
        if pd.isna(promo2):
            add_issue(
                StoreValidationIssueType.MISSING_REQUIRED_FIELD,
                "Promo2",
                None,
                "0 or 1",
            )
            promo2_enabled = False
        elif int(promo2) not in (0, 1):
            add_issue(
                StoreValidationIssueType.INVALID_PROMO2_FLAG,
                "Promo2",
                promo2,
                "0 or 1",
            )
            promo2_enabled = False
        else:
            promo2_enabled = int(promo2) == 1

        promo2_week = row.get("Promo2SinceWeek")
        promo2_year = row.get("Promo2SinceYear")
        promo_interval, promo_interval_valid = _normalize_promo_interval(row.get("PromoInterval"))

        if pd.notna(promo2_week) and (int(promo2_week) < 1 or int(promo2_week) > 52):
            add_issue(
                StoreValidationIssueType.INVALID_PROMO2_SINCE_WEEK,
                "Promo2SinceWeek",
                promo2_week,
                "integer between 1 and 52",
            )

        if promo2_enabled:
            if pd.isna(promo2_week) or pd.isna(promo2_year):
                add_issue(
                    StoreValidationIssueType.INCOMPLETE_PROMO2_DATES,
                    "Promo2SinceWeek/Promo2SinceYear",
                    f"{promo2_week}/{promo2_year}",
                    "both week and year are required when Promo2 is enabled",
                )
            if promo_interval is None:
                add_issue(
                    StoreValidationIssueType.INCOMPLETE_PROMO_INTERVAL,
                    "PromoInterval",
                    row.get("PromoInterval"),
                    "promo interval is required when Promo2 is enabled",
                )
            elif not promo_interval_valid:
                add_issue(
                    StoreValidationIssueType.INVALID_PROMO_INTERVAL,
                    "PromoInterval",
                    row.get("PromoInterval"),
                    "comma-separated month abbreviations such as Jan,Apr,Jul,Oct",
                )
        else:
            has_promo2_metadata = any(
                pd.notna(value) and str(value).strip() not in {"", "0"}
                for value in (promo2_week, promo2_year, row.get("PromoInterval"))
            )
            if has_promo2_metadata:
                add_issue(
                    StoreValidationIssueType.PROMO2_INTERVAL_MISMATCH,
                    "Promo2 metadata",
                    f"{promo2_week}/{promo2_year}/{row.get('PromoInterval')}",
                    "Promo2 metadata should be empty when Promo2=0",
                    severity="warning",
                )

    duplicates = df[df.duplicated(subset=["Store"], keep="first")]
    for idx, row in duplicates.iterrows():
        record_index = int(idx)
        issues.append(
            StoreValidationIssue(
                issue_type=StoreValidationIssueType.DUPLICATE_STORE_ID,
                record_index=record_index,
                store_id=int(row["Store"]) if pd.notna(row["Store"]) else None,
                field_name="Store",
                actual_value=row.get("Store"),
                expected="unique store identifier",
            )
        )
        error_rows.add(record_index)

    valid_records = max(len(df) - len(error_rows), 0)
    return StoreValidationResult(
        total_records=len(df),
        valid_records=valid_records,
        issues=issues,
        warnings=warnings,
    )
