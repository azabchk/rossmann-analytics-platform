"""Model metadata publishing and training run tracking.

This module provides functions for publishing model metadata and tracking
training runs in the database.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4


class ModelMetadata:
    """Container for model metadata."""

    def __init__(
        self,
        model_name: str,
        model_type: str,
        version: str,
        parameters: Dict,
        artifact_path: Optional[str] = None,
        artifact_hash: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """Initialize model metadata.

        Args:
            model_name: Unique name for the model
            model_type: Type of model (baseline, prophet, xgboost)
            version: Version string
            parameters: Model hyperparameters
            artifact_path: Path to serialized model artifact
            artifact_hash: Hash of the artifact
            metadata: Additional metadata
        """
        self.model_id = str(uuid4())
        self.model_name = model_name
        self.model_type = model_type
        self.version = version
        self.parameters = parameters
        self.artifact_path = artifact_path
        self.artifact_hash = artifact_hash
        self.metadata = metadata or {}
        self.published_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "model_id": self.model_id,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "version": self.version,
            "parameters": self.parameters,
            "artifact_path": self.artifact_path,
            "artifact_hash": self.artifact_hash,
            "metadata": self.metadata,
            "published_at": self.published_at.isoformat(),
        }


class TrainingRunMetadata:
    """Container for training run metadata."""

    def __init__(
        self,
        run_name: str,
        model_type: str,
        dataset_version: str,
        feature_version: Optional[str] = None,
        parameters: Optional[Dict] = None,
    ):
        """Initialize training run metadata.

        Args:
            run_name: Name of the training run
            model_type: Type of model being trained
            dataset_version: Version of the dataset used
            feature_version: Version of the features used
            parameters: Training parameters
        """
        self.run_id = str(uuid4())
        self.run_name = run_name
        self.model_type = model_type
        self.status = "pending"
        self.dataset_version = dataset_version
        self.feature_version = feature_version
        self.parameters = parameters or {}
        self.started_at = datetime.utcnow()
        self.completed_at = None
        self.error_message = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "run_name": self.run_name,
            "model_type": self.model_type,
            "status": self.status,
            "dataset_version": self.dataset_version,
            "feature_version": self.feature_version,
            "parameters": self.parameters,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


def register_training_run(
    run_name: str,
    model_type: str,
    dataset_version: str,
    feature_version: Optional[str] = None,
    parameters: Optional[Dict] = None,
) -> TrainingRunMetadata:
    """Register a new training run.

    Args:
        run_name: Name of the training run
        model_type: Type of model being trained
        dataset_version: Version of the dataset used
        feature_version: Version of the features used
        parameters: Training parameters

    Returns:
        TrainingRunMetadata object
    """
    return TrainingRunMetadata(
        run_name=run_name,
        model_type=model_type,
        dataset_version=dataset_version,
        feature_version=feature_version,
        parameters=parameters,
    )


def publish_model_metadata(
    run_metadata: TrainingRunMetadata,
    model_name: str,
    version: str,
    artifact_path: Optional[str] = None,
    additional_metadata: Optional[Dict] = None,
    is_active: bool = False,
) -> ModelMetadata:
    """Publish model metadata after training.

    Args:
        run_metadata: Training run metadata
        model_name: Name for the model
        version: Model version
        artifact_path: Path to serialized model
        additional_metadata: Additional metadata
        is_active: Whether this is the active model

    Returns:
        ModelMetadata object
    """
    metadata = ModelMetadata(
        model_name=model_name,
        model_type=run_metadata.model_type,
        version=version,
        parameters=run_metadata.parameters,
        artifact_path=artifact_path,
        metadata=additional_metadata or {},
    )
    metadata.metadata["training_run_id"] = run_metadata.run_id
    metadata.metadata["is_active"] = is_active

    return metadata


def create_evaluation_metadata(
    model_id: str,
    evaluation_period_start: str,
    evaluation_period_end: str,
    mape: float,
    rmse: float,
    mae: float,
    additional_metrics: Optional[Dict] = None,
) -> Dict:
    """Create evaluation metadata for publishing.

    Args:
        model_id: ID of the model being evaluated
        evaluation_period_start: Start date of evaluation period
        evaluation_period_end: End date of evaluation period
        mape: Mean Absolute Percentage Error
        rmse: Root Mean Squared Error
        mae: Mean Absolute Error
        additional_metrics: Additional metrics

    Returns:
        Dictionary with evaluation metadata
    """
    return {
        "evaluation_id": str(uuid4()),
        "model_id": model_id,
        "evaluation_period_start": evaluation_period_start,
        "evaluation_period_end": evaluation_period_end,
        "mape": mape,
        "rmse": rmse,
        "mae": mae,
        "additional_metrics": additional_metrics or {},
    }
