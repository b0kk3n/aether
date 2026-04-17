"""Sensor platform for Aether."""
from __future__ import annotations

from datetime import timedelta
import logging

import aiohttp

from homeassistant.components.sensor import SensorEntity
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
    coordinator = AetherDataCoordinator(hass, conf[CONF_HOST], conf[CONF_PORT])
    await coordinator.async_refresh()

    async_add_entities([
        AetherOverdueSensor(coordinator),
        AetherChoresDueSensor(coordinator),
    ])


class AetherDataCoordinator(DataUpdateCoordinator):
    """Fetches data from the Aether dashboard API."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.session = async_get_clientsession(hass)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self) -> dict:
        data = {"total_overdue": 0, "chores_due_soon": 0}
        try:
            url = f"http://{self.host}:{self.port}/api/dashboard"
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    dashboard = await resp.json()
                    data["total_overdue"] = dashboard.get("total_overdue", 0)
                    data["chores_due_soon"] = dashboard.get("chores_due_soon", 0)
        except aiohttp.ClientError as exc:
            _LOGGER.warning("Could not reach Aether: %s", exc)
        return data


class _AetherSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: AetherDataCoordinator, key: str, name: str, icon: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"aether_{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)


class AetherOverdueSensor(_AetherSensor):
    def __init__(self, coordinator: AetherDataCoordinator) -> None:
        super().__init__(coordinator, "total_overdue", "Aether Overdue Chores", "mdi:alert-circle")


class AetherChoresDueSensor(_AetherSensor):
    def __init__(self, coordinator: AetherDataCoordinator) -> None:
        super().__init__(coordinator, "chores_due_soon", "Aether Chores Due Soon", "mdi:broom")
