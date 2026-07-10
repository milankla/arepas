output "data_bucket_name" {
  description = "S3 bucket for photos and crops (set as AREPAS_S3_BUCKET)."
  value       = aws_s3_bucket.data.id
}

output "models_bucket_name" {
  description = "S3 bucket for model checkpoints and run metadata (set as AREPAS_S3_MODELS_BUCKET)."
  value       = aws_s3_bucket.models.id
}

output "data_bucket_arn" {
  value = aws_s3_bucket.data.arn
}

output "models_bucket_arn" {
  value = aws_s3_bucket.models.arn
}

output "lambda_read_policy_arn" {
  description = "Attach to the Lambda execution role in Phase 3."
  value       = aws_iam_policy.lambda_read.arn
}

output "sagemaker_training_policy_arn" {
  description = "Attach to the SageMaker execution role in Phase 5."
  value       = aws_iam_policy.sagemaker_training.arn
}
