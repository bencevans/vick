"""Reporting backends that publish decoded device metrics elsewhere."""

from __future__ import annotations

import abc
import time
from typing import Any


class Reporter(abc.ABC):
    @abc.abstractmethod
    def report(
        self, device_name: str, device_type: str, address: str, metrics: dict[str, Any]
    ) -> None:
        """Publish a set of metrics read from a device."""

    def close(self) -> None:
        """Release any resources held by the reporter. No-op by default."""


class IntervalThrottle:
    """Tracks, per device address, whether enough time has passed to report again."""

    def __init__(self, min_interval: float) -> None:
        self._min_interval = min_interval
        self._last_reported: dict[str, float] = {}

    def ready(self, address: str) -> bool:
        if self._min_interval <= 0:
            return True
        now = time.monotonic()
        last = self._last_reported.get(address)
        if last is not None and now - last < self._min_interval:
            return False
        self._last_reported[address] = now
        return True
