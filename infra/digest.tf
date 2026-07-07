# Daily task-digest email: a Lambda that reads the wiki from S3 and sends a digest via SES, on an
# EventBridge (Scheduler) daily trigger. The recipient email must be a verified SES identity
# (run: aws ses verify-email-identity --email-address <you> --region <region>, then click the link).

resource "aws_cloudwatch_log_group" "digest" {
  name              = "/aws/lambda/${local.name}-digest"
  retention_in_days = 14
}

resource "aws_lambda_function" "digest" {
  function_name = "${local.name}-digest"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "python3.12"
  handler       = "llm_gtd_wiki.digest.handler"
  timeout       = 30
  memory_size   = 256

  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)

  environment {
    variables = {
      WIKI_BUCKET    = aws_s3_bucket.wiki.id
      DIGEST_TO      = var.digest_email
      DIGEST_FROM    = var.digest_email
      COGNITO_REGION = var.aws_region
    }
  }

  depends_on = [aws_cloudwatch_log_group.digest]
}

# Let the shared exec role send email via SES.
resource "aws_iam_role_policy" "digest_ses" {
  name = "${local.name}-digest-ses"
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ses:SendEmail", "ses:SendRawEmail"]
      Resource = "*"
    }]
  })
}

# --- 8:30am daily schedule (America/Los_Angeles → DST-correct). Disabled until the test passes. ---
resource "aws_iam_role" "scheduler" {
  name = "${local.name}-scheduler"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  name = "${local.name}-scheduler-invoke"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.digest.arn
    }]
  })
}

resource "aws_scheduler_schedule" "digest" {
  name = "${local.name}-digest-830"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(30 8 * * ? *)"
  schedule_expression_timezone = "America/Los_Angeles"
  state                        = var.digest_schedule_enabled ? "ENABLED" : "DISABLED"

  target {
    arn      = aws_lambda_function.digest.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}
