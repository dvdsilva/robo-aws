# Permissão para o API Gateway invocar a Lambda
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.this.execution_arn}/*/*"
}

# REST API
resource "aws_api_gateway_rest_api" "this" {
  name        = "${var.project_name}-${var.environment}"
  description = "API de boas-vindas (Lambda)"
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# Método GET na raiz (/) — evita "Missing Authentication Token" ao acessar a URL base
resource "aws_api_gateway_method" "get_root" {
  rest_api_id   = aws_api_gateway_rest_api.this.id
  resource_id   = aws_api_gateway_rest_api.this.root_resource_id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "root_mock" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  resource_id = aws_api_gateway_rest_api.this.root_resource_id
  http_method = aws_api_gateway_method.get_root.http_method

  type                    = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "root_200" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  resource_id = aws_api_gateway_rest_api.this.root_resource_id
  http_method = aws_api_gateway_method.get_root.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "root_200" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  resource_id = aws_api_gateway_rest_api.this.root_resource_id
  http_method = aws_api_gateway_method.get_root.http_method
  status_code = aws_api_gateway_method_response.root_200.status_code

  response_templates = {
    "application/json" = "{\"message\": \"API de boas-vindas\", \"endpoint\": \"GET /welcome\", \"hint\": \"Acesse /welcome para o endpoint de boas-vindas\"}"
  }
}

# Recurso /welcome
resource "aws_api_gateway_resource" "welcome" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_rest_api.this.root_resource_id
  path_part   = "welcome"
}

# Método GET em /welcome
resource "aws_api_gateway_method" "get_welcome" {
  rest_api_id   = aws_api_gateway_rest_api.this.id
  resource_id   = aws_api_gateway_resource.welcome.id
  http_method   = "GET"
  authorization = "NONE"
  request_parameters = {}
}

# Integração Lambda (proxy: resposta inteira vem da Lambda)
resource "aws_api_gateway_integration" "lambda" {
  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_resource.welcome.id
  http_method             = aws_api_gateway_method.get_welcome.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${var.region}:lambda:path/2015-03-31/functions/${var.lambda_arn}/invocations"
  depends_on              = [aws_lambda_permission.api_gateway]
}

# Deployment
resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  depends_on = [
    aws_api_gateway_integration.lambda,
    aws_api_gateway_integration.root_mock,
    aws_api_gateway_integration_response.root_200
  ]
  lifecycle {
    create_before_destroy = true
  }
}

# Stage (stage_name foi removido de aws_api_gateway_deployment no provider 5.x)
resource "aws_api_gateway_stage" "this" {
  deployment_id = aws_api_gateway_deployment.this.id
  rest_api_id   = aws_api_gateway_rest_api.this.id
  stage_name    = var.environment
}
