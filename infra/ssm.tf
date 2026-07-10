# SSM Parameter Store — bucket names so Lambda/SageMaker code reads config
# from the environment rather than having it hardcoded.
# Standard tier is free for < 10,000 params.

resource "aws_ssm_parameter" "data_bucket" {
  name  = "/arepas/${var.environment}/s3/data-bucket"
  type  = "String"
  value = aws_s3_bucket.data.id
}

resource "aws_ssm_parameter" "models_bucket" {
  name  = "/arepas/${var.environment}/s3/models-bucket"
  type  = "String"
  value = aws_s3_bucket.models.id
}

resource "aws_ssm_parameter" "cognito_user_pool_id" {
  name  = "/arepas/${var.environment}/cognito/user-pool-id"
  type  = "String"
  value = aws_cognito_user_pool.main.id
}

resource "aws_ssm_parameter" "cognito_client_id" {
  name  = "/arepas/${var.environment}/cognito/client-id"
  type  = "String"
  value = aws_cognito_user_pool_client.spa.id
}
