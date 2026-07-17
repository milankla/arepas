import { useAuth } from "react-oidc-context";
import { AUTH_ENABLED } from "@/auth/config";

export type UserRole = "admin" | "user" | "anonymous";

/**
 * Returns the effective role of the current user.
 *
 * - "anonymous"  AUTH_ENABLED and not signed in (or AUTH_ENABLED=false in local dev)
 * - "admin"      signed in and member of the "admin" Cognito group
 * - "user"       signed in but NOT in the "admin" group
 *
 * Cognito writes group membership into the ID token as "cognito:groups".
 */
export function useUserRole(): UserRole {
  const auth = useAuth();

  // Local dev (AUTH_ENABLED=false): no Cognito config present, treat as admin
  // so all pages are accessible during development.
  if (!AUTH_ENABLED) return "admin";

  if (!auth.isAuthenticated) return "anonymous";

  const groups =
    (auth.user?.profile?.["cognito:groups"] as string[] | undefined) ?? [];

  return groups.includes("admin") ? "admin" : "user";
}
