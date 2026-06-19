"""Binary sensor entities exposing Remootio status flags."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RemootioConfigEntry
from .aioremootio import RemootioClient
from .const import CONF_SERIAL_NUMBER
from .entity import RemootioEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RemootioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Remootio binary sensor entities."""
    serial_number: str = config_entry.data[CONF_SERIAL_NUMBER]
    client: RemootioClient = config_entry.runtime_data

    async_add_entities(
        [
            RemootioConnectivityBinarySensor(serial_number, client),
            RemootioLeftOpenBinarySensor(serial_number, client),
            RemootioStatusSensorEnabledBinarySensor(serial_number, client),
            RemootioManualButtonEnabledBinarySensor(serial_number, client),
            RemootioDoorbellEnabledBinarySensor(serial_number, client),
            RemootioOutput1BinarySensor(serial_number, client),
            RemootioOutput2BinarySensor(serial_number, client),
        ]
    )


class RemootioConnectivityBinarySensor(RemootioEntity, BinarySensorEntity):
    """Whether the client is connected to the device."""

    _attr_name = "Connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "connectivity")

    @property
    def available(self) -> bool:
        # A connectivity sensor must stay available to report "disconnected".
        return True

    @property
    def is_on(self) -> bool:
        return self._client.connected


class RemootioLeftOpenBinarySensor(RemootioEntity, BinarySensorEntity):
    """Whether the device reported the door/gate as left open."""

    _attr_name = "Left open"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:garage-alert"

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "left_open")

    @property
    def is_on(self) -> bool | None:
        return self._client.left_open


class RemootioStatusSensorEnabledBinarySensor(RemootioEntity, BinarySensorEntity):
    """Whether the device's status sensor is enabled."""

    _attr_name = "Status sensor enabled"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:leak"

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "status_sensor_enabled")

    @property
    def is_on(self) -> bool | None:
        return self._client.sensor_enabled


class RemootioManualButtonEnabledBinarySensor(RemootioEntity, BinarySensorEntity):
    """Whether the physical manual button is enabled."""

    _attr_name = "Manual button enabled"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:gesture-tap-button"

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "manual_button_enabled")

    @property
    def is_on(self) -> bool | None:
        return self._client.manual_button_enabled


class RemootioDoorbellEnabledBinarySensor(RemootioEntity, BinarySensorEntity):
    """Whether the doorbell input is enabled."""

    _attr_name = "Doorbell enabled"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:bell"

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "doorbell_enabled")

    @property
    def is_on(self) -> bool | None:
        return self._client.doorbell_enabled


class RemootioOutput1BinarySensor(RemootioEntity, BinarySensorEntity):
    """Whether the primary relay output is currently active."""

    _attr_name = "Relay output 1 active"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:electric-switch"

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "output1_active")

    @property
    def is_on(self) -> bool | None:
        return self._client.output1_active


class RemootioOutput2BinarySensor(RemootioEntity, BinarySensorEntity):
    """Whether the secondary relay output is currently active."""

    _attr_name = "Relay output 2 active"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:electric-switch"

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "output2_active")

    @property
    def is_on(self) -> bool | None:
        return self._client.output2_active
