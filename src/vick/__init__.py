from __future__ import annotations

import asyncio
import logging

import click

from vick.config import Config, ConfigError, load_config
from vick.reporting.base import Reporter
from vick.scanner import DeviceScanner

logger = logging.getLogger("vick")


def build_reporters(config: Config) -> list[Reporter]:
    reporters: list[Reporter] = []
    if config.influxdb.enabled:
        from vick.reporting.influxdb import InfluxDBReporter

        reporters.append(InfluxDBReporter(config.influxdb))
    if config.prometheus.enabled:
        from vick.reporting.prometheus import PrometheusReporter

        reporters.append(PrometheusReporter(config.prometheus))
    if config.mqtt.enabled:
        from vick.reporting.mqtt import MqttReporter

        reporters.append(MqttReporter(config.mqtt))
    return reporters


async def run(config: Config) -> None:
    reporters = build_reporters(config)
    scanner = DeviceScanner(config.devices, reporters, adapter=config.scan.adapter)
    try:
        logger.info(f"Scanning for {[d.name for d in config.devices]}")
        await scanner.start()
        await asyncio.Event().wait()
    finally:
        await scanner.stop()
        for reporter in reporters:
            reporter.close()


@click.command()
@click.option(
    "-c",
    "--config",
    "config_path",
    default="config.toml",
    show_default=True,
    help="Path to the vick TOML configuration file.",
)
@click.option("-v", "--verbose", is_flag=True, help="Increase logging output.")
def main(config_path: str, verbose: bool) -> None:
    logging.basicConfig(level=logging.INFO)
    # Keep third-party BLE library logs quiet; -v only affects vick's own logging.
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    try:
        config = load_config(config_path)
    except ConfigError as e:
        raise click.ClickException(str(e))

    try:
        asyncio.run(run(config))
    except KeyboardInterrupt:
        pass
