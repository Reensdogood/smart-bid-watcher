from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..models import Notice


class ProcurementProvider(ABC):
    """Extension point for additional procurement sites."""

    source_name: str

    @abstractmethod
    def fetch(self, start: datetime, end: datetime) -> list[Notice]:
        raise NotImplementedError
