"""
MCP Server (Cursor) - AWS Diagnostics (READ-ONLY)

Objetivo:
- Ler configurações/estado e logs (CloudWatch Logs) para diagnosticar erros.
- Sugerir correções SEM alterar recursos.

Integração:
- Cursor chama estas tools via MCP (stdio).
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from mcp.server.fastmcp import FastMCP  # padrão "FastMCP" para tools
from pydantic import BaseModel, Field


# -----------------------------
# MCP bootstrap
# -----------------------------
mcp = FastMCP("aws-diagnostics-readonly")


# -----------------------------
# Helpers: sessão AWS
# -----------------------------
def _aws_session(profile: Optional[str] = None, region: Optional[str] = None) -> boto3.Session:
    """
    Cria uma sessão boto3.
    - profile: usa AWS_PROFILE
    - region: usa AWS_REGION/AWS_DEFAULT_REGION
    """
    profile = profile or os.getenv("AWS_PROFILE")
    region = region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "sa-east-1"

    # Config para melhorar debug/robustez sem efeitos colaterais
    cfg = Config(
        region_name=region,
        retries={"max_attempts": 8, "mode": "standard"},
        user_agent_extra="cursor-mcp-aws-diagnostics"
    )

    if profile:
        return boto3.Session(profile_name=profile, region_name=region), cfg
    return boto3.Session(region_name=region), cfg


def _client(service: str, profile: Optional[str] = None, region: Optional[str] = None):
    sess, cfg = _aws_session(profile, region)
    return sess.client(service, config=cfg)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# -----------------------------
# Models (inputs bem definidos ajudam o Agent a usar certo)
# -----------------------------
class AwsContext(BaseModel):
    profile: Optional[str] = Field(default=None, description="AWS profile (opcional). Se omitido, usa AWS_PROFILE.")
    region: Optional[str] = Field(default=None, description="AWS region (opcional). Se omitido, usa AWS_REGION/AWS_DEFAULT_REGION.")


class LogQuery(BaseModel):
    log_group: str
    minutes: int = Field(default=30, ge=1, le=1440, description="Janela de tempo para buscar logs.")
    filter_pattern: Optional[str] = Field(default=None, description="Filter pattern do CloudWatch Logs (opcional).")
    limit: int = Field(default=50, ge=1, le=200)


# -----------------------------
# Tool: identidade / sanity check
# -----------------------------
@mcp.tool()
def sts_whoami(ctx: AwsContext = AwsContext()) -> Dict[str, Any]:
    """Retorna a identidade atual (account/arn/userId). Útil para validar credenciais e conta."""
    c = _client("sts", ctx.profile, ctx.region)
    return c.get_caller_identity()


# -----------------------------
# S3 (READ-ONLY)
# -----------------------------
@mcp.tool()
def s3_list_buckets(ctx: AwsContext = AwsContext()) -> Dict[str, Any]:
    """Lista buckets (nome + criação)."""
    c = _client("s3", ctx.profile, ctx.region)
    resp = c.list_buckets()
    buckets = [
        {"Name": b["Name"], "CreationDate": b["CreationDate"].isoformat()}
        for b in resp.get("Buckets", [])
    ]
    return {"Buckets": buckets}


@mcp.tool()
def s3_get_bucket_policy(bucket: str, ctx: AwsContext = AwsContext()) -> Dict[str, Any]:
    """Lê a policy de um bucket (se existir)."""
    c = _client("s3", ctx.profile, ctx.region)
    try:
        resp = c.get_bucket_policy(Bucket=bucket)
        return {"Bucket": bucket, "Policy": resp.get("Policy")}
    except ClientError as e:
        return {"Bucket": bucket, "Error": str(e)}


# -----------------------------
# CloudWatch Logs (READ-ONLY) - usado por Lambda e API Gateway logs
# -----------------------------
@mcp.tool()
def logs_tail(ctx_query: LogQuery, ctx: AwsContext = AwsContext()) -> Dict[str, Any]:
    """
    Busca eventos recentes em um log group.
    Observação: não altera nada; apenas leitura.
    """
    c = _client("logs", ctx.profile, ctx.region)

    end = _now_utc()
    start = end - timedelta(minutes=ctx_query.minutes)

    kwargs: Dict[str, Any] = {
        "logGroupName": ctx_query.log_group,
        "startTime": int(start.timestamp() * 1000),
        "endTime": int(end.timestamp() * 1000),
        "limit": ctx_query.limit,
    }
    if ctx_query.filter_pattern:
        kwargs["filterPattern"] = ctx_query.filter_pattern

    resp = c.filter_log_events(**kwargs)
    events = [
        {
            "timestamp": e.get("timestamp"),
            "message": e.get("message"),
            "logStreamName": e.get("logStreamName"),
        }
        for e in resp.get("events", [])
    ]
    return {"logGroup": ctx_query.log_group, "start": start.isoformat(), "end": end.isoformat(), "events": events}


# -----------------------------
# Lambda (READ-ONLY)
# -----------------------------
@mcp.tool()
def lambda_get_config(function_name: str, ctx: AwsContext = AwsContext()) -> Dict[str, Any]:
    """Lê configuração da Lambda (runtime, handler, env keys, timeout, memory, role)."""
    c = _client("lambda", ctx.profile, ctx.region)
    try:
        resp = c.get_function_configuration(FunctionName=function_name)
        # Remova env values por segurança; mantenha apenas as chaves
        env = resp.get("Environment", {}).get("Variables", {})
        resp["Environment"] = {"VariableKeys": sorted(list(env.keys()))}
        return resp
    except ClientError as e:
        return {"FunctionName": function_name, "Error": str(e)}


@mcp.tool()
def lambda_recent_errors(function_name: str, minutes: int = 30, ctx: AwsContext = AwsContext()) -> Dict[str, Any]:
    """
    Busca erros recentes no log group padrão da Lambda: /aws/lambda/<function_name>
    """
    log_group = f"/aws/lambda/{function_name}"
    # Padrões comuns: ERROR, Task timed out, Exception, etc.
    filter_pattern = '?ERROR ?Exception ?Task ?timed out ?timedout'
    return logs_tail(LogQuery(log_group=log_group, minutes=minutes, filter_pattern=filter_pattern, limit=80), ctx)


# -----------------------------
# API Gateway (READ-ONLY) - metadados (logs geralmente estão no CloudWatch)
# -----------------------------
@mcp.tool()
def apigw_list_rest_apis(ctx: AwsContext = AwsContext(), limit: int = 50) -> Dict[str, Any]:
    """Lista REST APIs (API Gateway v1)."""
    c = _client("apigateway", ctx.profile, ctx.region)
    resp = c.get_rest_apis(limit=limit)
    items = [{"id": x["id"], "name": x.get("name"), "createdDate": x.get("createdDate").isoformat()} for x in resp.get("items", [])]
    return {"items": items}


@mcp.tool()
def apigw_get_stages(rest_api_id: str, ctx: AwsContext = AwsContext()) -> Dict[str, Any]:
    """Lista stages de uma REST API."""
    c = _client("apigateway", ctx.profile, ctx.region)
    try:
        resp = c.get_stages(restApiId=rest_api_id)
        return resp
    except ClientError as e:
        return {"restApiId": rest_api_id, "Error": str(e)}


# -----------------------------
# DynamoDB (READ-ONLY)
# -----------------------------
@mcp.tool()
def dynamodb_describe_table(table_name: str, ctx: AwsContext = AwsContext()) -> Dict[str, Any]:
    """Descreve tabela (chaves, billing mode, GSIs, status)."""
    c = _client("dynamodb", ctx.profile, ctx.region)
    try:
        return c.describe_table(TableName=table_name)
    except ClientError as e:
        return {"TableName": table_name, "Error": str(e)}


@mcp.tool()
def dynamodb_list_tables(ctx: AwsContext = AwsContext(), limit: int = 50) -> Dict[str, Any]:
    """Lista tabelas (paginação simples)."""
    c = _client("dynamodb", ctx.profile, ctx.region)
    resp = c.list_tables(Limit=limit)
    return {"TableNames": resp.get("TableNames", [])}


# -----------------------------
# SQS (READ-ONLY)
# -----------------------------
@mcp.tool()
def sqs_get_queue_attributes(queue_url: str, ctx: AwsContext = AwsContext()) -> Dict[str, Any]:
    """
    Lê atributos importantes da fila.
    Importante: NÃO faz receive-message (isso afeta visibility timeout).
    """
    c = _client("sqs", ctx.profile, ctx.region)
    attrs = [
        "All",
        "ApproximateNumberOfMessages",
        "ApproximateNumberOfMessagesNotVisible",
        "ApproximateNumberOfMessagesDelayed",
        "RedrivePolicy",
        "VisibilityTimeout",
        "MessageRetentionPeriod",
        "ReceiveMessageWaitTimeSeconds",
        "KmsMasterKeyId",
    ]
    try:
        resp = c.get_queue_attributes(QueueUrl=queue_url, AttributeNames=attrs)
        return resp
    except ClientError as e:
        return {"QueueUrl": queue_url, "Error": str(e)}


# -----------------------------
# EKS (READ-ONLY) - metadados
# -----------------------------
@mcp.tool()
def eks_list_clusters(ctx: AwsContext = AwsContext()) -> Dict[str, Any]:
    """Lista clusters EKS na região."""
    c = _client("eks", ctx.profile, ctx.region)
    return c.list_clusters()


@mcp.tool()
def eks_describe_cluster(cluster_name: str, ctx: AwsContext = AwsContext()) -> Dict[str, Any]:
    """Descreve cluster (endpoint, version, status, vpcConfig...)."""
    c = _client("eks", ctx.profile, ctx.region)
    try:
        return c.describe_cluster(name=cluster_name)
    except ClientError as e:
        return {"cluster": cluster_name, "Error": str(e)}


# -----------------------------
# Tool de "triagem" (heurísticas) - sugere próximos passos
# -----------------------------
@mcp.tool()
def diagnose_error_text(error_text: str) -> Dict[str, Any]:
    """
    Faz uma análise heurística do texto de erro e sugere investigação.
    NÃO altera nada; apenas recomenda.
    """
    t = error_text.lower()
    hints: List[str] = []

    # IAM / Auth
    if "accessdenied" in t or "not authorized" in t or "unauthorized" in t:
        hints.append("Parece erro de permissão (IAM). Verifique role/policy do caller e o recurso alvo (ARN/region).")

    # Lambda timeout / memory
    if "task timed out" in t or "timeout" in t:
        hints.append("Pode ser timeout. Verifique Timeout/Memory da Lambda e dependências (VPC, DNS, endpoints).")

    # DynamoDB throughput
    if "provisionedthroughputexceeded" in t or "throttl" in t:
        hints.append("Indício de throttling. Verifique capacidade (RCU/WCU) ou AutoScaling/on-demand e padrões de acesso.")

    # SQS DLQ / redrive
    if "redrive" in t or "dlq" in t:
        hints.append("Pode envolver DLQ/RedrivePolicy. Cheque policy, maxReceiveCount e mensagens indo para DLQ.")

    # TLS / cert
    if "certificate" in t or "x509" in t or "subject alternative name" in t:
        hints.append("Erro TLS/certificado. Verifique SAN do cert, host header, Ingress/ALB e DNS.")

    # EKS / pods
    if "crashloopbackoff" in t or "imagepullbackoff" in t or "oomkilled" in t:
        hints.append("Erro Kubernetes (CrashLoop/ImagePull/OOM). Checar logs do pod, image tag/registry e requests/limits.")

    return {"signals": hints or ["Não identifiquei padrão forte. Envie stacktrace/log e qual serviço envolvido."]}


if __name__ == "__main__":
    # STDIO é o modo mais comum para Cursor iniciar o MCP server.
    mcp.run(transport="stdio")