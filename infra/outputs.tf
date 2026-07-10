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

output "cognito_user_pool_id" {
  description = "Set as AREPAS_COGNITO_USER_POOL_ID in the Lambda environment."
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_arn" {
  value = aws_cognito_user_pool.main.arn
}

output "cognito_client_id" {
  description = "SPA app client ID — used by the React frontend."
  value       = aws_cognito_user_pool_client.spa.id
}

output "cognito_hosted_ui_domain" {
  description = "Hosted UI base URL for the login page."
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.region}.amazoncognito.com"
}
