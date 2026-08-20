from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

import paho.mqtt.client as mqtt

from vick.config import MqttConfig
from vick.reporting.base import IntervalThrottle, Reporter

logger = logging.getLogger(__name__)


class MqttReporter(Reporter):
    def __init__(self, config: MqttConfig) -> None:
        self._topic_prefix = config.topic_prefix
        self._client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        if config.username:
            self._client.username_pw_set(config.username, config.password)
        self._client.connect(config.host, config.port)
        self._client.loop_start()
        self._throttle = IntervalThrottle(config.min_interval)

    def report(
        self, device_name: str, device_type: str, address: str, metrics: dict[str, Any]
    ) -> None:
        if not self._throttle.ready(address):
            return
        self._client.publish(
            f"{self._topic_prefix}/{device_name}/address", json.dumps(address), retain=True
        )
        for key, value in metrics.items():
            if value is None:
                continue
            if isinstance(value, Enum):
                value = value.name.lower()
            topic = f"{self._topic_prefix}/{device_name}/{key}"
            self._client.publish(topic, json.dumps(value), retain=True)

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
