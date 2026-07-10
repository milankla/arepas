variable "region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI named profile used by Terraform. Must match ~/.aws/credentials."
  type        = string
  default     = "arepas"
}

variable "environment" {
  description = "Deployment environment tag (prod | dev)."
  type        = string
  default     = "prod"
}

variable "model_versioning_enabled" {
  description = "Enable S3 versioning on the models bucket (recommended: checkpoints are expensive to reproduce)."
  type        = bool
  default     = true
}
