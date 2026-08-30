from typing import Any

from fastapi import APIRouter, Depends

from app.api import permissions
from app.api.deps import require_roles
from app.models import GlobalSettings

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(require_roles(*permissions.MANAGE_SETTINGS))],
)

# Stub: settings are kept in memory and reset on restart (see NOTES.md)
_global_settings = GlobalSettings(app_name="Full Stack FastAPI", maintenance_mode=False)


@router.get("/", response_model=GlobalSettings)
def read_global_settings() -> Any:
    """
    Global application settings.
    """
    return _global_settings


@router.put("/", response_model=GlobalSettings)
def update_global_settings(settings_in: GlobalSettings) -> Any:
    """
    Replace global application settings.
    """
    global _global_settings
    _global_settings = settings_in
    return _global_settings
