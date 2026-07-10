/**
 * Cognito OIDC configuration for react-oidc-context.
 *
 * Values are read from Vite env vars so the same build can target local dev
 * (no auth) and the deployed CloudFront+App Runner stack (Cognito live).
 *
 * Local dev: leave all VITE_COGNITO_* unset → AuthProvider wraps the app
 * but auth is effectively disabled (no login prompt, all pages accessible).
 *
 * Deployed:  set in vite.config.ts define block at build time (from Terraform
 * outputs) so they are baked into the static bundle.
 */
import type { AuthProviderProps } from "react-oidc-context";

const POOL_ID = import.meta.env.VITE_COGNITO_USER_POOL_ID as string | undefined;
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID as string | undefined;
const DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN as string | undefined;

/** True when Cognito credentials are configured (deployed env). */
export const AUTH_ENABLED = Boolean(POOL_ID && CLIENT_ID && DOMAIN);

const region = POOL_ID?.split("_")[0] ?? "us-east-1";

export const oidcConfig: AuthProviderProps = {
  authority: AUTH_ENABLED
    ? `https://cognito-idp.${region}.amazonaws.com/${POOL_ID}`
    : "https://example.com", // placeholder — never used when AUTH_ENABLED=false
  client_id: CLIENT_ID ?? "placeholder",
  redirect_uri: `${window.location.origin}/callback`,
  post_logout_redirect_uri: window.location.origin,
  response_type: "code",
  scope: "openid email profile",
  // Cognito Hosted UI endpoint for login/logout
  metadata: AUTH_ENABLED
    ? {
        issuer: `https://cognito-idp.${region}.amazonaws.com/${POOL_ID}`,
        authorization_endpoint: `${DOMAIN}/oauth2/authorize`,
        token_endpoint: `${DOMAIN}/oauth2/token`,
        userinfo_endpoint: `${DOMAIN}/oauth2/userInfo`,
        end_session_endpoint: `${DOMAIN}/logout`,
        jwks_uri: `https://cognito-idp.${region}.amazonaws.com/${POOL_ID}/.well-known/jwks.json`,
      }
    : undefined,
  onSigninCallback: () => {
    // Remove the OIDC code+state from the URL after redirect without a full reload.
    window.history.replaceState({}, document.title, window.location.pathname);
  },
};
