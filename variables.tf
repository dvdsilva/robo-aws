variable "aws_region" {
  description = "Região AWS (ex.: us-east-1)"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Perfil do arquivo ~/.aws/config para autenticação"
  type        = string
  default     = null
}

variable "project_name" {
  description = "Nome do projeto (prefixo dos recursos)"
  type        = string
  default     = "welcome-api"
}

variable "environment" {
  description = "Ambiente (ex.: dev, prod)"
  type        = string
  default     = "dev"
}
