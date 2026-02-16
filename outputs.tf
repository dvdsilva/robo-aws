output "api_gateway_url" {
  description = "URL base do API Gateway (invoke URL)"
  value       = module.api_gateway.invoke_url
}

output "api_gateway_stage_name" {
  description = "Nome do stage do API Gateway"
  value       = module.api_gateway.stage_name
}

output "lambda_function_name" {
  description = "Nome da função Lambda"
  value       = module.lambda.function_name
}

output "welcome_endpoint" {
  description = "URL do endpoint de boas-vindas (GET)"
  value       = "${module.api_gateway.invoke_url}/welcome"
}
