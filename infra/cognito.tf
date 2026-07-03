# Cognito user pool = the OAuth 2.1 authorization server backing the Claude connector.
# Single-user by design: admin-create only, no self-signup.

resource "aws_cognito_user_pool" "wiki" {
  name = "${local.name}-pool"

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  # MFA optional here; recommend turning it on for a real deployment.
  mfa_configuration = "OFF"

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = true
  }

  username_attributes = ["email"]
}

resource "aws_cognito_user_pool_domain" "wiki" {
  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.wiki.id
}

# Resource server defines the custom scope the MCP server checks for on access tokens.
resource "aws_cognito_resource_server" "wiki" {
  identifier   = "wiki"
  name         = "${local.name}-resource-server"
  user_pool_id = aws_cognito_user_pool.wiki.id

  scope {
    scope_name        = "readwrite"
    scope_description = "Read/write the GTD wiki"
  }
}

# Public client (no secret) using authorization-code + PKCE — what a native/first-party app like
# Claude uses. The MCP OAuth shim (server/oauth_shim.py) hands this client_id back on DCR /register.
resource "aws_cognito_user_pool_client" "claude" {
  name         = "${local.name}-claude-client"
  user_pool_id = aws_cognito_user_pool.wiki.id

  generate_secret = false

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes = [
    "openid",
    "email",
    aws_cognito_resource_server.wiki.scope_identifiers[0], # "wiki/readwrite"
  ]
  supported_identity_providers = ["COGNITO"]

  callback_urls = var.claude_redirect_uris

  # Refresh so the connector doesn't force re-login constantly.
  explicit_auth_flows = ["ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_SRP_AUTH"]

  access_token_validity  = 1  # hours
  id_token_validity      = 1  # hours
  refresh_token_validity = 30 # days
  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}

# The single owner user. Cognito emails a temporary password on create.
resource "aws_cognito_user" "owner" {
  user_pool_id = aws_cognito_user_pool.wiki.id
  username     = var.owner_email
  attributes = {
    email          = var.owner_email
    email_verified = "true"
  }
}
