# Vick

Victron BLE monitoring tool with reporting to InfluxDB, Prometheus and MQTT.

## Features

- Read data from Victron devices over Bluetooth Low Energy (BLE), using the
  manufacturer's Instant Readout encrypted advertisements (no pairing needed)
- Report to InfluxDB, Prometheus, and/or MQTT simultaneously
- Monitor multiple devices, of different types, from a single config file

## Installation

```sh
uv tool install vick
```

## Configuration

Vick is configured with a [TOML](https://toml.io/) file. By default it looks
for `config.toml` in the current directory; pass a different path with
`vick --config /path/to/config.toml`.

A device must be listed under `[[devices]]` before Vick will read it. Each
device needs its BLE MAC address and the advertisement decryption key from the
VictronConnect app (**Settings > Product Info > Show Instant Readout
details**). The device type (battery monitor, solar charger, etc.) is
auto-detected from the advertisement, so it doesn't need to be configured.

At least one `[reporting.*]` backend must be enabled, or Vick has nowhere to
send the data it reads.

```toml
[scan]
# BLE adapter to use (defaults to the system default adapter)
adapter = "hci0"

[[devices]]
# Friendly name used as the metric/tag name for this device
name = "starter-battery"
# BLE MAC address of the device
address = "AA:BB:CC:DD:EE:FF"
# Advertisement decryption key, from the VictronConnect app
key = "abcdef0123456789abcdef0123456789"

[[devices]]
name = "solar-charger"
address = "11:22:33:44:55:66"
key = "0123456789abcdef0123456789abcdef"

[reporting.influxdb]
enabled = false
url = "http://localhost:8086"
token = "my-influxdb-token"
org = "my-org"
bucket = "vick"

[reporting.prometheus]
enabled = false
# Address the /metrics HTTP endpoint listens on
host = "0.0.0.0"
port = 9101

[reporting.mqtt]
enabled = false
host = "localhost"
port = 1883
username = ""
password = ""
# Metrics are published to "<topic_prefix>/<device name>/<metric>"
topic_prefix = "vick"
```

See [config.example.toml](config.example.toml) for a full annotated example,
including the list of supported device `type` overrides.

## Usage

```sh
vick --config config.toml
```

## Docker

A prebuilt image is available as `ghcr.io/bencevans/vick`, or you can build it
yourself with `docker build -t vick .`.

BLE access relies on the host's BlueZ stack over D-Bus (not the network
stack), so the container just needs access to the system D-Bus socket. If
you're exposing a reporter port (e.g. Prometheus), publish it with `-p`:

```sh
docker run --rm \
  -v /var/run/dbus:/var/run/dbus \
  -v "$(pwd)/config.toml:/config/config.toml:ro" \
  -p 9101:9101 \
  vick
```

This only works on Linux hosts with BlueZ (e.g. Raspberry Pi OS) — Docker
Desktop on macOS/Windows cannot pass through Bluetooth adapters.
