/**
 * RequireAuth — route guard for explore/training pages.
 *
 * When Cognito is configured (deployed):
 *   - Authenticated → renders children.
 *   - Unauthenticated → shows a login prompt instead of the page.
 *
 * When Cognito is NOT configured (local dev):
 *   - Always renders children (auth is disabled).
 */
import { Box, Button, Typography } from "@mui/material";
import { useAuth } from "react-oidc-context";
import { AUTH_ENABLED } from "@/auth/config";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const auth = useAuth();

  if (!AUTH_ENABLED) return <>{children}</>;
  if (auth.isLoading) return null;

  if (!auth.isAuthenticated) {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "60vh",
          gap: 2,
        }}
      >
        <Typography variant="h6" color="text.secondary">
          Sign in to explore datasets and training runs.
        </Typography>
        <Button
          variant="contained"
          onClick={() => auth.signinRedirect()}
        >
          Sign in
        </Button>
      </Box>
    );
  }

  return <>{children}</>;
}
