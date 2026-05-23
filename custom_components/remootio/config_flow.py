"""Config flow for the Remootio integration."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from voluptuous.error import RequiredFieldInvalid
from voluptuous.schema_builder import REMOVE_EXTRA

from homeassistant.components.cover import CoverDeviceClass
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_DEVICE_CLASS, CONF_HOST
from homeassistant.core import HomeAssistant

from .aioremootio import (
    ConnectionOptions,
    RemootioClientAuthenticationError,
    RemootioClientConnectionEstablishmentError,
)
from .aioremootio.constants import (
    CONNECTION_OPTION_REGEX_API_AUTH_KEY,
    CONNECTION_OPTION_REGEX_API_SECRET_KEY,
    CONNECTION_OPTION_REGEX_HOST,
)
from .const import (
    CONF_API_AUTH_KEY,
    CONF_API_SECRET_KEY,
    CONF_DATA,
    CONF_SERIAL_NUMBER,
    CONF_TITLE,
    DOMAIN,
)
from .exceptions import UnsupportedRemootioDeviceError
from .utils import get_serial_number

_LOGGER = logging.getLogger(__name__)

INPUT_VALIDATION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, msg="Host is required"): vol.All(
            vol.Coerce(str),
            vol.Match(CONNECTION_OPTION_REGEX_HOST),
            msg="Host appears to be invalid; it can be an IP address or a host name that complies with RFC-1123",
        ),
        vol.Required(CONF_API_SECRET_KEY, msg="API Secret Key is required"): vol.All(
            vol.Coerce(str),
            vol.Upper,
            vol.Match(CONNECTION_OPTION_REGEX_API_SECRET_KEY),
            msg="API Secret Key appears to be invalid; it must be a sequence of 64 characters and can contain only numbers and english letters",
        ),
        vol.Required(CONF_API_AUTH_KEY, msg="API Auth Key is required"): vol.All(
            vol.Coerce(str),
            vol.Upper,
            vol.Match(CONNECTION_OPTION_REGEX_API_AUTH_KEY),
            msg="API Auth Key appears to be invalid; it must be a sequence of 64 characters and can contain only numbers and english letters",
        ),
        vol.Required(
            CONF_DEVICE_CLASS,
            default=CoverDeviceClass.GARAGE,
            msg="Controlled device's class is required",
        ): vol.All(
            vol.Coerce(str),
            vol.In([CoverDeviceClass.GARAGE, CoverDeviceClass.GATE]),
            msg="Controlled device's class appears to be invalid",
        ),
    },
    extra=REMOVE_EXTRA,
)

REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_SECRET_KEY): vol.All(
            vol.Coerce(str),
            vol.Upper,
            vol.Match(CONNECTION_OPTION_REGEX_API_SECRET_KEY),
        ),
        vol.Required(CONF_API_AUTH_KEY): vol.All(
            vol.Coerce(str),
            vol.Upper,
            vol.Match(CONNECTION_OPTION_REGEX_API_AUTH_KEY),
        ),
    },
    extra=REMOVE_EXTRA,
)

DEVICE_NAME = "Remootio Device"


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input and retrieve the device's serial number."""
    data = INPUT_VALIDATION_SCHEMA(data)

    connection_options: ConnectionOptions = ConnectionOptions(
        data[CONF_HOST], data[CONF_API_SECRET_KEY], data[CONF_API_AUTH_KEY]
    )

    device_serial_number: str = await get_serial_number(
        hass, connection_options, _LOGGER
    )

    data[CONF_SERIAL_NUMBER] = device_serial_number

    return {
        CONF_TITLE: f"{DEVICE_NAME} (Host: {data[CONF_HOST]}, S/N: {device_serial_number})",
        CONF_DATA: data,
    }


class RemootioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Remootio."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step."""
        user_input = user_input or {}
        errors: dict[str, str] = {}

        if len(user_input) != 0:
            try:
                validation_result = await validate_input(self.hass, user_input)
            except UnsupportedRemootioDeviceError:
                return self.async_abort(reason="unsupported_device")
            except vol.MultipleInvalid as ex:
                for error in ex.errors:
                    if isinstance(error, RequiredFieldInvalid):
                        errors[str(error.path[0])] = f"{error.path[0]}_required"
                    else:
                        errors[str(error.path[0])] = f"{error.path[0]}_invalid"
            except RemootioClientConnectionEstablishmentError:
                errors["base"] = "cannot_connect"
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except RemootioClientAuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception/error")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    validation_result[CONF_DATA][CONF_SERIAL_NUMBER]
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=validation_result[CONF_TITLE],
                    data=validation_result[CONF_DATA],
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_HOST,
                        default=user_input.get(CONF_HOST, vol.UNDEFINED),
                    ): vol.Coerce(str),
                    vol.Optional(
                        CONF_API_SECRET_KEY,
                        default=user_input.get(CONF_API_SECRET_KEY, vol.UNDEFINED),
                    ): vol.Coerce(str),
                    vol.Optional(
                        CONF_API_AUTH_KEY,
                        default=user_input.get(CONF_API_AUTH_KEY, vol.UNDEFINED),
                    ): vol.Coerce(str),
                    vol.Optional(
                        CONF_DEVICE_CLASS,
                        default=user_input.get(
                            CONF_DEVICE_CLASS, CoverDeviceClass.GARAGE
                        ),
                    ): vol.All(
                        vol.Coerce(str),
                        vol.In([CoverDeviceClass.GARAGE, CoverDeviceClass.GATE]),
                    ),
                },
                extra=REMOVE_EXTRA,
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a reauthentication flow triggered by an authentication failure."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-prompt for the API keys and validate them against the same device."""
        reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        errors: dict[str, str] = {}

        if user_input is not None:
            candidate = {
                CONF_HOST: reauth_entry.data[CONF_HOST],
                CONF_DEVICE_CLASS: reauth_entry.data[CONF_DEVICE_CLASS],
                CONF_API_SECRET_KEY: user_input[CONF_API_SECRET_KEY],
                CONF_API_AUTH_KEY: user_input[CONF_API_AUTH_KEY],
            }

            try:
                validation_result = await validate_input(self.hass, candidate)
            except UnsupportedRemootioDeviceError:
                return self.async_abort(reason="unsupported_device")
            except vol.MultipleInvalid as ex:
                for error in ex.errors:
                    if isinstance(error, RequiredFieldInvalid):
                        errors[str(error.path[0])] = f"{error.path[0]}_required"
                    else:
                        errors[str(error.path[0])] = f"{error.path[0]}_invalid"
            except RemootioClientConnectionEstablishmentError:
                errors["base"] = "cannot_connect"
            except TimeoutError:
                errors["base"] = "cannot_connect"
            except RemootioClientAuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception/error")
                errors["base"] = "unknown"
            else:
                if (
                    validation_result[CONF_DATA][CONF_SERIAL_NUMBER]
                    != reauth_entry.unique_id
                ):
                    return self.async_abort(reason="wrong_device")

                return self.async_update_reload_and_abort(
                    reauth_entry, data=validation_result[CONF_DATA]
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"host": reauth_entry.data[CONF_HOST]},
        )
