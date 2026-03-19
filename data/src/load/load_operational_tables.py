"""Load operational data into database tables.

This module handles loading normalized sales and store data into the
operational database tables (staging and base tables).
"""

import logging
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def get_db_connection(database_url: str) -> Engine:
    """Create a database connection engine.

    Args:
        database_url: Database connection URL

    Returns:
        SQLAlchemy engine instance

    Raises:
        SQLAlchemyError: If connection cannot be established
    """
    try:
        engine = create_engine(database_url)
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except SQLAlchemyError as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def load_operational_tables(
    sales_df: pd.DataFrame,
    stores_df: pd.DataFrame,
    database_url: str,
    use_staging: bool = False,
    upsert: bool = True,
) -> dict[str, int]:
    """Load normalized sales and stores data into operational tables.

    Args:
        sales_df: Normalized sales DataFrame
        stores_df: Normalized stores DataFrame
        database_url: Database connection URL
        use_staging: If True, load into staging tables. If False, load into base tables.
        upsert: If True, perform upsert (update existing, insert new). If False, append only.

    Returns:
        Dictionary with counts of records loaded per table

    Raises:
        ValueError: If DataFrames are empty or invalid
        SQLAlchemyError: If database operations fail
    """
    # Validate input DataFrames
    if sales_df.empty and stores_df.empty:
        raise ValueError("Both sales and stores DataFrames are empty")

    engine = get_db_connection(database_url)

    results = {
        "sales_loaded": 0,
        "stores_loaded": 0,
        "sales_updated": 0,
        "stores_updated": 0,
    }

    try:
        # Determine schema suffix based on staging flag
        schema_suffix = "_staging" if use_staging else ""
        sales_table = f"internal.sales_operational{schema_suffix}"
        stores_table = f"internal.stores_operational{schema_suffix}"

        # Load stores first (foreign key dependency)
        if not stores_df.empty:
            store_results = _load_dataframe(
                df=stores_df,
                table_name=stores_table,
                engine=engine,
                upsert=upsert,
                key_columns=["store_id"],
            )
            results["stores_loaded"] = store_results["inserted"]
            results["stores_updated"] = store_results["updated"]
            logger.info(f"Loaded {results['stores_loaded']} store records")

        # Load sales records
        if not sales_df.empty:
            sales_results = _load_dataframe(
                df=sales_df,
                table_name=sales_table,
                engine=engine,
                upsert=upsert,
                key_columns=["store_id", "date"],
            )
            results["sales_loaded"] = sales_results["inserted"]
            results["sales_updated"] = sales_results["updated"]
            logger.info(f"Loaded {results['sales_loaded']} sales records")

        return results

    except SQLAlchemyError as e:
        logger.error(f"Database error during load: {e}")
        raise
    finally:
        engine.dispose()


def _load_dataframe(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    upsert: bool = True,
    key_columns: list[str] | None = None,
) -> dict[str, int]:
    """Load a DataFrame into a database table.

    Args:
        df: DataFrame to load
        table_name: Full table name (including schema)
        engine: SQLAlchemy engine
        upsert: Whether to perform upsert or insert only
        key_columns: Columns to use as key for upsert

    Returns:
        Dictionary with inserted and updated counts
    """
    inserted = 0
    updated = 0

    try:
        # Ensure DataFrame column types match database expectations
        df_to_load = df.copy()

        # Handle NaN values appropriately
        for col in df_to_load.columns:
            if df_to_load[col].dtype == "object":
                df_to_load[col] = df_to_load[col].where(pd.notna(df_to_load[col]), None)

        if upsert and key_columns:
            # Perform upsert using PostgreSQL ON CONFLICT
            inserted, updated = _upsert_dataframe(
                df=df_to_load,
                table_name=table_name,
                engine=engine,
                key_columns=key_columns,
            )
        else:
            # Simple insert
            rows_inserted = df_to_load.to_sql(
                table_name,
                engine,
                if_exists="append",
                index=False,
                method="multi",
            )
            inserted = rows_inserted

        return {"inserted": inserted, "updated": updated}

    except SQLAlchemyError as e:
        logger.error(f"Error loading DataFrame into {table_name}: {e}")
        raise


def _upsert_dataframe(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    key_columns: list[str],
) -> tuple[int, int]:
    """Perform upsert (update existing, insert new) for a DataFrame.

    Uses PostgreSQL's ON CONFLICT clause for efficient upsert.

    Args:
        df: DataFrame to upsert
        table_name: Full table name (including schema)
        engine: SQLAlchemy engine
        key_columns: Columns that define uniqueness

    Returns:
        Tuple of (inserted_count, updated_count)
    """
    inserted = 0
    updated = 0

    # Split table name into schema and table
    parts = table_name.split(".")
    if len(parts) == 2:
        schema, table = parts
    else:
        schema = "public"
        table = parts[0]

    with engine.connect() as conn:
        for _, row in df.iterrows():
            # Build conflict condition
            conflict_condition = " AND ".join([f'"{col}" = %s' for col in key_columns])
            conflict_values = [row[col] for col in key_columns]

            # Check if row exists
            check_query = text(
                f"""
                SELECT EXISTS(
                    SELECT 1 FROM "{schema}"."{table}"
                    WHERE {conflict_condition}
                )
                """
            )

            exists = conn.execute(check_query, conflict_values).scalar()

            # Get all column values
            columns = [f'"{col}"' for col in df.columns]
            values = [row[col] for col in df.columns]
            placeholders = ", ".join(["%s"] * len(df.columns))

            if exists:
                # Update existing row
                set_clause = ", ".join([
                    f'"{col}" = %s'
                    for col in df.columns
                    if col not in key_columns
                ])
                set_values = [row[col] for col in df.columns if col not in key_columns]

                update_query = text(
                    f"""
                    UPDATE "{schema}"."{table}"
                    SET {set_clause}
                    WHERE {conflict_condition}
                    """
                )

                conn.execute(update_query, set_values + conflict_values)
                updated += 1
            else:
                # Insert new row
                insert_query = text(
                    f"""
                    INSERT INTO "{schema}"."{table}" ({', '.join(columns)})
                    VALUES ({placeholders})
                    """
                )

                conn.execute(insert_query, values)
                inserted += 1

        conn.commit()

    return inserted, updated


def clear_staging_tables(database_url: str, tables: list[str] | None = None) -> int:
    """Clear staging tables before loading fresh data.

    Args:
        database_url: Database connection URL
        tables: List of table names to clear (schema.table). If None, clears all staging tables.

    Returns:
        Number of tables cleared

    Raises:
        SQLAlchemyError: If database operations fail
    """
    engine = get_db_connection(database_url)

    if tables is None:
        tables = [
            "internal.sales_operational_staging",
            "internal.stores_operational_staging",
        ]

    try:
        with engine.connect() as conn:
            for table in tables:
                truncate_query = text(f'TRUNCATE TABLE IF EXISTS "{table}" CASCADE')
                conn.execute(truncate_query)
                conn.commit()
                logger.info(f"Cleared staging table: {table}")

        return len(tables)

    except SQLAlchemyError as e:
        logger.error(f"Error clearing staging tables: {e}")
        raise
    finally:
        engine.dispose()


def promote_staging_to_base(database_url: str) -> dict[str, int]:
    """Promote data from staging tables to base tables.

    This atomically replaces the base tables with staging data.

    Args:
        database_url: Database connection URL

    Returns:
        Dictionary with counts of records promoted per table

    Raises:
        SQLAlchemyError: If database operations fail
    """
    engine = get_db_connection(database_url)

    results = {}

    try:
        with engine.connect() as conn:
            # Get counts before promotion
            for table in ["sales_operational", "stores_operational"]:
                staging_name = f"internal.{table}_staging"
                base_name = f"internal.{table}"

                # Count staging records
                count_query = text(f'SELECT COUNT(*) FROM "{staging_name}"')
                count = conn.execute(count_query).scalar()
                results[f"{table}_promoted"] = count

                # Replace base table with staging
                drop_query = text(f'DROP TABLE IF EXISTS "{base_name}" CASCADE')
                conn.execute(drop_query)

                rename_query = text(
                    f'ALTER TABLE "{staging_name}" RENAME TO "{table}"'
                )
                conn.execute(rename_query)

                conn.commit()
                logger.info(f"Promoted {count} records from {staging_name} to {base_name}")

        return results

    except SQLAlchemyError as e:
        logger.error(f"Error promoting staging to base: {e}")
        raise
    finally:
        engine.dispose()
