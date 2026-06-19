"""Sensor entities exposing Remootio telemetry."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RemootioConfigEntry
from .aioremootio import RemootioClient
from .aioremootio.enums import EventSource
from .const import CONF_SERIAL_NUMBER
from .entity import RemootioEntity

# Friendly labels for the connection method a key used.
_SOURCE_NAMES = {
    EventSource.DEVICE_OVER_BLUETOOTH: "Bluetooth",
    EventSource.DEVICE_OVER_WIFI: "Wi-Fi",
    EventSource.DEVICE_OVER_INTERNET: "Internet",
    EventSource.DEVICE_VIA_AUTOOPEN_FEATURE: "Auto-open",
    EventSource.UNKNOWN: "Unknown",
    EventSource.NONE: "None",
    EventSource.CLIENT: "Home Assistant",
}


def _prettify(name: str) -> str:
    """Turn an enum member name like ``RELAY_TRIGGER`` into ``Relay trigger``."""
    return name.replace("_", " ").capitalize()


def _source_name(source: EventSource | None) -> str | None:
    if source is None:
        return None
    return _SOURCE_NAMES.get(source, _prettify(source.name))


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RemootioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Remootio sensor entities."""
    serial_number: str = config_entry.data[CONF_SERIAL_NUMBER]
    client: RemootioClient = config_entry.runtime_data

    async_add_entities(
        [
            RemootioLastOperatedBySensor(serial_number, client),
            RemootioLastEventSensor(serial_number, client),
            RemootioUptimeSensor(serial_number, client),
            RemootioLeftOpenDurationSensor(serial_number, client),
        ]
    )


class RemootioLastOperatedBySensor(RemootioEntity, SensorEntity):
    """Which key/method last operated the device."""

    _attr_name = "Last operated by"
    _attr_icon = "mdi:account-key"

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "last_operated_by")

    @property
    def native_value(self) -> str | None:
        key = self._client.last_event_key
        if key is None:
            return None
        return f"{_prettify(key.key_type.name)} #{key.key_number}"

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        key = self._client.last_event_key
        return {
            "via": _source_name(self._client.last_event_source),
            "key_type": _prettify(key.key_type.name) if key is not None else None,
            "key_number": key.key_number if key is not None else None,
        }


class RemootioLastEventSensor(RemootioEntity, SensorEntity):
    """The most recent event reported by the device."""

    _attr_name = "Last event"
    _attr_icon = "mdi:history"

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "last_event")

    @property
    def native_value(self) -> str | None:
        event_type = self._client.last_event_type
        if event_type is None:
            return None
        return _prettify(event_type.name)


class RemootioUptimeSensor(RemootioEntity, SensorEntity):
    """Device uptime since its last restart."""

    _attr_name = "Uptime"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "uptime")

    @property
    def native_value(self) -> int | None:
        uptime = self._client.uptime
        return int(uptime) if uptime is not None else None


class RemootioLeftOpenDurationSensor(RemootioEntity, SensorEntity):
    """How long the door/gate was reported open in the most recent left-open event."""

    _attr_name = "Left open duration"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer-alert"

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "left_open_duration")

    @property
    def native_value(self) -> float | None:
        return self._client.left_open_duration
