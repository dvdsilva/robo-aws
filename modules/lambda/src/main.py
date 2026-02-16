"""
Lambda que retorna HTTP 200 e mensagem de boas-vindas.
Integração com API Gateway (proxy).
"""

def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/plain",
            "Access-Control-Allow-Origin": "*"
        },
        "body": "mensagem de bem vindo ao a web"
    }
