"""Aether integration for Home Assistant."""
from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

DOMAIN = "aether"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=8099): cv.port,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Aether component."""
    if DOMAIN not in config:
        return True

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["config"] = config[DOMAIN]

    def _base_url(call_or_conf) -> str:
        conf = config[DOMAIN]
        return f"http://{conf[CONF_HOST]}:{conf[CONF_PORT]}"

    async def handle_complete_chore(call: ServiceCall) -> None:
        """Mark a chore as complete."""
        chore_id = call.data["chore_id"]
        url = f"{_base_url(call)}/api/chores/{chore_id}/complete"
        session = async_get_clientsession(hass)
        try:
            async with session.post(url) as resp:
                if resp.status not in (200, 201):
                    _LOGGER.error("Aether complete_chore returned %s", resp.status)
                else:
                    _LOGGER.info("Completed chore %s", chore_id)
        except aiohttp.ClientError as exc:
            _LOGGER.error("Error completing chore: %s", exc)

    async def handle_what_now(call: ServiceCall) -> None:
        """Ask Aether what to do with available time."""
        minutes = call.data.get("minutes", 30)
        url = f"{_base_url(call)}/api/dashboard/quick-clean?minutes={minutes}"
        session = async_get_clientsession(hass)
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    hass.bus.async_fire(
                        f"{DOMAIN}_what_now",
                        {
                            "minutes": minutes,
                            "chores": [c["name"] for c in data.get("chores", [])[:5]],
                        },
                    )
        except aiohttp.ClientError as exc:
            _LOGGER.error("Error calling what_now: %s", exc)

    hass.services.async_register(
        DOMAIN,
        "complete_chore",
        handle_complete_chore,
        schema=vol.Schema({vol.Required("chore_id"): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        "what_now",
        handle_what_now,
        schema=vol.Schema({vol.Optional("minutes", default=30): cv.positive_int}),
    )

    return True
