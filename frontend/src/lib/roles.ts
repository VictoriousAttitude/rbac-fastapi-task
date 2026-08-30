// UX-only mirror of the backend permission mapping
// (backend/app/api/permissions.py). The backend is authoritative.
import { redirect } from "@tanstack/react-router"
import { type UserRole, UsersService } from "@/client"

export const canListUsers = (role?: UserRole) =>
  role === "admin" || role === "manager"

export const canManageUsers = (role?: UserRole) => role === "admin"

export const canViewMetrics = (role?: UserRole) =>
  role === "admin" || role === "manager"

// Shared beforeLoad guard: unauthenticated -> login, wrong role -> forbidden
export async function requireCapability(
  can: (role?: UserRole) => boolean,
): Promise<void> {
  let role: UserRole | undefined
  try {
    role = (await UsersService.readUserMe()).data.role
  } catch {
    throw redirect({ to: "/login" })
  }
  if (!can(role)) {
    throw redirect({ to: "/forbidden" })
  }
}
