"""Quality module for validating sales and store records."""

from .validate_sales_records import validate_sales_records
from .validate_store_records import validate_store_records

__all__ = ["validate_sales_records", "validate_store_records"]
