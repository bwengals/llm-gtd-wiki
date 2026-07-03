# The wiki store. One markdown object per file; versioning on for undo/rollback.

resource "aws_s3_bucket" "wiki" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_versioning" "wiki" {
  bucket = aws_s3_bucket.wiki.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "wiki" {
  bucket                  = aws_s3_bucket.wiki.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "wiki" {
  bucket = aws_s3_bucket.wiki.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "wiki" {
  bucket = aws_s3_bucket.wiki.id
  rule {
    id     = "expire-noncurrent"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_days
    }
  }
  depends_on = [aws_s3_bucket_versioning.wiki]
}

# Require TLS for all access.
resource "aws_s3_bucket_policy" "wiki_tls_only" {
  bucket = aws_s3_bucket.wiki.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.wiki.arn, "${aws_s3_bucket.wiki.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.wiki]
}
