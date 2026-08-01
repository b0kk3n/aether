"""App settings API routes."""

from fastapi import APIRouter

from aether.core import (
    AppSettings,
    AppSettingsUpdate,
    AppSettingsService,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettings)
def get_settings():
    """Get app-wide settings."""
    return AppSettingsService.get()


@router.put("", response_model=AppSettings)
def update_settings(update: AppSettingsUpdate):
    """Update app-wide settings."""
    return AppSettingsService.update(update)
