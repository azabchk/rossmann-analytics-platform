"""Normalization and cleaning for sales records.

This module handles data cleaning and normalization of sales records from
the Rossmann training data, preparing them for loading into operational tables.
"""

from typing import Literal

import pandas as pd


def normalize_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize and clean sales records from train.csv.

    This function performs the following transformations:
    - Ensures all required columns are present and properly typed
    - Handles missing values according to business rules
    - Normalizes date formats
    - Standardizes categorical values
    - Removes invalid records (closed stores with sales)

    Args:
        df: Raw DataFrame from train.csv

    Returns:
        Normalized DataFrame ready for loading

    Raises:
        ValueError: If the DataFrame structure is invalid
    """
    # Create a copy to avoid modifying the original
    df_clean = df.copy()

    # Validate required columns
    required_columns = [
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

    missing_columns = set(required_columns) - set(df_clean.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Normalize Store - ensure integer type
    df_clean["Store"] = pd.to_numeric(df_clean["Store"], errors="coerce").astype("Int64")

    # Normalize DayOfWeek - ensure integer type and valid range (1-7)
    df_clean["DayOfWeek"] = pd.to_numeric(df_clean["DayOfWeek"], errors="coerce").astype("Int64")
    df_clean["DayOfWeek"] = df_clean["DayOfWeek"].clip(lower=1, upper=7)

    # Normalize Date - ensure datetime type
    df_clean["Date"] = pd.to_datetime(df_clean["Date"], errors="coerce")

    # Normalize Sales - ensure numeric, non-negative
    df_clean["Sales"] = pd.to_numeric(df_clean["Sales"], errors="coerce")
    df_clean["Sales"] = df_clean["Sales"].clip(lower=0)

    # Normalize Customers - ensure numeric, non-negative
    df_clean["Customers"] = pd.to_numeric(df_clean["Customers"], errors="coerce")
    df_clean["Customers"] = df_clean["Customers"].clip(lower=0)

    # Normalize Open - ensure integer type (0 or 1)
    df_clean["Open"] = pd.to_numeric(df_clean["Open"], errors="coerce").fillna(1).astype("Int64")
    df_clean["Open"] = df_clean["Open"].clip(lower=0, upper=1)

    # Normalize Promo - ensure integer type (0 or 1)
    df_clean["Promo"] = pd.to_numeric(df_clean["Promo"], errors="coerce").fillna(0).astype("Int64")
    df_clean["Promo"] = df_clean["Promo"].clip(lower=0, upper=1)

    # Normalize StateHoliday - standardize to string values
    # Rossmann uses "0", "a", "b", "c" for different holiday states
    df_clean["StateHoliday"] = df_clean["StateHoliday"].astype(str)
    # Convert numeric "0" to "0" string for consistency
    df_clean["StateHoliday"] = df_clean["StateHoliday"].replace("nan", "0")
    df_clean["StateHoliday"] = df_clean["StateHoliday"].replace("0.0", "0")

    # Normalize SchoolHoliday - ensure integer type (0 or 1)
    df_clean["SchoolHoliday"] = pd.to_numeric(df_clean["SchoolHoliday"], errors="coerce").fillna(0).astype("Int64")
    df_clean["SchoolHoliday"] = df_clean["SchoolHoliday"].clip(lower=0, upper=1)

    # Handle business logic: remove closed stores with non-zero sales
    # These are data errors - closed stores should have 0 sales
    sales_when_closed = (df_clean["Open"] == 0) & (df_clean["Sales"] > 0)
    df_clean = df_clean[~sales_when_closed].copy()

    # Handle business logic: set sales and customers to 0 for closed stores
    df_clean.loc[df_clean["Open"] == 0, "Sales"] = 0
    df_clean.loc[df_clean["Open"] == 0, "Customers"] = 0

    # Handle missing sales values for open stores - use median by store
    open_with_missing_sales = (df_clean["Open"] == 1) & (df_clean["Sales"].isna())
    if open_with_missing_sales.any():
        # Calculate median sales per store
        store_medians = df_clean[df_clean["Sales"].notna()].groupby("Store")["Sales"].median()
        for store_id in df_clean.loc[open_with_missing_sales, "Store"].unique():
            if store_id in store_medians.index:
                df_clean.loc[
                    (df_clean["Store"] == store_id) & df_clean["Sales"].isna(), "Sales"
                ] = store_medians[store_id]

    # Fill remaining NA sales with 0
    df_clean["Sales"] = df_clean["Sales"].fillna(0)

    # Fill missing customers for open stores with median
    open_with_missing_customers = (df_clean["Open"] == 1) & (df_clean["Customers"].isna())
    if open_with_missing_customers.any():
        # Calculate median customers per store
        customer_medians = df_clean[df_clean["Customers"].notna()].groupby("Store")["Customers"].median()
        for store_id in df_clean.loc[open_with_missing_customers, "Store"].unique():
            if store_id in customer_medians.index:
                df_clean.loc[
                    (df_clean["Store"] == store_id) & df_clean["Customers"].isna(), "Customers"
                ] = customer_medians[store_id]

    # Fill remaining NA customers with 0
    df_clean["Customers"] = df_clean["Customers"].fillna(0)

    # Remove records with invalid dates
    df_clean = df_clean[df_clean["Date"].notna()].copy()

    # Sort by store and date for consistent ordering
    df_clean = df_clean.sort_values(["Store", "Date"]).reset_index(drop=True)

    return df_clean


def create_sales_operational_columns() -> list[str]:
    """Get the column names for the operational sales table.

    Returns:
        List of column names in the correct order
    """
    return [
        "store_id",
        "date",
        "day_of_week",
        "sales",
        "customers",
        "open",
        "promo",
        "state_holiday",
        "school_holiday",
    ]


def map_sales_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map DataFrame columns to operational table column names.

    Args:
        df: Normalized DataFrame with source column names

    Returns:
        DataFrame with operational column names
    """
    column_mapping = {
        "Store": "store_id",
        "Date": "date",
        "DayOfWeek": "day_of_week",
        "Sales": "sales",
        "Customers": "customers",
        "Open": "open",
        "Promo": "promo",
        "StateHoliday": "state_holiday",
        "SchoolHoliday": "school_holiday",
    }

    df_mapped = df.rename(columns=column_mapping)
    return df_mapped[create_sales_operational_columns()]


def get_sales_cleaning_summary(original_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> dict:
    """Get a summary of cleaning operations performed.

    Args:
        original_df: DataFrame before cleaning
        cleaned_df: DataFrame after cleaning

    Returns:
        Dictionary containing cleaning summary statistics
    """
    original_count = len(original_df)
    cleaned_count = len(cleaned_df)
    removed_count = original_count - cleaned_count

    # Count NA values before and after
    original_na_sales = original_df["Sales"].isna().sum()
    cleaned_na_sales = cleaned_df["sales"].isna().sum()

    original_na_customers = original_df["Customers"].isna().sum()
    cleaned_na_customers = cleaned_df["customers"].isna().sum()

    original_na_dates = original_df["Date"].isna().sum()
    cleaned_na_dates = cleaned_df["date"].isna().sum()

    # Count records with sales when closed
    sales_when_closed = ((original_df["Open"] == 0) & (original_df["Sales"] > 0)).sum()

    return {
        "original_record_count": original_count,
        "cleaned_record_count": cleaned_count,
        "records_removed": removed_count,
        "removal_rate_pct": (removed_count / original_count * 100) if original_count > 0 else 0,
        "missing_sales_before": original_na_sales,
        "missing_sales_after": cleaned_na_sales,
        "missing_customers_before": original_na_customers,
        "missing_customers_after": cleaned_na_customers,
        "missing_dates_before": original_na_dates,
        "missing_dates_after": cleaned_na_dates,
        "sales_when_closed_fixed": sales_when_closed,
    }
