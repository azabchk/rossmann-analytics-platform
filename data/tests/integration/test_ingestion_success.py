"""Integration coverage for the successful ingestion path."""

import importlib
from pathlib import Path

import pandas as pd

from src.ingest import read_store_csv, read_train_csv
from src.quality import validate_sales_records, validate_store_records
from src.runs.models import IngestionRun, IngestionRunStatus, TableValidationResult
from src.runs.reporting import create_validation_report
from src.transform import map_sales_columns, map_store_columns, normalize_sales, normalize_stores

run_ingestion_module = importlib.import_module("src.runs.run_ingestion")


def test_read_train_csv_reads_expected_columns(tmp_path: Path) -> None:
    csv_file = tmp_path / "train.csv"
    csv_file.write_text(
        "Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday\n"
        "1,5,2015-07-31,5263,555,1,1,0,1\n"
        "2,4,2015-07-30,5602,581,1,1,0,1\n"
    )

    frame = read_train_csv(csv_file)

    assert list(frame.columns) == [
        "Store",
        "DayOfWeek",
        "Date",
        "Sales",
        "Customers",
        "Open",
        "Promo",
        "StateHoliday",
        "SchoolHoliday",
    ]
    assert len(frame) == 2


def test_read_store_csv_reads_expected_columns(tmp_path: Path) -> None:
    csv_file = tmp_path / "store.csv"
    csv_file.write_text(
        "Store,StoreType,Assortment,CompetitionDistance,CompetitionOpenSinceMonth,"
        "CompetitionOpenSinceYear,Promo2,Promo2SinceWeek,Promo2SinceYear,PromoInterval\n"
        "1,c,a,1270,9,2008,0,,,\n"
        '2,a,a,570,11,2007,1,13,2010,"Jan,Apr,Jul,Oct"\n'
    )

    frame = read_store_csv(csv_file)

    assert "StoreType" in frame.columns
    assert "PromoInterval" in frame.columns
    assert len(frame) == 2


def test_valid_input_passes_validation(
    sample_train_df: pd.DataFrame,
    sample_store_df: pd.DataFrame,
) -> None:
    sales_result = validate_sales_records(sample_train_df, strict=False)
    store_result = validate_store_records(sample_store_df, strict=False)

    assert not sales_result.has_errors
    assert not store_result.has_errors
    assert sales_result.valid_records == len(sample_train_df)
    assert store_result.valid_records == len(sample_store_df)


def test_normalization_maps_to_operational_columns(
    sample_train_df: pd.DataFrame,
    sample_store_df: pd.DataFrame,
) -> None:
    normalized_sales = map_sales_columns(normalize_sales(sample_train_df))
    normalized_stores = map_store_columns(normalize_stores(sample_store_df))

    assert list(normalized_sales.columns) == [
        "store_id",
        "sales_date",
        "day_of_week",
        "sales",
        "customers",
        "is_open",
        "promo",
        "state_holiday",
        "school_holiday",
    ]
    assert list(normalized_stores.columns) == [
        "store_id",
        "store_type",
        "assortment",
        "competition_distance",
        "competition_open_since_month",
        "competition_open_since_year",
        "promo2",
        "promo2_since_week",
        "promo2_since_year",
        "promo_interval",
    ]
    assert normalized_stores.loc[0, "store_type"] == "C"
    assert bool(normalized_sales.loc[0, "is_open"]) is True


def test_validation_report_summarizes_clean_run(sample_train_df: pd.DataFrame) -> None:
    run = IngestionRun(train_record_count=len(sample_train_df), store_record_count=2)
    run.start()
    run.add_validation_result(
        TableValidationResult(table_name="sales_records", total_records=3, valid_records=3)
    )
    run.add_validation_result(
        TableValidationResult(table_name="stores", total_records=2, valid_records=2)
    )
    report = create_validation_report(run)

    assert report.total_records == 5
    assert report.total_valid == 5
    assert report.total_errors == 0
    assert "Validation Summary" in report.to_markdown()


def test_run_ingestion_completes_when_validation_and_load_succeed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    train_csv = tmp_path / "train.csv"
    train_csv.write_text(
        "Store,DayOfWeek,Date,Sales,Customers,Open,Promo,StateHoliday,SchoolHoliday\n"
        "1,5,2015-07-31,5263,555,1,1,0,1\n"
        "1,4,2015-07-30,5020,534,1,1,0,1\n"
    )
    store_csv = tmp_path / "store.csv"
    store_csv.write_text(
        "Store,StoreType,Assortment,CompetitionDistance,CompetitionOpenSinceMonth,"
        "CompetitionOpenSinceYear,Promo2,Promo2SinceWeek,Promo2SinceYear,PromoInterval\n"
        "1,c,a,1270,9,2008,0,,,\n"
    )

    saved_states: list[str] = []

    monkeypatch.setattr(run_ingestion_module, "create_ingestion_run_db", lambda run, database_url: run.run_id)
    monkeypatch.setattr(
        run_ingestion_module,
        "update_ingestion_run_db",
        lambda run, database_url: saved_states.append(run.status.value) or True,
    )
    monkeypatch.setattr(
        run_ingestion_module,
        "save_validation_results_db",
        lambda run_id, validation_results, database_url: 0,
    )
    monkeypatch.setattr(run_ingestion_module, "clear_staging_tables", lambda database_url: 2)
    monkeypatch.setattr(
        run_ingestion_module,
        "load_operational_tables",
        lambda sales_df, stores_df, database_url, use_staging, upsert: {
            "sales_loaded": len(sales_df),
            "stores_loaded": len(stores_df),
            "sales_updated": 0,
            "stores_updated": 0,
        },
    )
    monkeypatch.setattr(
        run_ingestion_module,
        "promote_staging_to_base",
        lambda database_url: {"sales_promoted": 2, "stores_promoted": 1},
    )

    run = run_ingestion_module.run_ingestion(
        train_csv_path=str(train_csv),
        store_csv_path=str(store_csv),
        database_url="sqlite:///:memory:",
        use_staging=True,
    )

    assert run.status == IngestionRunStatus.COMPLETED
    assert run.records_loaded == 3
    assert "validation_report" in run.parameters
    assert "load_summary" in run.parameters
    assert "validating" in saved_states
    assert "transforming" in saved_states
    assert "loading" in saved_states
    assert "completed" in saved_states
