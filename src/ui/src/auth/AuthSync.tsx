/**
 * AuthSync — keeps the API client's token in sync with the OIDC session.
 *
 * Renders nothing; just runs an effect whenever the auth state changes.
 * Must be rendered inside AuthProvider.
 */
import { useEffect } from "react";
import { useAuth } from "react-oidc-context";
import { setAuthToken } from "@/api/client";

export function AuthSync() {
  const auth = useAuth();
  useEffect(() => {
    // id_token satisfies audience=client_id validation on the API.
    setAuthToken(auth.user?.id_token ?? null);
  }, [auth.user]);
  return null;
}
