from fastapi import APIRouter

from app.api.routes import (
    app_settings,
    items,
    login,
    metrics,
    private,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(metrics.router)
api_router.include_router(app_settings.router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
