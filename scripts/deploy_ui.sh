#!/usr/bin/env bash
# Build the React UI and deploy it to S3 + CloudFront.
#
# Usage (from project root):
#   scripts/deploy_ui.sh
#
# Prerequisites:
#   - Node.js + npm installed
#   - AWS_PROFILE=arepas (or credentials in env)
#   - terraform apply already run (S3 bucket + CloudFront exist)
set -euo pipefail

cd "$(dirname "$0")/.."
INFRA_DIR="infra"

echo "=== Reading deployment config from Terraform outputs ==="
BUCKET=$(cd "$INFRA_DIR" && terraform output -raw frontend_bucket_name)
CF_ID=$(cd "$INFRA_DIR" && terraform output -raw cloudfront_distribution_id)
CF_URL=$(cd "$INFRA_DIR" && terraform output -raw cloudfront_url)

# Cognito values baked into the build at compile time.
POOL_ID=$(cd "$INFRA_DIR" && terraform output -raw cognito_user_pool_id)
CLIENT_ID=$(cd "$INFRA_DIR" && terraform output -raw cognito_client_id)
COGNITO_DOMAIN=$(cd "$INFRA_DIR" && terraform output -raw cognito_hosted_ui_domain)

echo "=== Updating Cognito callback URLs to include CloudFront ==="
POOL_CLIENT_ID=$(cd "$INFRA_DIR" && terraform output -raw cognito_client_id)
# Cognito requires re-supplying ALL existing settings on update — fetch them first.
EXISTING=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id "$POOL_ID" --client-id "$POOL_CLIENT_ID" \
  --region us-east-1 --query "UserPoolClient" --output json)
# Build updated URL lists (deduplicated)
CB_URLS=$(echo "$EXISTING" | python3 -c "
import json,sys
c=json.load(sys.stdin)
urls=list(set(c.get('CallbackURLs',[])+['${CF_URL}/callback']))
print(' '.join(urls))")
LO_URLS=$(echo "$EXISTING" | python3 -c "
import json,sys
c=json.load(sys.stdin)
urls=list(set(c.get('LogoutURLs',[])+['${CF_URL}/logout']))
print(' '.join(urls))")
aws cognito-idp update-user-pool-client \
  --user-pool-id "$POOL_ID" --client-id "$POOL_CLIENT_ID" \
  --region us-east-1 \
  --allowed-o-auth-flows code \
  --allowed-o-auth-flows-user-pool-client \
  --allowed-o-auth-scopes openid email profile \
  --callback-urls $CB_URLS \
  --logout-urls $LO_URLS \
  --supported-identity-providers COGNITO \
  > /dev/null && echo "  Cognito callback URLs updated."

echo "=== Building React app ==="
cd src/ui
VITE_COGNITO_USER_POOL_ID="$POOL_ID" \
VITE_COGNITO_CLIENT_ID="$CLIENT_ID" \
VITE_COGNITO_DOMAIN="$COGNITO_DOMAIN" \
  npm run build

echo "=== Syncing to S3 ==="
cd ../..
# Long-lived cache for hashed assets, no-cache for index.html
aws s3 sync src/ui/dist/ "s3://${BUCKET}/" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html"
aws s3 cp src/ui/dist/index.html "s3://${BUCKET}/index.html" \
  --cache-control "no-cache, no-store, must-revalidate"

echo "=== Invalidating CloudFront cache ==="
aws cloudfront create-invalidation \
  --distribution-id "$CF_ID" \
  --paths "/*" \
  --query "Invalidation.Id" --output text

echo ""
echo "Deployed to: ${CF_URL}"
