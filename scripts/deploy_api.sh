#!/usr/bin/env bash
# Build and push the Arepas API container image to ECR, then trigger an
# App Runner deployment.
#
# Usage (from project root):
#   scripts/deploy_api.sh
#
# Prerequisites:
#   - Docker Desktop running
#   - AWS_PROFILE=arepas (or credentials in env)
#   - terraform apply already run (ECR + App Runner exist)
set -euo pipefail

cd "$(dirname "$0")/.."

REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/arepas-api-prod"
SERVICE_ARN=$(aws apprunner list-services --region "$REGION" \
  --query "ServiceSummaryList[?ServiceName=='arepas-api-prod'].ServiceArn" \
  --output text)

echo "=== Building image (linux/amd64) ==="
docker buildx build --platform linux/amd64 -t arepas-api:latest .

echo "=== Authenticating to ECR ==="
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "=== Tagging and pushing ==="
docker tag arepas-api:latest "${ECR_REPO}:latest"
docker push "${ECR_REPO}:latest"

echo "=== Triggering App Runner deployment ==="
aws apprunner start-deployment \
  --service-arn "$SERVICE_ARN" \
  --region "$REGION"

echo ""
echo "Deployment started. Monitor at:"
echo "  https://console.aws.amazon.com/apprunner/home?region=${REGION}"
echo ""
APP_URL=$(aws apprunner describe-service \
  --service-arn "$SERVICE_ARN" --region "$REGION" \
  --query "Service.ServiceUrl" --output text)
echo "Service URL: https://${APP_URL}"
