# ---------------------------------------------------------------------------
# Frontend hosting: S3 (static build) + CloudFront (single distribution,
# two origins so /api/* routes to App Runner without CORS).
# ---------------------------------------------------------------------------
locals {
  frontend_bucket = "arepas-frontend-${local.account_id}"
}

# ---------------------------------------------------------------------------
# S3 bucket — private; served exclusively through CloudFront OAC.
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "frontend" {
  bucket = local.frontend_bucket
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

# ---------------------------------------------------------------------------
# CloudFront Origin Access Control — lets CloudFront pull from the private
# S3 bucket without making the bucket public.
# ---------------------------------------------------------------------------
resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "arepas-frontend-oac-${var.environment}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ---------------------------------------------------------------------------
# S3 bucket policy — allow CloudFront OAC to read objects.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "frontend_s3_oac" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.frontend.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.frontend_s3_oac.json
}

# ---------------------------------------------------------------------------
# CloudFront distribution — two origins:
#   1. S3 (default)  — serves the React SPA (index.html + assets)
#   2. App Runner    — proxies /api/* so there is no cross-origin at all
# ---------------------------------------------------------------------------
resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"   # US + EU edge nodes only
  comment             = "Arepas frontend + API proxy (${var.environment})"

  # Origin 1: S3 (React build)
  origin {
    origin_id                = "s3-frontend"
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  # Origin 2: App Runner (FastAPI)
  origin {
    origin_id   = "apprunner-api"
    domain_name = aws_apprunner_service.api.service_url
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Behaviour: /api/* → App Runner, no caching, forward Authorization header
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    target_origin_id = "apprunner-api"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    compress         = true

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type"]
      cookies { forward = "none" }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }

  # Default behaviour: S3 → React SPA, cached aggressively for assets
  default_cache_behavior {
    target_origin_id       = "s3-frontend"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # SPA routing: 403/404 from S3 → return index.html (200) so React Router works
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }
  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true  # use the *.cloudfront.net cert; no custom domain
  }
}

# ---------------------------------------------------------------------------
# SSM — CloudFront domain so Cognito callback URLs can be wired in 4c.
# ---------------------------------------------------------------------------
resource "aws_ssm_parameter" "cloudfront_url" {
  name  = "/arepas/${var.environment}/frontend/url"
  type  = "String"
  value = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}
