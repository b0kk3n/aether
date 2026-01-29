"""Aether integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

DOMAIN = "aether"
PLATFORMS = [Platform.SENSOR]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=8080): cv.port,
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

    # Register services
    async def handle_add_task(call: ServiceCall) -> None:
        """Handle add task service call."""
        text = call.data.get("text", "")
        if not text:
            return

        host = config[DOMAIN][CONF_HOST]
        port = config[DOMAIN][CONF_PORT]
        url = f"http://{host}:{port}/api/tasks"

        session = async_get_clientsession(hass)
        try:
            async with session.post(url, json={"text": text}) as response:
                if response.status == 200:
                    _LOGGER.info(f"Added task: {text}")
                else:
                    _LOGGER.error(f"Failed to add task: {response.status}")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Error connecting to Aether: {e}")

    async def handle_complete_task(call: ServiceCall) -> None:
        """Handle complete task service call."""
        task_id = call.data.get("task_id", "")
        if not task_id:
            return

        host = config[DOMAIN][CONF_HOST]
        port = config[DOMAIN][CONF_PORT]
        url = f"http://{host}:{port}/api/tasks/{task_id}/done"

        session = async_get_clientsession(hass)
        try:
            async with session.post(url) as response:
                if response.status == 200:
                    _LOGGER.info(f"Completed task: {task_id}")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Error connecting to Aether: {e}")

    async def handle_set_energy(call: ServiceCall) -> None:
        """Handle set energy service call."""
        level = call.data.get("level", "good")

        host = config[DOMAIN][CONF_HOST]
        port = config[DOMAIN][CONF_PORT]
        url = f"http://{host}:{port}/api/energy"

        session = async_get_clientsession(hass)
        try:
            async with session.post(url, json={"level": level}) as response:
                if response.status == 200:
                    _LOGGER.info(f"Set energy: {level}")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Error connecting to Aether: {e}")

    async def handle_what_now(call: ServiceCall) -> None:
        """Handle what now service call."""
        minutes = call.data.get("minutes", 20)

        host = config[DOMAIN][CONF_HOST]
        port = config[DOMAIN][CONF_PORT]
        url = f"http://{host}:{port}/api/whatnow"

        session = async_get_clientsession(hass)
        try:
            async with session.post(url, json={"minutes": minutes}) as response:
                if response.status == 200:
                    data = await response.json()
                    # Fire event with recommendations
                    hass.bus.async_fire(
                        f"{DOMAIN}_recommendations",
                        {
                            "minutes": minutes,
                            "tasks": [t["task"]["title"] for t in data.get("tasks", [])[:3]],
                            "chores": [c["name"] for c in data.get("chores", [])[:3]],
                            "suggestion": data.get("suggestion", ""),
                        },
                    )
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Error connecting to Aether: {e}")

    async def handle_complete_chore(call: ServiceCall) -> None:
        """Handle complete chore service call."""
        chore_id = call.data.get("chore_id", "")
        if not chore_id:
            return

        host = config[DOMAIN][CONF_HOST]
        port = config[DOMAIN][CONF_PORT]
        url = f"http://{host}:{port}/api/chores/{chore_id}/done"

        session = async_get_clientsession(hass)
        try:
            async with session.post(url) as response:
                if response.status == 200:
                    _LOGGER.info(f"Completed chore: {chore_id}")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Error connecting to Aether: {e}")

    # Register all services
    hass.services.async_register(
        DOMAIN,
        "add_task",
        handle_add_task,
        schema=vol.Schema({vol.Required("text"): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        "complete_task",
        handle_complete_task,
        schema=vol.Schema({vol.Required("task_id"): cv.string}),
    )

    hass.services.async_register(
        DOMAIN,
        "set_energy",
        handle_set_energy,
        schema=vol.Schema(
            {vol.Required("level"): vol.In(["peak", "good", "low", "depleted"])}
        ),
    )

    hass.services.async_register(
        DOMAIN,
        "what_now",
        handle_what_now,
        schema=vol.Schema({vol.Optional("minutes", default=20): cv.positive_int}),
    )

    hass.services.async_register(
        DOMAIN,
        "complete_chore",
        handle_complete_chore,
        schema=vol.Schema({vol.Required("chore_id"): cv.string}),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aether from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
