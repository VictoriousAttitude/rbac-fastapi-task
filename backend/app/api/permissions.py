"""Central role -> permission mapping.

Single source of truth for which roles may perform which actions.
Routes reference these constants via `require_roles` / `ensure_role`
and must never hardcode role literals.
"""

from app.models import UserRole

LIST_USERS = (UserRole.admin, UserRole.manager)
MANAGE_USERS = (UserRole.admin,)
READ_ANY_USER = (UserRole.admin, UserRole.manager)
VIEW_METRICS = (UserRole.admin, UserRole.manager)
MANAGE_SETTINGS = (UserRole.admin,)
