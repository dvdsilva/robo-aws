variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "environment" {
  description = "Nome do stage (dev, prod, etc.)"
  type        = string
}

variable "region" {
  description = "Região AWS (para o URI da integração Lambda)"
  type        = string
}

variable "lambda_arn" {
  description = "ARN da função Lambda"
  type        = string
}

variable "lambda_name" {
  description = "Nome da função Lambda"
  type        = string
}
