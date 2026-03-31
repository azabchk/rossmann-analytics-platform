"""Artifact management for model serialization.

This module provides functions for publishing and loading model artifacts.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import joblib


class ArtifactMetadata:
    """Container for artifact metadata."""

    def __init__(
        self,
        artifact_type: str,
        model_type: str,
        version: str,
        artifact_path: str,
        additional_metadata: Optional[Dict] = None,
    ):
        """Initialize artifact metadata.

        Args:
            artifact_type: Type of artifact (model, features, etc.)
            model_type: Type of model
            version: Version string
            artifact_path: Path to the artifact file
            additional_metadata: Additional metadata
        """
        self.artifact_id = str(uuid4())
        self.artifact_type = artifact_type
        self.model_type = model_type
        self.version = version
        self.artifact_path = artifact_path
        self.artifact_hash = None
        self.metadata = additional_metadata or {}
        self.published_at = datetime.utcnow()

    def calculate_hash(self) -> str:
        """Calculate hash of the artifact file."""
        if Path(self.artifact_path).exists():
            with open(self.artifact_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            self.artifact_hash = file_hash
        return self.artifact_hash or ""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "model_type": self.model_type,
            "version": self.version,
            "artifact_path": self.artifact_path,
            "artifact_hash": self.artifact_hash,
            "metadata": self.metadata,
            "published_at": self.published_at.isoformat(),
        }


def publish_artifact(
    artifact: Any,
    artifact_path: str,
    artifact_type: str,
    model_type: str,
    version: str,
    additional_metadata: Optional[Dict] = None,
) -> ArtifactMetadata:
    """Publish an artifact to storage.

    Args:
        artifact: Object to serialize
        artifact_path: Path where to save the artifact
        artifact_type: Type of artifact
        model_type: Type of model
        version: Version string
        additional_metadata: Additional metadata

    Returns:
        ArtifactMetadata object
    """
    # Ensure directory exists
    Path(artifact_path).parent.mkdir(parents=True, exist_ok=True)

    # Save artifact using joblib
    joblib.dump(artifact, artifact_path)

    # Create metadata
    metadata = ArtifactMetadata(
        artifact_type=artifact_type,
        model_type=model_type,
        version=version,
        artifact_path=artifact_path,
        additional_metadata=additional_metadata,
    )

    # Calculate hash
    metadata.calculate_hash()

    return metadata


def load_artifact(artifact_path: str) -> Any:
    """Load an artifact from storage.

    Args:
        artifact_path: Path to the artifact file

    Returns:
        Loaded artifact object
    """
    return joblib.load(artifact_path)


def save_model_metadata(
    metadata: ArtifactMetadata,
    metadata_path: str,
) -> None:
    """Save artifact metadata to a JSON file.

    Args:
        metadata: ArtifactMetadata object
        metadata_path: Path where to save metadata
    """
    Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "w") as f:
        json.dump(metadata.to_dict(), f, indent=2)


def load_model_metadata(metadata_path: str) -> Optional[ArtifactMetadata]:
    """Load artifact metadata from a JSON file.

    Args:
        metadata_path: Path to the metadata file

    Returns:
        ArtifactMetadata object or None if file doesn't exist
    """
    if not Path(metadata_path).exists():
        return None

    with open(metadata_path, "r") as f:
        data = json.load(f)

    metadata = ArtifactMetadata(
        artifact_type=data["artifact_type"],
        model_type=data["model_type"],
        version=data["version"],
        artifact_path=data["artifact_path"],
        additional_metadata=data.get("metadata", {}),
    )
    metadata.artifact_id = data["artifact_id"]
    metadata.artifact_hash = data["artifact_hash"]
    metadata.published_at = datetime.fromisoformat(data["published_at"])

    return metadata
