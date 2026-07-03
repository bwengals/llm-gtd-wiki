# Phase 0: the MCP server Lambda exposing a single `ping` tool + the OAuth discovery/DCR shim.
# Build the zip first:  cd server && ./scripts/package.sh   (produces server/dist/lambda.zip)

locals {
  cognito_domain_url = "https://${aws_cognito_user_pool_domain.wiki.domain}.auth.${var.aws_region}.amazoncognito.com"
  lambda_zip         = "${path.module}/../server/dist/lambda.zip"
}

resource "aws_cloudwatch_log_group" "mcp" {
  name              = "/aws/lambda/${local.name}-mcp"
  retention_in_days = 14
}

resource "aws_lambda_function" "mcp" {
  function_name = "${local.name}-mcp"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "python3.12"
  handler       = "llm_gtd_wiki.app.handler"
  timeout       = 30
  memory_size   = 512

  filename         = local.lambda_zip
  source_code_hash = filebase64sha256(local.lambda_zip)

  environment {
    variables = {
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.wiki.id
      COGNITO_CLIENT_ID    = aws_cognito_user_pool_client.claude.id
      COGNITO_DOMAIN       = local.cognito_domain_url
      COGNITO_REGION       = var.aws_region
      # ALLOWED_SUBS empty => allow any authenticated user in this (single-user, admin-create) pool.
      ALLOWED_SUBS = ""
      WIKI_BUCKET  = aws_s3_bucket.wiki.id
    }
  }

  depends_on = [aws_cloudwatch_log_group.mcp]
}

# API Gateway HTTP API in front of the Lambda — used INSTEAD of a Lambda Function URL because
# Function URLs remap the `WWW-Authenticate` response header (to x-amzn-Remapped-WWW-Authenticate),
# which breaks the MCP/OAuth auth-discovery handshake. API Gateway passes headers through intact.
# Auth is enforced inside the app (bearer token on /mcp); the /.well-known/* + /register routes are
# public, which is why the API has no gateway-level authorizer.
resource "aws_apigatewayv2_api" "mcp" {
  name          = "${local.name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins  = ["https://claude.ai", "https://claude.com"]
    allow_methods  = ["GET", "POST", "OPTIONS"]
    allow_headers  = ["content-type", "authorization", "mcp-protocol-version", "mcp-session-id"]
    expose_headers = ["mcp-session-id", "www-authenticate"]
    max_age        = 3600
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.mcp.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.mcp.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.mcp.id
  route_key = "$default" # catch-all: routes /mcp, /.well-known/*, /register to the Lambda
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.mcp.id
  name        = "$default" # no stage prefix in the path
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mcp.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.mcp.execution_arn}/*/*"
}
