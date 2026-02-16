# Terraform: API Gateway + Lambda (boas-vindas)

Região: **us-east-1**. Autenticação via arquivos `~/.aws/config` e `~/.aws/credentials`.

## Estrutura

```
terraform/
├── main.tf           # Provider + chamada dos módulos
├── variables.tf      # Variáveis (região, profile, projeto)
├── outputs.tf        # URL da API e da Lambda
├── versions.tf       # Terraform e providers
├── modules/
│   ├── lambda/       # Função Lambda (retorna 200 + mensagem)
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── src/
│   │       └── main.py
│   └── api_gateway/  # REST API + recurso /welcome
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── README.md
```

## Uso

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Com perfil específico:

```bash
terraform apply -var="aws_profile=meu_perfil"
```

Ou criar `terraform.tfvars`:

```hcl
aws_region  = "us-east-1"
aws_profile = "meu_perfil"
project_name = "welcome-api"
environment  = "dev"
```

Após o apply, o output `welcome_endpoint` mostra a URL do GET (ex.: `https://xxx.execute-api.us-east-1.amazonaws.com/dev/welcome`).
