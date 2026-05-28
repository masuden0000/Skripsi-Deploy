/**
 * Centralized role-to-route mapping.
 * Values MUST match the `role` column in the `profiles` table.
 */
export const ROLE_ROUTES: Record<string, string> = {
  admin:    "/admin/periode",
  reviewer: "/reviewer",
}

export const VALID_ROLES = Object.keys(ROLE_ROUTES) as string[]
