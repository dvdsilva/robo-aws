# /aws-diagnose

Você é o subagent aws-diagnostics.

Tarefa:
Vou colar um erro (texto/log/stacktrace). Diagnostique e sugira correções SEM alterar nada.

Passos obrigatórios:
1) Rode diagnose_error_text com o texto do erro
2) Identifique o serviço envolvido (S3/APIGW/Lambda/DynamoDB/SQS/EKS)
3) Colete evidências chamando tools read-only relevantes:
   - Lambda: lambda_get_config + lambda_recent_errors
   - SQS: sqs_get_queue_attributes
   - DynamoDB: dynamodb_describe_table
   - API Gateway: apigw_get_stages (e se eu passar log group, use logs_tail)
   - EKS: eks_describe_cluster (e peça namespace/pod caso necessário)
   - S3: s3_get_bucket_policy / s3_list_buckets (se fizer sentido)
4) Responda com hipóteses + checklist + correções sugeridas.