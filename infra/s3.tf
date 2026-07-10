# ---------------------------------------------------------------------------
# Bucket name locals — derived from account ID, no extra tfvar needed.
# ---------------------------------------------------------------------------
locals {
  account_id    = data.aws_caller_identity.current.account_id
  data_bucket   = "arepas-data-${local.account_id}"
  models_bucket = "arepas-models-${local.account_id}"
}

# ---------------------------------------------------------------------------
# arepas-data — photos (data/, data2/, data3/) + crops/
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "data" {
  bucket = local.data_bucket
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ---------------------------------------------------------------------------
# arepas-models — outputs/ (checkpoints, training_history.json, run_config.json)
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "models" {
  bucket = local.models_bucket
}

resource "aws_s3_bucket_public_access_block" "models" {
  bucket = aws_s3_bucket.models.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id

  versioning_configuration {
    status = var.model_versioning_enabled ? "Enabled" : "Suspended"
  }
}

# ---------------------------------------------------------------------------
# IAM policy documents — not attached yet; Lambda (Phase 3) and SageMaker
# (Phase 5) roles will reference these ARNs.
# ---------------------------------------------------------------------------

# Lambda read: photos + models (inference)
data "aws_iam_policy_document" "lambda_read" {
  statement {
    sid    = "ReadData"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.data.arn,
      "${aws_s3_bucket.data.arn}/*",
      aws_s3_bucket.models.arn,
      "${aws_s3_bucket.models.arn}/*",
    ]
  }
}

resource "aws_iam_policy" "lambda_read" {
  name        = "arepas-lambda-read-${var.environment}"
  description = "Lambda: read photos + model checkpoints from S3."
  policy      = data.aws_iam_policy_document.lambda_read.json
}

# SageMaker training: read photos, read+write models
data "aws_iam_policy_document" "sagemaker_training" {
  statement {
    sid     = "ReadPhotos"
    effect  = "Allow"
    actions = ["s3:GetObject", "s3:ListBucket"]
    resources = [
      aws_s3_bucket.data.arn,
      "${aws_s3_bucket.data.arn}/*",
    ]
  }

  statement {
    sid    = "ReadWriteModels"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.models.arn,
      "${aws_s3_bucket.models.arn}/*",
    ]
  }
}

resource "aws_iam_policy" "sagemaker_training" {
  name        = "arepas-sagemaker-training-${var.environment}"
  description = "SageMaker training jobs: read photos, read+write model checkpoints."
  policy      = data.aws_iam_policy_document.sagemaker_training.json
}
