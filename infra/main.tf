provider "aws" {
  region = var.aws_region
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  name = var.name_prefix
  # Base URL of the Lambda Function URL, without the trailing slash. Computed from the function URL
  # after creation and injected back into the Lambda env so the OAuth shim can advertise itself.
  # (Terraform resolves this via the aws_lambda_function_url resource in lambda.tf.)
}
