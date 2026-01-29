"""Home Assistant integration for context and triggers."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
import logging

import aiohttp

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """Client for Home Assistant REST API."""

    def __init__(self, url: str, token: str):
        """Initialize with HA URL and long-lived access token."""
        self.base_url = url.rstrip("/")
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
    ) -> dict[str, Any] | list | None:
        """Make HTTP request to Home Assistant."""
        url = f"{self.base_url}/api/{endpoint}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(
                    method,
                    url,
                    headers=self.headers,
                    json=data,
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 201:
                        return await response.json()
                    else:
                        text = await response.text()
                        logger.error(f"HA API error {response.status}: {text}")
                        return None
            except aiohttp.ClientError as e:
                logger.error(f"HA connection error: {e}")
                return None

    async def get_state(self, entity_id: str) -> dict[str, Any] | None:
        """Get state of an entity."""
        result = await self._request("GET", f"states/{entity_id}")
        return result if isinstance(result, dict) else None

    async def get_states(self) -> list[dict[str, Any]]:
        """Get all entity states."""
        result = await self._request("GET", "states")
        return result if isinstance(result, list) else []

    async def call_service(
        self,
        domain: str,
        service: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Call a Home Assistant service."""
        result = await self._request("POST", f"services/{domain}/{service}", data)
        return result is not None

    async def fire_event(
        self,
        event_type: str,
        event_data: dict[str, Any] | None = None,
    ) -> bool:
        """Fire a Home Assistant event."""
        result = await self._request("POST", f"events/{event_type}", event_data)
        return result is not None

    # Aether-specific methods

    async def get_context(self) -> dict[str, Any]:
        """Get context information from Home Assistant sensors."""
        context = {
            "timestamp": datetime.now().isoformat(),
            "presence": None,
            "location": None,
            "weather": None,
            "air_quality": None,
            "energy": None,
        }

        # Try to get presence
        presence = await self.get_state("person.me")  # Adjust entity_id
        if presence:
            context["presence"] = presence.get("state")

        # Try to get weather
        weather = await self.get_state("weather.home")  # Adjust entity_id
        if weather:
            context["weather"] = {
                "condition": weather.get("state"),
                "temperature": weather.get("attributes", {}).get("temperature"),
            }

        # Try to get air quality
        air = await self.get_state("sensor.air_quality_index")  # Adjust entity_id
        if air:
            context["air_quality"] = air.get("state")

        return context

    async def notify(
        self,
        message: str,
        title: str = "Aether",
        target: str | None = None,
    ) -> bool:
        """Send notification via Home Assistant."""
        data = {
            "message": message,
            "title": title,
        }
        if target:
            data["target"] = target

        return await self.call_service("notify", "notify", data)

    async def speak(
        self,
        message: str,
        media_player: str,
    ) -> bool:
        """Speak message via TTS on media player."""
        return await self.call_service(
            "tts",
            "speak",
            {
                "entity_id": media_player,
                "message": message,
            },
        )

    async def update_sensor(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
    ) -> bool:
        """Update a sensor state (for Aether sensors)."""
        data = {
            "state": state,
            "attributes": attributes or {},
        }
        result = await self._request("POST", f"states/{entity_id}", data)
        return result is not None

    # Aether sensor updates

    async def update_aether_sensors(
        self,
        tasks_due_today: int,
        overdue_count: int,
        next_event: str | None,
        chores_due: int,
        energy_level: str,
    ) -> None:
        """Update all Aether sensors in Home Assistant."""
        sensors = [
            ("sensor.aether_tasks_due_today", str(tasks_due_today), {
                "friendly_name": "Tasks Due Today",
                "icon": "mdi:checkbox-marked-outline",
            }),
            ("sensor.aether_overdue_count", str(overdue_count), {
                "friendly_name": "Overdue Tasks",
                "icon": "mdi:alert-circle",
            }),
            ("sensor.aether_next_event", next_event or "None", {
                "friendly_name": "Next Event",
                "icon": "mdi:calendar",
            }),
            ("sensor.aether_chores_due", str(chores_due), {
                "friendly_name": "Chores Due",
                "icon": "mdi:broom",
            }),
            ("sensor.aether_energy", energy_level, {
                "friendly_name": "Energy Level",
                "icon": "mdi:lightning-bolt",
            }),
        ]

        for entity_id, state, attributes in sensors:
            await self.update_sensor(entity_id, state, attributes)

    async def trigger_morning_briefing(self, briefing: dict[str, Any]) -> None:
        """Fire morning briefing event for HA automations."""
        await self.fire_event("aether_morning_briefing", {
            "tasks_due": briefing.get("summary", {}).get("due_today", 0),
            "overdue": briefing.get("summary", {}).get("overdue", 0),
            "events_count": len(briefing.get("events", [])),
            "warnings_count": len(briefing.get("warnings", [])),
        })

    async def check_for_alerts(self) -> list[dict[str, str]]:
        """Check HA for conditions that should trigger Aether alerts."""
        alerts = []

        # Check air quality
        air = await self.get_state("sensor.air_quality_index")
        if air and air.get("state"):
            try:
                aqi = int(float(air["state"]))
                if aqi > 100:
                    alerts.append({
                        "type": "air_quality",
                        "severity": "warning" if aqi < 150 else "critical",
                        "message": f"Air quality is poor (AQI: {aqi}). Consider staying indoors.",
                    })
            except ValueError:
                pass

        # Check energy usage
        energy = await self.get_state("sensor.energy_daily")
        if energy and energy.get("state"):
            try:
                kwh = float(energy["state"])
                avg = energy.get("attributes", {}).get("average", kwh)
                if kwh > avg * 1.5:
                    alerts.append({
                        "type": "energy",
                        "severity": "info",
                        "message": f"Energy usage is high today ({kwh:.1f} kWh vs {avg:.1f} avg).",
                    })
            except ValueError:
                pass

        return alerts


class HomeAssistantWebhook:
    """Webhook handler for receiving events from Home Assistant."""

    def __init__(self, callback):
        """Initialize with callback function for events."""
        self.callback = callback

    async def handle_webhook(self, data: dict[str, Any]) -> dict[str, str]:
        """Handle incoming webhook from Home Assistant."""
        event_type = data.get("event_type")
        event_data = data.get("event_data", {})

        if event_type == "aether_voice_command":
            # Voice command received
            text = event_data.get("text", "")
            await self.callback("voice_command", {"text": text})

        elif event_type == "aether_presence_change":
            # User arrived/left
            state = event_data.get("state")  # home, away, etc.
            await self.callback("presence_change", {"state": state})

        elif event_type == "aether_time_available":
            # User indicated available time
            minutes = event_data.get("minutes", 0)
            await self.callback("time_available", {"minutes": minutes})

        return {"status": "ok"}
