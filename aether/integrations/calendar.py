"""Google Calendar integration."""

from datetime import datetime, timedelta
from typing import Any
import logging

logger = logging.getLogger(__name__)


class CalendarSync:
    """Sync with Google Calendar."""

    def __init__(self, credentials_file: str | None = None):
        """Initialize calendar sync.

        Args:
            credentials_file: Path to Google OAuth credentials JSON.
        """
        self.credentials_file = credentials_file
        self._service = None

    def _get_service(self):
        """Get or create Google Calendar service."""
        if self._service:
            return self._service

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import os.path
            import pickle

            SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
            creds = None
            token_path = self.credentials_file.replace(".json", "_token.pickle")

            if os.path.exists(token_path):
                with open(token_path, "rb") as token:
                    creds = pickle.load(token)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                with open(token_path, "wb") as token:
                    pickle.dump(creds, token)

            self._service = build("calendar", "v3", credentials=creds)
            return self._service

        except ImportError:
            logger.warning("Google Calendar libraries not installed. Install with: pip install aether[google]")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar: {e}")
            return None

    def get_events(
        self,
        calendar_id: str = "primary",
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """Get events from Google Calendar."""
        service = self._get_service()
        if not service:
            return []

        if not time_min:
            time_min = datetime.now()
        if not time_max:
            time_max = time_min + timedelta(days=7)

        try:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat() + "Z",
                timeMax=time_max.isoformat() + "Z",
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = events_result.get("items", [])
            return [self._parse_event(e) for e in events]

        except Exception as e:
            logger.error(f"Failed to fetch calendar events: {e}")
            return []

    def _parse_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Parse Google Calendar event into Aether format."""
        start = event.get("start", {})
        end = event.get("end", {})

        # Handle all-day vs timed events
        if "dateTime" in start:
            start_dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
            all_day = False
        else:
            start_dt = datetime.strptime(start.get("date", ""), "%Y-%m-%d")
            all_day = True

        if "dateTime" in end:
            end_dt = datetime.fromisoformat(end["dateTime"].replace("Z", "+00:00"))
        else:
            end_dt = datetime.strptime(end.get("date", ""), "%Y-%m-%d")

        return {
            "id": event.get("id"),
            "title": event.get("summary", "No Title"),
            "description": event.get("description", ""),
            "start": start_dt,
            "end": end_dt,
            "all_day": all_day,
            "location": event.get("location"),
            "attendees": [
                a.get("email") for a in event.get("attendees", [])
            ],
            "status": event.get("status"),
            "link": event.get("htmlLink"),
            "source": "google_calendar",
        }

    def get_todays_events(self, calendar_id: str = "primary") -> list[dict[str, Any]]:
        """Get today's events."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        return self.get_events(calendar_id, today_start, today_end)

    def get_upcoming(
        self,
        calendar_id: str = "primary",
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Get upcoming events in the next N hours."""
        now = datetime.now()
        end = now + timedelta(hours=hours)
        return self.get_events(calendar_id, now, end)

    def get_birthdays(
        self,
        days_ahead: int = 7,
    ) -> list[dict[str, Any]]:
        """Get upcoming birthdays (from contacts birthday calendar)."""
        # Google has a special calendar for birthdays
        birthday_calendar = "addressbook#contacts@group.v.calendar.google.com"
        now = datetime.now()
        end = now + timedelta(days=days_ahead)
        return self.get_events(birthday_calendar, now, end)


class CalendarEventMatcher:
    """Match calendar events with tasks for prep reminders."""

    def __init__(self, calendar: CalendarSync):
        """Initialize with calendar sync."""
        self.calendar = calendar

    def find_events_needing_prep(
        self,
        hours_ahead: int = 24,
        keywords: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Find events that might need preparation.

        Keywords to look for: meeting, call, interview, presentation, etc.
        """
        if keywords is None:
            keywords = [
                "meeting", "call", "interview", "presentation",
                "review", "demo", "standup", "sync", "1:1", "one on one",
            ]

        events = self.calendar.get_upcoming(hours=hours_ahead)
        events_needing_prep = []

        for event in events:
            title_lower = event["title"].lower()
            if any(kw in title_lower for kw in keywords):
                # Estimate prep time based on event type
                prep_minutes = self._estimate_prep_time(event)
                event["prep_minutes"] = prep_minutes
                events_needing_prep.append(event)

        return events_needing_prep

    def _estimate_prep_time(self, event: dict[str, Any]) -> int:
        """Estimate preparation time for an event."""
        title_lower = event["title"].lower()

        if "interview" in title_lower:
            return 30
        if "presentation" in title_lower or "demo" in title_lower:
            return 45
        if "review" in title_lower:
            return 20
        if "1:1" in title_lower or "one on one" in title_lower:
            return 10

        # Default: 15 minutes for meetings
        return 15

    def get_next_event_with_prep(self) -> dict[str, Any] | None:
        """Get the next event that needs prep."""
        events = self.find_events_needing_prep(hours_ahead=12)
        if events:
            return events[0]
        return None
