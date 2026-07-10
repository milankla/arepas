# ---------------------------------------------------------------------------
# Cognito User Pool — Arepas authentication
# Three groups: admin > user > guest (guest is implicit / no-login)
# ---------------------------------------------------------------------------

resource "aws_cognito_user_pool" "main" {
  name = "arepas-${var.environment}"

  # Allow users to sign in with email
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  # Email verification
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Arepas — verify your email"
    email_message        = "Your Arepas verification code is {####}"
  }

  # Token lifetimes
  user_pool_add_ons {
    advanced_security_mode = "OFF"
  }
}

# ---------------------------------------------------------------------------
# Groups — admin and user only. Guest = no Cognito account / no JWT.
# ---------------------------------------------------------------------------
resource "aws_cognito_user_group" "admin" {
  name         = "admin"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Full access: inference + explore + training jobs"
  precedence   = 1  # lower = higher priority when a user belongs to multiple groups
}

resource "aws_cognito_user_group" "user" {
  name         = "user"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Inference + explore access"
  precedence   = 10
}

# ---------------------------------------------------------------------------
# App client — public SPA (no client secret; PKCE flow for the React app)
# ---------------------------------------------------------------------------
resource "aws_cognito_user_pool_client" "spa" {
  name         = "arepas-spa-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id

  # No client secret — standard for browser-based SPAs
  generate_secret = false

  # Token validity
  access_token_validity  = 1   # hours
  id_token_validity      = 1   # hours
  refresh_token_validity = 30  # days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Allowed OAuth flows — Authorization Code + PKCE (most secure for SPAs)
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["openid", "email", "profile"]

  # Callback / logout URLs.
  # Includes localhost for local dev. The CloudFront URL is added by
  # scripts/deploy_ui.sh after the first CloudFront apply, using:
  #   aws cognito-idp update-user-pool-client ...
  # Do NOT add a reference to aws_cloudfront_distribution here — it creates
  # a cycle through aws_apprunner_service.
  callback_urls = ["http://localhost:5173/callback"]
  logout_urls   = ["http://localhost:5173/logout"]

  # Explicit auth flows — needed for Amplify / Hosted UI
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  # Prevent accidental user existence enumeration
  prevent_user_existence_errors = "ENABLED"
}

# ---------------------------------------------------------------------------
# Hosted UI domain — <prefix>.auth.us-east-1.amazoncognito.com
# Required for the Cognito Hosted UI login page (used until Phase 4 custom UI)
# ---------------------------------------------------------------------------
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "arepas-${var.environment}-${local.account_id}"
  user_pool_id = aws_cognito_user_pool.main.id
}
