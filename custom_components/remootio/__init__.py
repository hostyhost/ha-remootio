"""The Remootio integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .aioremootio import ConnectionOptions, RemootioClient
from .aioremootio.errors import RemootioClientAuthenticationError, RemootioError
from .const import CONF_API_AUTH_KEY, CONF_API_SECRET_KEY, CONF_SERIAL_NUMBER
from .utils import create_client

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.COVER]

RemootioConfigEntry = ConfigEntry[RemootioClient]


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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: RemootioConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unloaded:
        await entry.runtime_data.terminate()

    return unloaded
