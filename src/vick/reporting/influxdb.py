from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from vick.config import InfluxDBConfig
from vick.reporting.base import Reporter

logger = logging.getLogger(__name__)


class InfluxDBReporter(Reporter):
    def __init__(self, config: InfluxDBConfig) -> None:
        self._bucket = config.bucket
        self._client = InfluxDBClient(url=config.url, token=config.token, org=config.org)
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)

    def report(self, device_name: str, device_type: str, metrics: dict[str, Any]) -> None:
        point = Point(device_type).tag("device", device_name)
        for key, value in metrics.items():
            if value is None:
                continue
            if isinstance(value, Enum):
                value = value.name.lower()
            point.field(key, value)
        try:
            self._write_api.write(bucket=self._bucket, record=point)
        except Exception:
            logger.exception(f"Failed to write metrics for {device_name} to InfluxDB")

    def close(self) -> None:
        self._client.close()
