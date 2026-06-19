"""Button entities for Remootio control outputs and maintenance actions."""
from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
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
    """Set up the Remootio button entities."""
    serial_number: str = config_entry.data[CONF_SERIAL_NUMBER]
    client: RemootioClient = config_entry.runtime_data

    async_add_entities(
        [
            RemootioTriggerButton(serial_number, client),
            RemootioSecondaryTriggerButton(serial_number, client),
            RemootioRestartButton(serial_number, client),
        ]
    )


class RemootioTriggerButton(RemootioEntity, ButtonEntity):
    """Pulse the primary control output regardless of the known door state."""

    _attr_name = "Trigger"
    _attr_icon = "mdi:gate"

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "trigger")

    async def async_press(self) -> None:
        await self._client.trigger()


class RemootioSecondaryTriggerButton(RemootioEntity, ButtonEntity):
    """Pulse the secondary (free) relay output, on devices that have one."""

    _attr_name = "Trigger secondary output"
    _attr_icon = "mdi:gate-arrow-right"
    _attr_entity_registry_enabled_default = False

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "trigger_secondary")

    async def async_press(self) -> None:
        await self._client.trigger_secondary()


class RemootioRestartButton(RemootioEntity, ButtonEntity):
    """Restart the Remootio device."""

    _attr_name = "Restart device"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, serial_number: str, client: RemootioClient) -> None:
        super().__init__(serial_number, client, "restart")

    async def async_press(self) -> None:
        await self._client.restart()
