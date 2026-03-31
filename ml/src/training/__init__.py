"""Model training package.

Keep this package lightweight so importing one trainer does not eagerly import
optional model backends such as Prophet or XGBoost.
"""

__all__ = [
    "train_baseline",
    "train_prophet",
    "train_xgboost",
]
