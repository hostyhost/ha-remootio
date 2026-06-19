"""The Remootio integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_NAME, CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .aioremootio import ConnectionOptions, Event, EventType, Listener, RemootioClient
from .aioremootio.errors import RemootioClientAuthenticationError, RemootioError
from .const import (
    ATTR_SERIAL_NUMBER,
    CONF_API_AUTH_KEY,
    CONF_API_SECRET_KEY,
    CONF_SERIAL_NUMBER,
    DOMAIN,
)
from .utils import create_client

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.COVER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

# Device events forwarded onto the Home Assistant event bus as ``remootio_<type>`` for automations.
# (``LeftOpen`` keeps its dedicated ``remootio_left_open`` event fired from cover.py.)
EVENT_BUS_EVENT_TYPES = {
    EventType.RELAY_TRIGGER,
    EventType.SECONDARY_RELAY_TRIGGER,
    EventType.KEY_CONNECTED,
    EventType.KEY_MANAGEMENT,
    EventType.MANUAL_BUTTON_PUSHED,
    EventType.DOORBELL_PUSHED,
    EventType.SENSOR_FLIPPED,
    EventType.RESTART,
}

RemootioConfigEntry = ConfigEntry[RemootioClient]


class RemootioEventBusListener(Listener[Event]):
    """Forward selected device events onto the Home Assistant event bus for automations."""

    def __init__(self, hass: HomeAssistant, serial_number: str) -> None:
        super().__init__()
        self._hass = hass
        self._serial_number = serial_number

    async def execute(self, client: RemootioClient, subject: Event) -> None:
        if subject.type not in EVENT_BUS_EVENT_TYPES:
            return

        event_data: dict[str, object] = {
            ATTR_SERIAL_NUMBER: self._serial_number,
            ATTR_NAME: subject.type.name.replace("_", " ").capitalize(),
            "event_type": subject.type.value,
            "source": subject.source.value if subject.source is not None else None,
        }
        if subject.key is not None:
            event_data["key_type"] = subject.key.key_type.value
            event_data["key_number"] = subject.key.key_number

        self._hass.bus.async_fire(
            f"{DOMAIN}_{subject.type.name.lower()}", event_data
        )


async def async_setup_entry(hass: HomeAssistant, entry: RemootioConfigEntry) -> bool:
    """Set up Remootio from a config entry."""
    connection_options = ConnectionOptions(
        entry.data[CONF_HOST],
        entry.data[CONF_API_SECRET_KEY],
        entry.data[CONF_API_AUTH_KEY],
    )
    serial_number: str = entry.data[CONF_SERIAL_NUMBER]

    try:
        client = await create_client(
            hass, connection_options, _LOGGER, serial_number
        )
    except RemootioClientAuthenticationError as ex:
        raise ConfigEntryAuthFailed(
            "Authentication by the Remootio device failed"
        ) from ex
    except (RemootioError, TimeoutError) as ex:
        raise ConfigEntryNotReady(
            "Unable to connect to the Remootio device"
        ) from ex

    entry.runtime_data = client

    await client.add_event_listener(RemootioEventBusListener(hass, serial_number))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: RemootioConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unloaded:
        await entry.runtime_data.terminate()

    return unloaded
