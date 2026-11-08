"""Explicitly configured image-reading adapters; importing never loads a model."""

from .base import AdapterError, TranscriptionResult
from .registry import ModelRegistry

__all__ = ["AdapterError", "ModelRegistry", "TranscriptionResult"]
