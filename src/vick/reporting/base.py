"""Reporting backends that publish decoded device metrics elsewhere."""

from __future__ import annotations

import abc
from typing import Any


class Reporter(abc.ABC):
    @abc.abstractmethod
    def report(
        self, device_name: str, device_type: str, address: str, metrics: dict[str, Any]
    ) -> None:
        """Publish a set of metrics read from a device."""

    def close(self) -> None:
        """Release any resources held by the reporter. No-op by default."""
