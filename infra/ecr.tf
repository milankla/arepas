# ---------------------------------------------------------------------------
# ECR private repository for the Arepas API container image.
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "api" {
  name                 = "arepas-api-${var.environment}"
  image_tag_mutability = "MUTABLE"  # allows re-pushing :latest

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Keep only the 5 most recent images — the rest are stale builds.
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}
