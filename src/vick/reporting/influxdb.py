"""InfluxDB reporting, supporting both the 1.x line-protocol HTTP API and 2.x clients."""

from __future__ import annotations

import base64
import logging
import urllib.parse
import urllib.request
from enum import Enum
from typing import Any

from vick.config import InfluxDBConfig
from vick.reporting.base import Reporter

logger = logging.getLogger(__name__)


def _escape_key(value: Any) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace("=", "\\=")
        .replace(" ", "\\ ")
    )


def _field_value(value: Any) -> str:
    if isinstance(value, Enum):
        value = value.name.lower()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value}i"
    if isinstance(value, float):
        return repr(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _line_protocol(measurement: str, tags: dict[str, Any], fields: dict[str, Any]) -> str:
    measurement_esc = str(measurement).replace(",", "\\,").replace(" ", "\\ ")
    tag_str = "".join(f",{_escape_key(k)}={_escape_key(v)}" for k, v in tags.items())
    field_str = ",".join(f"{_escape_key(k)}={_field_value(v)}" for k, v in fields.items())
    return f"{measurement_esc}{tag_str} {field_str}"


class InfluxDBV1Reporter(Reporter):
    """Writes to InfluxDB 1.x via the /write line-protocol HTTP API."""

    def __init__(self, config: InfluxDBConfig) -> None:
        self._base_url = f"{config.protocol}://{config.host}:{config.port}"
        self._database = config.database
        self._auth_header = None
        if config.username:
            token = base64.b64encode(f"{config.username}:{config.password}".encode()).decode()
            self._auth_header = f"Basic {token}"

    def report(
        self, device_name: str, device_type: str, address: str, metrics: dict[str, Any]
    ) -> None:
        fields = {k: v for k, v in metrics.items() if v is not None}
        if not fields:
            return
        tags = {"device": device_name, "address": address}
        line = _line_protocol(device_type, tags, fields)
        query = urllib.parse.urlencode({"db": self._database, "precision": "s"})
        req = urllib.request.Request(
            f"{self._base_url}/write?{query}", data=line.encode(), method="POST"
        )
        if self._auth_header:
            req.add_header("Authorization", self._auth_header)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status >= 300:
                    logger.error(f"InfluxDB write failed ({resp.status}) for {device_name}")
        except Exception:
            logger.exception(f"Failed to write metrics for {device_name} to InfluxDB")

    def close(self) -> None:
        pass


class InfluxDBV2Reporter(Reporter):
    """Writes to InfluxDB 2.x using the official client's token/org/bucket auth."""

    def __init__(self, config: InfluxDBConfig) -> None:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import SYNCHRONOUS

        self._bucket = config.bucket
        url = f"{config.protocol}://{config.host}:{config.port}"
        self._client = InfluxDBClient(url=url, token=config.token, org=config.org)
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)

    def report(
        self, device_name: str, device_type: str, address: str, metrics: dict[str, Any]
    ) -> None:
        from influxdb_client import Point

        point = Point(device_type).tag("device", device_name).tag("address", address)
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


def create_influxdb_reporter(config: InfluxDBConfig) -> Reporter:
    if config.version == 1:
        return InfluxDBV1Reporter(config)
    return InfluxDBV2Reporter(config)
