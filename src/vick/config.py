"""Loading and validation of the vick TOML configuration file."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class ConfigError(Exception):
    """Raised when the configuration file is missing or invalid."""


@dataclass
class DeviceConfig:
    name: str
    address: str
    key: str
    type: str | None = None


@dataclass
class ScanConfig:
    adapter: str | None = None


@dataclass
class InfluxDBConfig:
    enabled: bool = False
    url: str = "http://localhost:8086"
    token: str = ""
    org: str = ""
    bucket: str = "vick"


@dataclass
class PrometheusConfig:
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 9101


@dataclass
class MqttConfig:
    enabled: bool = False
    host: str = "localhost"
    port: int = 1883
    username: str = ""
    password: str = ""
    topic_prefix: str = "vick"


@dataclass
class Config:
    scan: ScanConfig = field(default_factory=ScanConfig)
    devices: list[DeviceConfig] = field(default_factory=list)
    influxdb: InfluxDBConfig = field(default_factory=InfluxDBConfig)
    prometheus: PrometheusConfig = field(default_factory=PrometheusConfig)
    mqtt: MqttConfig = field(default_factory=MqttConfig)


def load_config(path: str) -> Config:
    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}")
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Could not parse config file {path}: {e}")

    devices = []
    for i, raw_device in enumerate(raw.get("devices", [])):
        for required in ("name", "address", "key"):
            if not raw_device.get(required):
                raise ConfigError(f"devices[{i}] is missing required field '{required}'")
        devices.append(
            DeviceConfig(
                name=raw_device["name"],
                address=raw_device["address"].lower(),
                key=raw_device["key"],
                type=raw_device.get("type"),
            )
        )
    if not devices:
        raise ConfigError("No devices configured; add at least one [[devices]] entry")

    reporting = raw.get("reporting", {})
    try:
        influxdb = InfluxDBConfig(**reporting.get("influxdb", {}))
        prometheus = PrometheusConfig(**reporting.get("prometheus", {}))
        mqtt = MqttConfig(**reporting.get("mqtt", {}))
        scan = ScanConfig(**raw.get("scan", {}))
    except TypeError as e:
        raise ConfigError(f"Invalid config option: {e}")

    if not (influxdb.enabled or prometheus.enabled or mqtt.enabled):
        raise ConfigError(
            "No reporting backend enabled; enable at least one of "
            "[reporting.influxdb], [reporting.prometheus], [reporting.mqtt]"
        )

    return Config(
        scan=scan,
        devices=devices,
        influxdb=influxdb,
        prometheus=prometheus,
        mqtt=mqtt,
    )
