# ADR 002: Frontend capability checks are UX only

Status: accepted

## Context

The frontend needs to hide navigation and actions the user's role cannot perform, and
direct navigation to a forbidden route must show a friendly page. The backend already
enforces everything; the question is how role awareness reaches the UI.

Options considered:

1. **Mirror the permission mapping as capability helpers** (chosen)
2. Backend-served capability list per user (e.g. `/users/me/capabilities`)
3. Scatter `role === "admin"` literals through components

## Decision

`frontend/src/lib/roles.ts` mirrors `backend/app/api/permissions.py` as small
capability helpers (`canListUsers`, `canManageUsers`, `canViewMetrics`) over the
`UserRole` type generated from the OpenAPI schema. The backend remains authoritative —
these checks are UX only.

- Route guards use TanStack Router `beforeLoad` via a shared `requireCapability()`
  helper: unauthenticated → `/login`, wrong role → `/forbidden`.
- Nav links render only when the capability check passes; `/admin` is visible to
  managers with write actions (add user, row actions) hidden.
- Global error handling distinguishes 401 (drop token, redirect to login) from 403
  (friendly forbidden page for queries, toast for mutations) — a 403 must never
  destroy a valid session.

A server-provided capability list was rejected as gold-plating for three roles: the
generated `UserRole` type already keeps the mirror honest at compile time, and any
drift fails safe because the backend still returns 403.

## Consequences

- One file to update when the matrix changes; no role literals in components.
- A user whose role changes mid-session may briefly see stale UI until the profile
  refetches; the backend 403 path covers the gap.
- No e2e tests for the guards (out of scope) — verification is lint/typecheck/build
  plus the backend test matrix.
