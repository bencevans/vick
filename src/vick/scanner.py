"""BLE scanning that decodes Victron advertisements and dispatches to reporters."""

from __future__ import annotations

import inspect
import logging

from bleak import BleakScanner

from victron_ble.devices import (
    AcCharger,
    BatteryMonitor,
    BatterySense,
    DcDcConverter,
    DcEnergyMeter,
    Device,
    Inverter,
    LynxSmartBMS,
    MultiRS,
    OrionXS,
    SmartBatteryProtect,
    SmartLithium,
    SolarCharger,
    VEBus,
)
from victron_ble.devices import detect_device_type
from victron_ble.exceptions import AdvertisementKeyMismatchError, UnknownDeviceError
from victron_ble.scanner import BaseScanner

from vick.config import DeviceConfig
from vick.reporting.base import Reporter

logger = logging.getLogger(__name__)

DEVICE_TYPES: dict[str, type[Device]] = {
    "ac_charger": AcCharger,
    "battery_monitor": BatteryMonitor,
    "battery_sense": BatterySense,
    "dc_energy_meter": DcEnergyMeter,
    "dcdc_converter": DcDcConverter,
    "inverter": Inverter,
    "lynx_smart_bms": LynxSmartBMS,
    "multirs": MultiRS,
    "orion_xs": OrionXS,
    "smart_battery_protect": SmartBatteryProtect,
    "smart_lithium": SmartLithium,
    "solar_charger": SolarCharger,
    "vebus": VEBus,
}


def _extract_metrics(data) -> dict:
    metrics = {}
    for name, method in inspect.getmembers(data, predicate=inspect.ismethod):
        if name.startswith("get_"):
            value = method()
            if value is not None:
                metrics[name[4:]] = value
    return metrics


class DeviceScanner(BaseScanner):
    def __init__(
        self, devices: list[DeviceConfig], reporters: list[Reporter], adapter: str | None = None
    ) -> None:
        self._seen_data = set()
        kwargs = {"adapter": adapter} if adapter else {}
        self._scanner = BleakScanner(detection_callback=self._detection_callback, **kwargs)
        self._devices_by_address = {d.address: d for d in devices}
        self._reporters = reporters
        self._known_devices: dict[str, Device] = {}
        self._error_logged: set[str] = set()

    def _get_device(self, address: str, raw_data: bytes) -> Device | None:
        device = self._known_devices.get(address)
        if device is not None:
            return device

        config = self._devices_by_address.get(address)
        if config is None:
            return None

        if config.type is not None:
            device_klass = DEVICE_TYPES.get(config.type)
            if device_klass is None:
                raise UnknownDeviceError(
                    f"Unknown device type '{config.type}' configured for '{config.name}'"
                )
        else:
            device_klass = detect_device_type(raw_data)
            if device_klass is None:
                raise UnknownDeviceError(
                    f"Could not identify device type for '{config.name}' ({address})"
                )

        device = device_klass(config.key)
        self._known_devices[address] = device
        logger.info(f"Identified '{config.name}' ({address}) as {device_klass.__name__}")
        return device

    def callback(self, ble_device, raw_data: bytes, advertisement) -> None:
        address = ble_device.address.lower()
        config = self._devices_by_address.get(address)
        if config is None:
            logger.debug(f"Ignoring advertisement from unconfigured device {address}")
            return

        logger.debug(f"Received advertisement from '{config.name}' ({address}): {raw_data.hex()}")

        try:
            device = self._get_device(address, raw_data)
        except UnknownDeviceError as e:
            self._log_once(address, str(e))
            return
        if device is None:
            return

        try:
            parsed = device.parse(raw_data)
        except AdvertisementKeyMismatchError:
            self._log_once(
                address, f"Advertisement key for '{config.name}' does not match its data"
            )
            return
        self._error_logged.discard(address)

        metrics = _extract_metrics(parsed)
        device_type = type(device).__name__
        logger.debug(f"Read '{config.name}' ({device_type}): {metrics}")
        for reporter in self._reporters:
            try:
                reporter.report(config.name, device_type, metrics)
            except Exception:
                logger.exception(f"Reporter {type(reporter).__name__} failed for {config.name}")

    def _log_once(self, address: str, message: str) -> None:
        if address not in self._error_logged:
            logger.error(message)
            self._error_logged.add(address)
