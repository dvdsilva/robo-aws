provider "aws" {
  region = var.aws_region

  # Usa o arquivo de config/credenciais (~/.aws/config e ~/.aws/credentials)
  shared_config_files     = ["~/.aws/config"]
  shared_credentials_files = ["~/.aws/credentials"]
  profile                 = var.aws_profile
}

# ---------------------------------------------------------------------------
# Módulo Lambda
# ---------------------------------------------------------------------------
module "lambda" {
  source = "./modules/lambda"

  project_name = var.project_name
  environment  = var.environment
}

# ---------------------------------------------------------------------------
# Módulo API Gateway
# ---------------------------------------------------------------------------
module "api_gateway" {
  source = "./modules/api_gateway"

  project_name = var.project_name
  environment  = var.environment
  region       = var.aws_region
  lambda_arn   = module.lambda.function_arn
  lambda_name  = module.lambda.function_name
}
