from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import func, select

from app.api import permissions
from app.api.deps import SessionDep, require_roles
from app.models import MetricsSummary, User, UserRole

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "/summary",
    dependencies=[Depends(require_roles(*permissions.VIEW_METRICS))],
    response_model=MetricsSummary,
)
def read_metrics_summary(session: SessionDep) -> Any:
    """
    User count metrics.
    """
    total_users = session.exec(select(func.count()).select_from(User)).one()
    active_users = session.exec(
        select(func.count()).select_from(User).where(User.is_active)
    ).one()
    users_by_role = {
        role: session.exec(
            select(func.count()).select_from(User).where(User.role == role)
        ).one()
        for role in UserRole
    }
    return MetricsSummary(
        total_users=total_users,
        active_users=active_users,
        users_by_role=users_by_role,
    )
