output "connector_url" {
  description = "Paste this into the Claude app as the custom-connector URL."
  value       = "${aws_apigatewayv2_api.mcp.api_endpoint}/mcp"
}

output "function_base_url" {
  description = "Base URL of the API (the OAuth shim advertises itself under this)."
  value       = aws_apigatewayv2_api.mcp.api_endpoint
}

output "cognito_hosted_ui" {
  description = "Cognito hosted-UI base URL (authorize/token live here)."
  value       = local.cognito_domain_url
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.wiki.id
}

output "cognito_client_id" {
  value = aws_cognito_user_pool_client.claude.id
}

output "owner_email" {
  description = "The user Cognito created; check this inbox for the temporary password."
  value       = var.owner_email
}
