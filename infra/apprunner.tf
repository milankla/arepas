# ---------------------------------------------------------------------------
# App Runner service — Arepas API (FastAPI + uvicorn, always warm, min 1).
# ---------------------------------------------------------------------------

# IAM role that App Runner assumes to pull from ECR at deploy time.
resource "aws_iam_role" "apprunner_ecr_access" {
  name = "arepas-apprunner-ecr-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "build.apprunner.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# IAM role assumed by the running App Runner instance (reads S3 + SSM).
resource "aws_iam_role" "apprunner_instance" {
  name = "arepas-apprunner-instance-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "tasks.apprunner.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Attach the Phase-1 read policy (data + models buckets).
resource "aws_iam_role_policy_attachment" "apprunner_s3_read" {
  role       = aws_iam_role.apprunner_instance.name
  policy_arn = aws_iam_policy.lambda_read.arn  # from s3.tf; "lambda_read" = API read
}

# Allow instance to read SSM params (/arepas/…).
data "aws_iam_policy_document" "apprunner_ssm" {
  statement {
    effect    = "Allow"
    actions   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"]
    resources = ["arn:aws:ssm:${var.region}:${local.account_id}:parameter/arepas/*"]
  }
}

resource "aws_iam_policy" "apprunner_ssm" {
  name   = "arepas-apprunner-ssm-${var.environment}"
  policy = data.aws_iam_policy_document.apprunner_ssm.json
}

resource "aws_iam_role_policy_attachment" "apprunner_ssm" {
  role       = aws_iam_role.apprunner_instance.name
  policy_arn = aws_iam_policy.apprunner_ssm.arn
}

# ---------------------------------------------------------------------------
# App Runner service
# ---------------------------------------------------------------------------
resource "aws_apprunner_service" "api" {
  service_name = "arepas-api-${var.environment}"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    image_repository {
      image_identifier      = "${aws_ecr_repository.api.repository_url}:latest"
      image_repository_type = "ECR"

      image_configuration {
        port = "8080"

        runtime_environment_variables = {
          AREPAS_S3_BUCKET          = aws_s3_bucket.data.id
          AREPAS_S3_MODELS_BUCKET   = aws_s3_bucket.models.id
          AREPAS_COGNITO_USER_POOL_ID = aws_cognito_user_pool.main.id
          AREPAS_COGNITO_CLIENT_ID  = aws_cognito_user_pool_client.spa.id
          AREPAS_AUTH_MODE          = "cognito"
          PYTHONUNBUFFERED          = "1"
        }
      }
    }

    # Don't auto-deploy on every ECR push — deploy explicitly via the script.
    auto_deployments_enabled = false
  }

  instance_configuration {
    cpu    = "4096"   # 4 vCPU
    memory = "12288"  # 12 GB — fits B5 (434 MB) + GroundingDINO (172 MB) + overhead
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/api/checkpoints"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 3
  }
}

# SSM param — the App Runner service URL so other infra can reference it.
resource "aws_ssm_parameter" "apprunner_url" {
  name  = "/arepas/${var.environment}/api/url"
  type  = "String"
  value = "https://${aws_apprunner_service.api.service_url}"
}
