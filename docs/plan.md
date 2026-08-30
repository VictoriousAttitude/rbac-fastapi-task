# RBAC Implementation Plan

> **For agentic workers:** executed inline in this session (superpowers:executing-plans), TDD per milestone, one conventional commit per milestone, `uv run prek run --all-files` green before every commit.

**Goal:** Role-based access control (admin / manager / member) enforced in the backend via one dependency factory, mirrored as UX-only guards in the frontend.

**Architecture:** Single `role` enum column on `User` (source of truth; `is_superuser` kept for template compatibility). One `require_roles(*roles)` dependency in `app/api/deps.py`; central action→roles mapping in `app/api/permissions.py`; routes never contain role literals. Frontend reads `role` from `UserPublic` and mirrors the mapping in `src/lib/roles.ts`.

**Tech stack:** FastAPI, SQLModel, Alembic, PostgreSQL enum; React + TanStack Router; openapi-ts generated client.

## Global constraints

- 401 = missing/invalid credentials; 403 = authenticated but not permitted. Never mix.
- Every denial: `logger.warning` with user id + route.
- No inline role literals in route bodies; adding a role touches ≤3 files (enum, permissions map, migration).
- Tests: parametrized role×endpoint, allowed AND denied cases, plus 401 unauthenticated. Few and sharp.
- Frontend verified by lint/typecheck/build only (no e2e).

## Permission matrix (single source: `app/api/permissions.py`)

| Action | Constant | admin | manager | member |
|---|---|---|---|---|
| List users `GET /users/` | `LIST_USERS` | ✓ | ✓ | ✗ |
| Create user `POST /users/` | `MANAGE_USERS` | ✓ | ✗ | ✗ |
| Update/delete any user `PATCH/DELETE /users/{id}` | `MANAGE_USERS` | ✓ | ✗ | ✗ |
| Read other user `GET /users/{id}` | `READ_ANY_USER` | ✓ | ✓ | self only |
| Metrics `GET /metrics/summary` | `VIEW_METRICS` | ✓ | ✓ | ✗ |
| Global settings `GET/PUT /settings/` | `MANAGE_SETTINGS` | ✓ | ✗ | ✗ |
| Own profile `GET/PATCH /users/me` | (authenticated) | ✓ | ✓ | ✓ |
| `POST /users/signup` | public; always assigns `member` | — | — | — |

---

## Milestone 1 — `feat: add role column to user model with migration`

**Files:** modify `backend/app/models.py`, `backend/app/core/db.py`; create `backend/app/alembic/versions/<rev>_add_role_to_user.py` (down_revision `fe56fa70289e`).

- `models.py`: add

  ```python
  class UserRole(str, enum.Enum):
      admin = "admin"      # lowercase members so SQLAlchemy's name-based
      manager = "manager"  # enum storage matches the value
      member = "member"
  ```

  `UserBase` gains `role: UserRole = Field(default=UserRole.member)` (flows to `UserCreate` — admin endpoint — and `UserPublic` — frontend). `UserUpdate` gains `role: UserRole | None = None`. `UserRegister` and `UserUpdateMe` unchanged → no self-escalation path.
- `core/db.py` `init_db`: first superuser gets `role=UserRole.admin`.
- Migration (`uv run alembic revision -m "add role to user"`, then fill):

  ```python
  def upgrade():
      user_role = sa.Enum("admin", "manager", "member", name="userrole")
      user_role.create(op.get_bind())
      op.add_column("user", sa.Column("role", user_role, nullable=False,
                                      server_default="member"))
      op.execute("""UPDATE "user" SET role = 'admin' WHERE is_superuser = true""")

  def downgrade():
      op.drop_column("user", "role")
      sa.Enum(name="userrole").drop(op.get_bind())
  ```
- Verify: `uv run alembic upgrade head`, run test suite (still green), `uv run alembic downgrade -1 && uv run alembic upgrade head` round-trip. Commit.

## Milestone 2 — `feat: enforce role-based authorization on user routes`

**Files:** create `backend/app/api/permissions.py`; modify `backend/app/api/deps.py`, `backend/app/api/routes/users.py`. Failing tests from Milestone 3 are written FIRST (kept uncommitted until M3), shown red, then this milestone makes them green.

- `permissions.py`:

  ```python
  from app.models import UserRole

  LIST_USERS = (UserRole.admin, UserRole.manager)
  MANAGE_USERS = (UserRole.admin,)
  READ_ANY_USER = (UserRole.admin, UserRole.manager)
  VIEW_METRICS = (UserRole.admin, UserRole.manager)
  MANAGE_SETTINGS = (UserRole.admin,)
  ```
- `deps.py`: `logger = logging.getLogger(__name__)`; invalid-JWT branch in `get_current_user` becomes **401** with `headers={"WWW-Authenticate": "Bearer"}` (was 403); add:

  ```python
  def ensure_role(user: User, allowed: tuple[UserRole, ...], route: str) -> None:
      if user.role not in allowed:
          logger.warning("Access denied: user=%s role=%s route=%s",
                         user.id, user.role.value, route)
          raise HTTPException(status_code=403,
                              detail="The user doesn't have enough privileges")

  def require_roles(*allowed: UserRole) -> Callable[..., User]:
      def check_role(current_user: CurrentUser, request: Request) -> User:
          ensure_role(current_user, allowed, request.url.path)
          return current_user
      return check_role
  ```
- `users.py`: swap `Depends(get_current_active_superuser)` → `Depends(require_roles(*permissions.LIST_USERS))` on `read_users`; `MANAGE_USERS` on `create_user`, `update_user`, `delete_user`. `read_user_by_id`: self OR `ensure_role(current_user, permissions.READ_ANY_USER, request.url.path)`. Self-delete guards (`users.py:137`, `users.py:224`) switch `is_superuser` → `role == UserRole.admin` (role is source of truth), messages unchanged. `get_current_active_superuser` stays for out-of-surface routes (utils test-email, private) — NOTES.md.
- Verify: new tests green, full suite green. Commit (implementation only).

## Milestone 3 — `test: role-based authorization matrix`

**Files:** create `backend/tests/api/routes/test_rbac.py`; modify `backend/tests/conftest.py`, `backend/tests/utils/user.py`. (Written during M2 TDD; committed here.)

- `tests/utils/user.py`: `authentication_token_from_email(..., role: UserRole = UserRole.member)` — create user with that role, or update existing user's password AND role.
- `conftest.py`: add module-scoped `manager_token_headers` (email `manager@example.com`, `role=UserRole.manager`).
- `test_rbac.py` — fixture map `{"admin": "superuser_token_headers", "manager": "manager_token_headers", "member": "normal_user_token_headers"}`; tests:
  1. `test_role_matrix` — parametrized over (method, path, body, role, expected): `GET /users/` (admin 200, manager 200, member 403), `POST /users/` with random email/password (admin 200, manager 403, member 403), `GET /users/{other_id}` (manager 200, member 403).
  2. `test_protected_endpoint_without_token_returns_401`
  3. `test_invalid_token_returns_401` (garbage bearer token)
  4. `test_member_can_read_and_update_own_profile` (`GET /users/me`, `PATCH /users/me` → 200)
  5. `test_member_cannot_escalate_own_role` (`PATCH /users/me` with `"role": "admin"` in body → role stays `member`)
  6. `test_signup_assigns_member_role`
- Verify red→green already shown in M2; full suite green. Commit tests.

## Milestone 4 — `feat: add metrics summary and global settings stub endpoints`

**Files:** create `backend/app/api/routes/metrics.py`, `backend/app/api/routes/app_settings.py`; modify `backend/app/models.py` (add `MetricsSummary`, `GlobalSettings`), `backend/app/api/main.py`, `backend/tests/api/routes/test_rbac.py` (matrix rows for the new endpoints, written first, shown red).

- `metrics.py`: `GET /metrics/summary`, `dependencies=[Depends(require_roles(*permissions.VIEW_METRICS))]`, returns `MetricsSummary(total_users, active_users, users_by_role)` via `func.count` queries.
- `app_settings.py`: module named to avoid clashing with `core.config.settings`; `GET /settings/` + `PUT /settings/` guarded by `MANAGE_SETTINGS`; in-memory module-level `GlobalSettings(app_name=..., maintenance_mode=False)` store — stub, not persisted (NOTES.md).
- Matrix rows: metrics (admin 200, manager 200, member 403); settings GET+PUT (admin 200, manager 403, member 403).
- Verify red → implement → green. Commit.

## Milestone 5 — `feat: role-aware frontend guards, nav, and metrics page`

**Files:** regenerate `frontend/src/client/`; create `frontend/src/lib/roles.ts`, `frontend/src/routes/_layout/forbidden.tsx`, `frontend/src/routes/_layout/metrics.tsx`; modify `frontend/src/routes/_layout/admin.tsx`, `frontend/src/components/Sidebar/AppSidebar.tsx`, `frontend/src/components/Admin/columns.tsx` (Role column shows `role` badge; actions column filtered out for non-admin via component), admin route component (AddUser only for admin).

- `bash scripts/generate-client.sh` from repo root; confirm `UserPublic.role` exists.
- `roles.ts` mirrors backend mapping (UX only — backend authoritative):

  ```ts
  import type { UserPublic } from "@/client"
  export type Role = UserPublic["role"]
  export const canListUsers = (role?: Role) => role === "admin" || role === "manager"
  export const canManageUsers = (role?: Role) => role === "admin"
  export const canViewMetrics = canListUsers
  ```
- Guards (admin.tsx pattern): `beforeLoad` fetches `readUserMe`, `throw redirect({ to: "/forbidden" })` when not allowed. `/admin` → `canListUsers`; `/metrics` → `canViewMetrics`.
- `forbidden.tsx`: friendly "Access denied" page with a link home.
- Sidebar: Metrics link when `canViewMetrics`, Users link when `canListUsers` (replaces `is_superuser` check).
- `/admin` for manager: AddUser button and row-actions column render only when `canManageUsers`.
- `/metrics`: fetch `GET /metrics/summary` via generated service, render the three counts.
- Verify: `bun run lint`, typecheck, `bun run build` in frontend (exact script names from package.json). Commit.

## Milestone 6 — `docs: RBAC documentation`

**Files:** modify `README.md`; create `docs/adr/001-role-model-and-enforcement.md`, `docs/adr/002-frontend-capability-propagation.md`, `NOTES.md`.

- README: RBAC section — setup that works first try (compose up, prestart, fastapi dev, seed: prestart creates admin `FIRST_SUPERUSER`; non-admin via `/signup`; manager via admin `POST /users/` curl example), permission matrix table, 2–4 paragraph approach, how to run tests, mermaid authz-flow diagram (client → OAuth2 bearer → `get_current_user` 401s → `require_roles` 403s → route).
- ADR-1: enum column + dependency factory vs policy engine (and vs role table). ADR-2: role in `UserPublic` → generated client → `roles.ts` guards; UX-only.
- NOTES.md: scope cuts — no role-edit UI in Add/EditUser forms (API only), settings stub in-memory, `get_current_active_superuser` left on out-of-surface routes, no e2e.
- Commit.

## Verification (after M6)

Full backend suite + manual curl per role (admin/manager/member/no-token) against `GET /users/`, `GET /metrics/summary`, `GET /settings/` showing 200/403/401 as per matrix; app boots. Then PR.
