# NOTES — deliberate scope cuts and known seams

Decisions made consciously to keep the change set focused; each is cheap to revisit.

## Backend

- **`is_superuser` retained but not authoritative.** The RBAC surface only consults
  `role`. `get_current_active_superuser` still guards two out-of-scope template routes
  (`POST /utils/test-email/` and `POST /login/password-recovery-html-content/{email}`);
  migrating them to `require_roles` would touch template code the task doesn't cover.
- **`UserUpdate` still exposes `is_superuser`.** An admin could set `is_superuser`
  and `role` inconsistently. Harmless today (nothing on the RBAC surface reads
  `is_superuser`), but the field should be dropped when the template compatibility
  constraint goes away.
- **`/settings` is an in-memory stub.** `GET/PUT /settings/` demonstrate the
  admin-only guard; values reset on restart and are process-local. Persistence was
  explicitly out of scope.
- **`/metrics/summary` counts with one query per role.** Three trivial COUNT queries;
  a grouped query is not worth the typing friction at this size.

## Frontend

- **No role editing in Add/Edit user forms.** The backend supports
  `PATCH /users/{id}` with `role`; wiring it into the admin UI forms was cut to keep
  the frontend diff minimal. Roles are visible in the users table.
- **`requireCapability` fetches `/users/me` per guarded navigation** instead of
  reading the React Query cache — one extra small request on entering a guarded
  route, in exchange for keeping the guard self-contained.
- **No Playwright/e2e coverage.** Frontend verification is lint + typecheck + build;
  authorization itself is covered by the backend test matrix.
