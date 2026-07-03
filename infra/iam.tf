# Phase 0: the ping Lambda only needs to write logs. Phase 2 adds a scoped S3 policy here.

resource "aws_iam_role" "lambda_exec" {
  name = "${local.name}-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Least-privilege access to ONLY the wiki bucket.
resource "aws_iam_role_policy" "wiki_s3" {
  name = "${local.name}-wiki-s3"
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:GetObjectVersion"]
        Resource = "${aws_s3_bucket.wiki.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:ListBucketVersions"]
        Resource = aws_s3_bucket.wiki.arn
      },
    ]
  })
}
