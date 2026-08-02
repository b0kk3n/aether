"""App settings service - a singleton settings blob (currently just a household name)."""

from aether.core.models import AppSettings, AppSettingsUpdate
from aether.core.database import get_db


class AppSettingsService:
    """Service for app-wide settings."""

    @staticmethod
    def get() -> AppSettings:
        """Get current app settings."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT household_name FROM app_settings WHERE id = 1"
            ).fetchone()

        return AppSettings(household_name=row["household_name"] if row else None)

    @staticmethod
    def update(update: AppSettingsUpdate) -> AppSettings:
        """Update app settings. household_name may be set to None to clear it."""
        with get_db() as conn:
            conn.execute(
                "UPDATE app_settings SET household_name = ? WHERE id = 1",
                (update.household_name,),
            )

        return AppSettingsService.get()
