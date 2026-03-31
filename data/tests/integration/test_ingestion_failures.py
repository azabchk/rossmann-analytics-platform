"""Integration coverage for ingestion failure scenarios."""

import importlib
from pathlib import Path

import pandas as pd
import pytest

from src.ingest import read_store_csv, read_train_csv
from src.quality import validate_sales_records, validate_store_records

run_ingestion_module = importlib.import_module("src.runs.run_ingestion")

def test_train_csv_missing_required_columns_raises_error(tmp_path: Path) -> None:
    csv_file = tmp_path / "train.csv"
    csv_file.write_text("Store,DayOfWeek,Date,Sales\n1,5,2015-07-31,5263\n")

    with pytest.raises(ValueError, match="Missing expected columns"):
        read_train_csv(csv_file)


def test_train_csv_parser_error_is_reported(tmp_path: Path) -> None:
    csv_file = tmp_path / "train.csv"
    csv_file.write_text(
        "Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday\n"
        '1,5,"2015-07-31,5263,555,1,1,0,1\n'
    )

    with pytest.raises(ValueError, match="Failed to parse train CSV"):
        read_train_csv(csv_file)


def test_store_csv_missing_required_columns_raises_error(tmp_path: Path) -> None:
    csv_file = tmp_path / "store.csv"
    csv_file.write_text("Store,StoreType\n1,c\n")

    with pytest.raises(ValueError, match="Missing expected columns"):
        read_store_csv(csv_file)


def test_sales_validation_detects_business_rule_failures(sample_train_df: pd.DataFrame) -> None:
    sample_train_df.loc[0, "Open"] = 0
    sample_train_df.loc[0, "Sales"] = 100
    sample_train_df.loc[1, "Customers"] = -10

    result = validate_sales_records(sample_train_df, strict=False)

    assert result.has_errors
    assert any(issue.issue_type.value == "sales_when_closed" for issue in result.issues)
    assert any(issue.issue_type.value == "negative_customers" for issue in result.issues)


def test_store_validation_detects_promo2_metadata_problems(sample_store_df: pd.DataFrame) -> None:
    sample_store_df.loc[1, "Promo2SinceWeek"] = None
    sample_store_df.loc[1, "PromoInterval"] = None

    result = validate_store_records(sample_store_df, strict=False)

    assert result.has_errors
    assert any(issue.issue_type.value == "incomplete_promo2_dates" for issue in result.issues)
    assert any(issue.issue_type.value == "incomplete_promo_interval" for issue in result.issues)


def test_sales_validation_flags_duplicates_and_outliers(sample_train_df: pd.DataFrame) -> None:
    duplicate = sample_train_df.iloc[[0]].copy()
    duplicate.loc[:, "Sales"] = 50000
    frame = pd.concat([sample_train_df, duplicate], ignore_index=True)

    result = validate_sales_records(frame, strict=False, check_outliers=True)

    assert result.has_errors
    assert any(issue.issue_type.value == "duplicate_record" for issue in result.issues)
    assert any(warning.issue_type.value == "extreme_outlier" for warning in result.warnings)


def test_run_ingestion_fails_when_validation_detects_errors(tmp_path: Path, monkeypatch) -> None:
    train_csv = tmp_path / "train.csv"
    train_csv.write_text(
        "Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday\n"
        "1,5,2015-07-31,100,25,0,1,0,1\n"
    )
    store_csv = tmp_path / "store.csv"
    store_csv.write_text(
        "Store,StoreType,Assortment,CompetitionDistance,CompetitionOpenSinceMonth,"
        "CompetitionOpenSinceYear,Promo2,Promo2SinceWeek,Promo2SinceYear,PromoInterval\n"
        "1,c,a,1270,9,2008,0,,,\n"
    )

    saved_statuses: list[str] = []

    monkeypatch.setattr(run_ingestion_module, "create_ingestion_run_db", lambda run, database_url: run.run_id)
    monkeypatch.setattr(
        run_ingestion_module,
        "update_ingestion_run_db",
        lambda run, database_url: saved_statuses.append(run.status.value) or True,
    )
    monkeypatch.setattr(
        run_ingestion_module,
        "save_validation_results_db",
        lambda run_id, validation_results, database_url: 0,
    )

    with pytest.raises(ValueError, match="Validation failed"):
        run_ingestion_module.run_ingestion(
            train_csv_path=str(train_csv),
            store_csv_path=str(store_csv),
            database_url="sqlite:///:memory:",
            use_staging=True,
        )

    assert "failed" in saved_statuses


def test_run_ingestion_fails_when_sales_reference_unknown_store(
    tmp_path: Path,
    monkeypatch,
) -> None:
    train_csv = tmp_path / "train.csv"
    train_csv.write_text(
        "Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday\n"
        "9,5,2015-07-31,5263,555,1,1,0,1\n"
    )
    store_csv = tmp_path / "store.csv"
    store_csv.write_text(
        "Store,StoreType,Assortment,CompetitionDistance,CompetitionOpenSinceMonth,"
        "CompetitionOpenSinceYear,Promo2,Promo2SinceWeek,Promo2SinceYear,PromoInterval\n"
        "1,c,a,1270,9,2008,0,,,\n"
    )

    monkeypatch.setattr(run_ingestion_module, "create_ingestion_run_db", lambda run, database_url: run.run_id)
    monkeypatch.setattr(run_ingestion_module, "update_ingestion_run_db", lambda run, database_url: True)
    monkeypatch.setattr(
        run_ingestion_module,
        "save_validation_results_db",
        lambda run_id, validation_results, database_url: 0,
    )

    with pytest.raises(ValueError, match="Validation failed"):
        run_ingestion_module.run_ingestion(
            train_csv_path=str(train_csv),
            store_csv_path=str(store_csv),
            database_url="sqlite:///:memory:",
            use_staging=True,
        )
