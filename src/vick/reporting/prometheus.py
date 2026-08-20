from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from prometheus_client import Gauge, start_http_server

from vick.config import PrometheusConfig
from vick.reporting.base import Reporter

logger = logging.getLogger(__name__)


class PrometheusReporter(Reporter):
    def __init__(self, config: PrometheusConfig) -> None:
        self._gauges: dict[str, Gauge] = {}
        start_http_server(config.port, addr=config.host)

    def _gauge(self, key: str) -> Gauge:
        gauge = self._gauges.get(key)
        if gauge is None:
            gauge = Gauge(f"vick_{key}", f"Victron {key}", ["device", "device_type", "address"])
            self._gauges[key] = gauge
        return gauge

    def report(
        self, device_name: str, device_type: str, address: str, metrics: dict[str, Any]
    ) -> None:
        for key, value in metrics.items():
            if isinstance(value, Enum):
                value = value.value
            if not isinstance(value, (int, float)):
                continue
            self._gauge(key).labels(
                device=device_name, device_type=device_type, address=address
            ).set(value)
