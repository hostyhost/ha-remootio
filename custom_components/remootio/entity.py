"""Shared base entity and device info for the Remootio integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .aioremootio import RemootioClient
from .aioremootio.enums import DeviceType
from .const import DOMAIN


def build_device_info(serial_number: str, client: RemootioClient) -> DeviceInfo:
    """Build the shared device-registry entry every Remootio entity attaches to."""
    device_type: DeviceType | None = client.device_type
    if device_type is None or device_type == DeviceType.UNKNOWN:
        model: str | None = None
    else:
        # "remootio-3" -> "Remootio 3"
        model = device_type.value.replace("-", " ").title()

    return DeviceInfo(
        identifiers={(DOMAIN, serial_number)},
        manufacturer="Assemblabs Ltd",
        model=model,
        sw_version=f"API v{client.api_version}" if client.api_version is not None else None,
        serial_number=serial_number,
    )


class RemootioEntity(Entity):
    """Base for Remootio entities whose state is derived from the client's cached telemetry.

    Subscribes to the client's update notifications so the entity re-renders whenever the
    device reports a state change, an event, or a connect/disconnect.
    """

    _attr_has_entity_name = True

    def __init__(self, serial_number: str, client: RemootioClient, key: str) -> None:
        """Initialize the entity with a stable unique id and shared device info."""
        self._client = client
        self._serial_number = serial_number
        self._attr_unique_id = f"{serial_number}_{key}"
        self._attr_device_info = build_device_info(serial_number, client)

    @property
    def available(self) -> bool:
        """Entities are available while the client is connected to the device."""
        return self._client.connected

    async def async_added_to_hass(self) -> None:
        """Register for client telemetry updates."""
        self._client.add_update_listener(self._handle_client_update)

    async def async_will_remove_from_hass(self) -> None:
        """Stop listening for client telemetry updates."""
        self._client.remove_update_listener(self._handle_client_update)

    def _handle_client_update(self) -> None:
        """Schedule a state write when the client's telemetry changes."""
        self.async_write_ha_state()
