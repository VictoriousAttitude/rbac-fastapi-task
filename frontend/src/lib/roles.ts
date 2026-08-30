// UX-only mirror of the backend permission mapping
// (backend/app/api/permissions.py). The backend is authoritative.
import type { UserRole } from "@/client"

export const canListUsers = (role?: UserRole) =>
  role === "admin" || role === "manager"

export const canManageUsers = (role?: UserRole) => role === "admin"

export const canViewMetrics = canListUsers
