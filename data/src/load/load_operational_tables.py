"""Load normalized operational data into restricted database tables."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

STAGING_TABLES = {
    "stores": "internal.stores_staging",
    "sales": "internal.sales_records_staging",
}

BASE_TABLES = {
    "stores": "internal.stores",
    "sales": "internal.sales_records",
}

STORE_COLUMNS = [
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

SALES_COLUMNS = [
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


def _split_table_name(table_name: str) -> tuple[str, str]:
    schema, relation = table_name.split(".", maxsplit=1)
    return schema, relation


def get_db_connection(database_url: str) -> Engine:
    """Create and test a synchronous SQLAlchemy engine."""

    engine = create_engine(database_url, future=True, pool_pre_ping=True)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return engine


def _sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    sanitized = df.copy()
    return sanitized.where(pd.notna(sanitized), None)


def _iter_records(df: pd.DataFrame, batch_size: int = 1000) -> Iterator[list[dict[str, object]]]:
    records = _sanitize_dataframe(df).to_dict(orient="records")
    for start in range(0, len(records), batch_size):
        yield records[start : start + batch_size]


def _append_dataframe(
    connection: Connection,
    df: pd.DataFrame,
    table_name: str,
) -> int:
    if df.empty:
        return 0

    schema, relation = _split_table_name(table_name)
    sanitized = _sanitize_dataframe(df)
    written = sanitized.to_sql(
        relation,
        connection,
        schema=schema,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )
    return int(written or len(sanitized))


def _reflect_table(connection: Connection, table_name: str) -> Table:
    schema, relation = _split_table_name(table_name)
    metadata = MetaData()
    return Table(relation, metadata, schema=schema, autoload_with=connection)


def _upsert_dataframe(
    connection: Connection,
    df: pd.DataFrame,
    table_name: str,
    conflict_columns: Iterable[str],
) -> dict[str, int]:
    if df.empty:
        return {"loaded": 0, "updated": 0}

    table = _reflect_table(connection, table_name)
    written = 0
    for batch in _iter_records(df):
        statement = pg_insert(table).values(batch)
        conflict_column_set = set(conflict_columns)
        update_columns = {
            column.name: getattr(statement.excluded, column.name)
            for column in table.columns
            if column.name not in conflict_column_set
            and column.name not in {"sales_record_id", "created_at"}
        }
        connection.execute(
            statement.on_conflict_do_update(
                index_elements=list(conflict_columns),
                set_=update_columns,
            )
        )
        written += len(batch)
    return {"loaded": written, "updated": 0}


def load_operational_tables(
    sales_df: pd.DataFrame,
    stores_df: pd.DataFrame,
    database_url: str,
    use_staging: bool = True,
    upsert: bool = True,
) -> dict[str, int]:
    """Load normalized sales and store data into base or staging tables."""

    if sales_df.empty and stores_df.empty:
        raise ValueError("Both sales_df and stores_df are empty")

    engine = get_db_connection(database_url)
    tables = STAGING_TABLES if use_staging else BASE_TABLES

    try:
        with engine.begin() as connection:
            if use_staging or not upsert:
                stores_loaded = _append_dataframe(connection, stores_df[STORE_COLUMNS], tables["stores"])
                sales_loaded = _append_dataframe(connection, sales_df[SALES_COLUMNS], tables["sales"])
                return {
                    "stores_loaded": stores_loaded,
                    "stores_updated": 0,
                    "sales_loaded": sales_loaded,
                    "sales_updated": 0,
                }

            store_results = _upsert_dataframe(
                connection=connection,
                df=stores_df[STORE_COLUMNS],
                table_name=tables["stores"],
                conflict_columns=["store_id"],
            )
            sales_results = _upsert_dataframe(
                connection=connection,
                df=sales_df[SALES_COLUMNS],
                table_name=tables["sales"],
                conflict_columns=["store_id", "sales_date"],
            )
            return {
                "stores_loaded": store_results["loaded"],
                "stores_updated": store_results["updated"],
                "sales_loaded": sales_results["loaded"],
                "sales_updated": sales_results["updated"],
            }
    except SQLAlchemyError as exc:
        logger.error("Failed loading operational tables: %s", exc)
        raise
    finally:
        engine.dispose()


def clear_staging_tables(database_url: str, tables: list[str] | None = None) -> int:
    """Clear configured staging tables before a repeatable ingestion run."""

    engine = get_db_connection(database_url)
    target_tables = tables or [STAGING_TABLES["sales"], STAGING_TABLES["stores"]]

    try:
        with engine.begin() as connection:
            for table_name in target_tables:
                schema, relation = _split_table_name(table_name)
                connection.execute(
                    text(f'TRUNCATE TABLE "{schema}"."{relation}" RESTART IDENTITY CASCADE')
                )
        return len(target_tables)
    finally:
        engine.dispose()


def promote_staging_to_base(database_url: str) -> dict[str, int]:
    """Promote staging contents into stable operational base tables."""

    engine = get_db_connection(database_url)
    try:
        with engine.begin() as connection:
            store_count = connection.execute(
                text("SELECT COUNT(*) FROM internal.stores_staging")
            ).scalar_one()
            sales_count = connection.execute(
                text("SELECT COUNT(*) FROM internal.sales_records_staging")
            ).scalar_one()

            connection.execute(
                text(
                    """
                    INSERT INTO internal.stores (
                        store_id,
                        store_type,
                        assortment,
                        competition_distance,
                        competition_open_since_month,
                        competition_open_since_year,
                        promo2,
                        promo2_since_week,
                        promo2_since_year,
                        promo_interval
                    )
                    SELECT
                        store_id,
                        store_type,
                        assortment,
                        competition_distance,
                        competition_open_since_month,
                        competition_open_since_year,
                        promo2,
                        promo2_since_week,
                        promo2_since_year,
                        promo_interval
                    FROM internal.stores_staging
                    ON CONFLICT (store_id) DO UPDATE
                    SET
                        store_type = EXCLUDED.store_type,
                        assortment = EXCLUDED.assortment,
                        competition_distance = EXCLUDED.competition_distance,
                        competition_open_since_month = EXCLUDED.competition_open_since_month,
                        competition_open_since_year = EXCLUDED.competition_open_since_year,
                        promo2 = EXCLUDED.promo2,
                        promo2_since_week = EXCLUDED.promo2_since_week,
                        promo2_since_year = EXCLUDED.promo2_since_year,
                        promo_interval = EXCLUDED.promo_interval,
                        updated_at = timezone('utc', now())
                    """
                )
            )

            connection.execute(text("DELETE FROM internal.sales_records"))
            connection.execute(
                text(
                    """
                    INSERT INTO internal.sales_records (
                        store_id,
                        sales_date,
                        day_of_week,
                        sales,
                        customers,
                        is_open,
                        promo,
                        state_holiday,
                        school_holiday
                    )
                    SELECT
                        store_id,
                        sales_date,
                        day_of_week,
                        sales,
                        customers,
                        is_open,
                        promo,
                        state_holiday,
                        school_holiday
                    FROM internal.sales_records_staging
                    """
                )
            )

        return {
            "stores_promoted": int(store_count),
            "sales_promoted": int(sales_count),
        }
    finally:
        engine.dispose()
