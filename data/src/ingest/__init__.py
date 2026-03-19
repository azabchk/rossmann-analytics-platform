"""Ingestion module for reading raw Rossmann dataset files."""

from .read_train_csv import read_train_csv
from .read_store_csv import read_store_csv

__all__ = ["read_train_csv", "read_store_csv"]
