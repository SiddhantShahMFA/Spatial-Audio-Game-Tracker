"""Replay source abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO

from .models import ReplayBundle


class ReplaySource(ABC):
    @abstractmethod
    def load(
        self,
        tracking_file: str | BinaryIO,
        events_file: str | BinaryIO,
        *,
        source_name: str,
    ) -> ReplayBundle:
        """Load a replay bundle from provider-specific files."""
