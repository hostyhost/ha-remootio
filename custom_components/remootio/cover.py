"""Support for a Remootio controlled garage door or gate."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_NAME, CONF_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RemootioConfigEntry
from .aioremootio import (
    Event,
    EventType,
    Listener,
    RemootioClient,
    State,
    StateChange,
)
from .const import ATTR_SERIAL_NUMBER, CONF_SERIAL_NUMBER, DOMAIN

_LOGGER = logging.getLogger(__name__)

# The device pushes state changes, but it can drop its websocket around operations
# and miss an event. Poll periodically as a backstop so a missed event self-corrects
# (and the query doubles as a keepalive / reconnect trigger).
SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: RemootioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a ``RemootioCover`` entity based on the given configuration entry."""
    serial_number: str = config_entry.data[CONF_SERIAL_NUMBER]
    device_class: CoverDeviceClass = config_entry.data[CONF_DEVICE_CLASS]
    client: RemootioClient = config_entry.runtime_data

    async_add_entities([RemootioCover(serial_number, device_class, client)])


class RemootioCover(CoverEntity):
    """Cover entity which represents a Remootio controlled garage door or gate."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = True
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(
        self,
        serial_number: str,
        device_class: CoverDeviceClass,
        client: RemootioClient,
    ) -> None:
        """Initialize this cover entity."""
        self._client = client
        self._attr_unique_id = serial_number
        self._attr_device_class = device_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial_number)},
            manufacturer="Assemblabs Ltd",
            model=client.device_type.value if client.device_type is not None else None,
            sw_version=f"API v{client.api_version}",
        )

    async def async_added_to_hass(self) -> None:
        """Register listeners on the client to be notified about state changes and events."""
        await self._client.add_state_change_listener(
            RemootioCoverStateChangeListener(self)
        )
        await self._client.add_event_listener(RemootioCoverEventListener(self))

        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_update(self) -> None:
        """Trigger a state update of the used Remootio client."""
        await self._client.trigger_state_update()

    @property
    def available(self) -> bool:
        """Return True when the client is connected to the Remootio device."""
        return self._client.connected

    @property
    def is_opening(self) -> bool:
        """Return True when the garage door or gate is currently opening."""
        return self._client.state == State.OPENING

    @property
    def is_closing(self) -> bool:
        """Return True when the garage door or gate is currently closing."""
        return self._client.state == State.CLOSING

    @property
    def is_closed(self) -> bool | None:
        """Return whether the garage door or gate is closed.

        Returns ``None`` when the state is unknown or no sensor is installed.
        """
        if self._client.state in (State.UNKNOWN, State.NO_SENSOR_INSTALLED):
            return None
        return self._client.state == State.CLOSED

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the garage door or gate."""
        await self._client.trigger_open()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the garage door or gate."""
        await self._client.trigger_close()


class RemootioCoverStateChangeListener(Listener[StateChange]):
    """Listener invoked when the Remootio controlled garage door or gate changes its state."""

    def __init__(self, owner: RemootioCover) -> None:
        """Initialize an instance of this class."""
        super().__init__()
        self._owner = owner

    async def execute(self, client: RemootioClient, subject: StateChange) -> None:
        """Tell Home Assistant that the represented device has changed its state."""
        self._owner.async_write_ha_state()


class RemootioCoverEventListener(Listener[Event]):
    """Listener invoked on an event sent by the Remootio device."""

    def __init__(self, owner: RemootioCover) -> None:
        """Initialize an instance of this class."""
        super().__init__()
        self._owner = owner

    async def execute(self, client: RemootioClient, subject: Event) -> None:
        """React to events sent by the Remootio device.

        Updates the entity availability when the client connects/disconnects and fires the
        ``remootio_left_open`` event in Home Assistant when the device reports it was left open.
        """
        if subject.type in (EventType.CONNECTED, EventType.DISCONNECTED):
            self._owner.async_write_ha_state()
        elif subject.type == EventType.LEFT_OPEN:
            event_type = f"{DOMAIN}_{subject.type.name.lower()}"
            self._owner.hass.bus.async_fire(
                event_type,
                {
                    ATTR_ENTITY_ID: self._owner.entity_id,
                    ATTR_SERIAL_NUMBER: self._owner.unique_id,
                    ATTR_NAME: self._owner.name,
                },
            )
