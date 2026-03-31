"""Normalization and cleaning for Rossmann sales records."""

from __future__ import annotations

import pandas as pd


REQUIRED_SALES_COLUMNS = [
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


def normalize_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize sales records for controlled operational loading."""

    cleaned = df.copy()
    missing_columns = set(REQUIRED_SALES_COLUMNS) - set(cleaned.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    cleaned["Store"] = pd.to_numeric(cleaned["Store"], errors="coerce").astype("Int64")
    cleaned["Date"] = pd.to_datetime(cleaned["Date"], errors="coerce")
    cleaned = cleaned[cleaned["Store"].notna() & cleaned["Date"].notna()].copy()

    cleaned["DayOfWeek"] = cleaned["Date"].dt.isocalendar().day.astype("Int64")
    cleaned["Sales"] = pd.to_numeric(cleaned["Sales"], errors="coerce").clip(lower=0)
    cleaned["Customers"] = pd.to_numeric(cleaned["Customers"], errors="coerce").clip(lower=0)
    cleaned["Open"] = (
        pd.to_numeric(cleaned["Open"], errors="coerce").fillna(1).clip(lower=0, upper=1).astype("Int64")
    )
    cleaned["Promo"] = (
        pd.to_numeric(cleaned["Promo"], errors="coerce").fillna(0).clip(lower=0, upper=1).astype("Int64")
    )
    cleaned["SchoolHoliday"] = (
        pd.to_numeric(cleaned["SchoolHoliday"], errors="coerce")
        .fillna(0)
        .clip(lower=0, upper=1)
        .astype("Int64")
    )
    cleaned["StateHoliday"] = (
        cleaned["StateHoliday"]
        .astype("string")
        .str.strip()
        .str.lower()
        .fillna("0")
        .replace({"nan": "0", "0.0": "0", "": "0"})
    )

    closed_mask = cleaned["Open"] == 0
    cleaned.loc[closed_mask, "Sales"] = 0
    cleaned.loc[closed_mask, "Customers"] = 0

    sales_medians = cleaned.groupby("Store")["Sales"].transform("median")
    customer_medians = cleaned.groupby("Store")["Customers"].transform("median")
    cleaned["Sales"] = cleaned["Sales"].fillna(sales_medians).fillna(0).round().astype("Int64")
    cleaned["Customers"] = (
        cleaned["Customers"].fillna(customer_medians).fillna(0).round().astype("Int64")
    )

    cleaned = cleaned.drop_duplicates(subset=["Store", "Date"], keep="last")
    cleaned = cleaned.sort_values(["Store", "Date"]).reset_index(drop=True)
    return cleaned


def create_sales_operational_columns() -> list[str]:
    return [
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


def map_sales_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map normalized sales columns to the operational schema."""

    mapped = df.rename(
        columns={
            "Store": "store_id",
            "Date": "sales_date",
            "DayOfWeek": "day_of_week",
            "Sales": "sales",
            "Customers": "customers",
            "Open": "is_open",
            "Promo": "promo",
            "StateHoliday": "state_holiday",
            "SchoolHoliday": "school_holiday",
        }
    ).copy()

    mapped["is_open"] = mapped["is_open"].astype(bool)
    mapped["promo"] = mapped["promo"].astype(bool)
    mapped["school_holiday"] = mapped["school_holiday"].astype(bool)
    return mapped[create_sales_operational_columns()]


def get_sales_cleaning_summary(
    original_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
) -> dict[str, object]:
    """Return a compact summary of the sales cleaning process."""

    sales_column = "sales" if "sales" in cleaned_df.columns else "Sales"
    customers_column = "customers" if "customers" in cleaned_df.columns else "Customers"
    original_count = len(original_df)
    cleaned_count = len(cleaned_df)

    return {
        "original_record_count": original_count,
        "cleaned_record_count": cleaned_count,
        "records_removed": original_count - cleaned_count,
        "sales_missing_after": int(cleaned_df[sales_column].isna().sum()),
        "customers_missing_after": int(cleaned_df[customers_column].isna().sum()),
    }
