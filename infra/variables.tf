variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-west-2"
}

variable "name_prefix" {
  description = "Prefix for resource names (keep it globally-unique-ish for the Cognito domain)."
  type        = string
  default     = "llm-gtd-wiki"
}

variable "cognito_domain_prefix" {
  description = "Globally-unique prefix for the Cognito hosted-UI domain (<prefix>.auth.<region>.amazoncognito.com)."
  type        = string
}

variable "owner_email" {
  description = "Email of the single owner user created in the Cognito pool."
  type        = string
}

variable "claude_redirect_uris" {
  description = <<-EOT
    OAuth callback URL(s) the hosted Claude apps (web/desktop/mobile) use for custom connectors.
    Confirmed via Anthropic docs (2026): https://claude.ai/api/mcp/auth_callback. (Claude Code's
    native client instead uses an ephemeral loopback http://localhost/callback — add that only if
    you also want to connect from Claude Code.)
  EOT
  type        = list(string)
  default = [
    "https://claude.ai/api/mcp/auth_callback",
  ]
}

variable "bucket_name" {
  description = "S3 bucket that stores the wiki (globally unique)."
  type        = string
}

variable "noncurrent_version_days" {
  description = "Days to retain noncurrent object versions before expiring them."
  type        = number
  default     = 90
}
