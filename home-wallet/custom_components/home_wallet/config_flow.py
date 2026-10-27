"""Config flow for Home Wallet."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_TOKEN, CONF_URL

from .const import DOMAIN


class HomeWalletConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Home Wallet config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the Home Assistant URL and a long-lived access token.

        The token is what the Android app uses; it is created in Home
        Assistant under the user's profile ("Long-Lived Access Tokens").
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id("home_wallet")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Home Wallet",
                data={
                    CONF_URL: user_input[CONF_URL].rstrip("/"),
                    CONF_TOKEN: user_input[CONF_TOKEN],
                },
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL): str,
                    vol.Required(CONF_TOKEN): str,
                }
            ),
            errors=errors,
        )
