"""Sensor platform for Aether."""
from __future__ import annotations

from datetime import timedelta
import logging

import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict | None = None,
) -> None:
    """Set up the Aether sensors."""
    if DOMAIN not in hass.data or "config" not in hass.data[DOMAIN]:
        return

    conf = hass.data[DOMAIN]["config"]
    host = conf[CONF_HOST]
    port = conf[CONF_PORT]

    coordinator = AetherDataCoordinator(hass, host, port)
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        AetherTasksDueTodaySensor(coordinator),
        AetherOverdueSensor(coordinator),
        AetherChoresDueSensor(coordinator),
        AetherEnergySensor(coordinator),
        AetherNextEventSensor(coordinator),
    ]

    async_add_entities(sensors)


class AetherDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Aether data."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialize."""
        self.host = host
        self.port = port
        self.session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from Aether API."""
        data = {
            "tasks_due_today": 0,
            "overdue": 0,
            "chores_due": 0,
            "energy": "good",
            "next_event": None,
        }

        try:
            # Get status
            url = f"http://{self.host}:{self.port}/api/status"
            async with self.session.get(url) as response:
                if response.status == 200:
                    status = await response.json()
                    data["overdue"] = status.get("overdue_count", 0)
                    data["energy"] = status.get("energy", "good")

            # Get briefing for more data
            url = f"http://{self.host}:{self.port}/api/briefing"
            async with self.session.get(url) as response:
                if response.status == 200:
                    briefing = await response.json()
                    summary = briefing.get("summary", {})
                    data["tasks_due_today"] = summary.get("due_today", 0)

                    events = briefing.get("events", [])
                    if events:
                        data["next_event"] = events[0].get("title")

            # Get chores
            url = f"http://{self.host}:{self.port}/api/chores/stats"
            async with self.session.get(url) as response:
                if response.status == 200:
                    stats = await response.json()
                    data["chores_due"] = stats.get("due_now", 0)

        except aiohttp.ClientError as e:
            _LOGGER.warning(f"Error fetching Aether data: {e}")

        return data


class AetherBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Aether sensors."""

    def __init__(self, coordinator: AetherDataCoordinator, key: str, name: str, icon: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"aether_{key}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)


class AetherTasksDueTodaySensor(AetherBaseSensor):
    """Sensor for tasks due today."""

    def __init__(self, coordinator: AetherDataCoordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            "tasks_due_today",
            "Aether Tasks Due Today",
            "mdi:checkbox-marked-outline",
        )


class AetherOverdueSensor(AetherBaseSensor):
    """Sensor for overdue tasks."""

    def __init__(self, coordinator: AetherDataCoordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            "overdue",
            "Aether Overdue Tasks",
            "mdi:alert-circle",
        )


class AetherChoresDueSensor(AetherBaseSensor):
    """Sensor for chores due."""

    def __init__(self, coordinator: AetherDataCoordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            "chores_due",
            "Aether Chores Due",
            "mdi:broom",
        )


class AetherEnergySensor(AetherBaseSensor):
    """Sensor for energy level."""

    def __init__(self, coordinator: AetherDataCoordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            "energy",
            "Aether Energy Level",
            "mdi:lightning-bolt",
        )


class AetherNextEventSensor(AetherBaseSensor):
    """Sensor for next event."""

    def __init__(self, coordinator: AetherDataCoordinator) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            "next_event",
            "Aether Next Event",
            "mdi:calendar",
        )
