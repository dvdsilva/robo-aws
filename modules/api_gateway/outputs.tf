output "rest_api_id" {
  description = "ID do REST API"
  value       = aws_api_gateway_rest_api.this.id
}

output "invoke_url" {
  description = "URL base de invocação do API (sem path)"
  value       = aws_api_gateway_stage.this.invoke_url
}

output "stage_name" {
  description = "Nome do stage"
  value       = aws_api_gateway_stage.this.stage_name
}

output "welcome_url" {
  description = "URL do endpoint GET /welcome"
  value       = "${aws_api_gateway_stage.this.invoke_url}/welcome"
}
