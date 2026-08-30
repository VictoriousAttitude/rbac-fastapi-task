# ADR 001: Single role enum column as the source of truth

Status: accepted

## Context

The template ships with a boolean `is_superuser` flag and a `get_current_active_superuser`
dependency. The task requires three roles (admin, manager, member) with distinct
permissions, and the design must make adding a role cheap and keep authorization
gap-free.

Options considered:

1. **Single `role` enum column on `User`** (chosen)
2. Separate `Role`/`UserRole` tables (many-to-many)
3. Permission strings per user (ACL-style)

## Decision

Add `role: UserRole` (Postgres enum `admin | manager | member`, server default
`member`) to the `user` table. `role` is the sole source of truth for authorization.

- Central mapping in `app/api/permissions.py`: each protected capability is a tuple of
  allowed roles (`LIST_USERS`, `MANAGE_USERS`, `READ_ANY_USER`, `VIEW_METRICS`,
  `MANAGE_SETTINGS`).
- One dependency factory `require_roles(*roles)` in `app/api/deps.py` guards routes
  declaratively; `ensure_role()` handles the one conditional case (self-read of
  `GET /users/{id}`). No role literals in route bodies.
- Adding a role touches at most three files: `models.py` (enum member), a migration,
  and `permissions.py` (grant capabilities).
- Migration backfills `is_superuser=true → role=admin` and creates/drops the Postgres
  enum explicitly for a clean round-trip.

`is_superuser` is retained but no longer consulted on the RBAC surface — it stays only
for template compatibility (see NOTES.md for the remaining seams).

## Consequences

- Role checks are O(1) tuple membership; no joins, no extra queries.
- Exactly one role per user — sufficient for this hierarchy; a role table would be
  gold-plating at this scale and can be introduced later behind the same
  `require_roles` seam.
- 401 (missing/invalid credentials) and 403 (authenticated but forbidden) are strictly
  separated, and every denial is logged with user id and route.
- `UserUpdateMe`/`UserRegister` deliberately exclude `role`, so members cannot
  escalate themselves; only admins (via `UserUpdate`) can change roles.
