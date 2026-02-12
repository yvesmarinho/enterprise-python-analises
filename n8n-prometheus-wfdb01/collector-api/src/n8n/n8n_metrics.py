"""Métricas Prometheus para N8N"""
from prometheus_client import Counter, Histogram, Gauge

# Métricas de API
n8n_api_request_total = Counter(
    'n8n_api_request_total',
    'Total de requisições à API do N8N',
    ['method', 'endpoint', 'status_code']
)

n8n_api_request_duration = Histogram(
    'n8n_api_request_duration_seconds',
    'Duração das requisições à API do N8N',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

n8n_api_request_errors = Counter(
    'n8n_api_request_errors_total',
    'Total de erros nas requisições à API do N8N',
    ['method', 'endpoint', 'error_type']
)

# Métricas de Workflows
n8n_workflow_executions_total = Counter(
    'n8n_workflow_executions_total',
    'Total de execuções de workflows',
    ['workflow_id', 'workflow_name', 'status']
)

n8n_workflow_execution_duration = Histogram(
    'n8n_workflow_execution_duration_seconds',
    'Duração das execuções de workflows',
    ['workflow_id', 'workflow_name'],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
)

n8n_workflow_execution_status = Gauge(
    'n8n_workflow_execution_status',
    'Status da última execução do workflow (1=success, 0=error, -1=running)',
    ['workflow_id', 'workflow_name']
)

n8n_workflow_active_status = Gauge(
    'n8n_workflow_active_status',
    'Status ativo do workflow (1=active, 0=inactive)',
    ['workflow_id', 'workflow_name']
)

# Métricas de Nodes
n8n_node_execution_duration = Histogram(
    'n8n_node_execution_duration_seconds',
    'Duração da execução de nodes',
    ['workflow_id', 'workflow_name', 'node_name', 'node_type'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0]
)

n8n_node_execution_errors = Counter(
    'n8n_node_execution_errors_total',
    'Total de erros na execução de nodes',
    ['workflow_id', 'workflow_name', 'node_name', 'node_type']
)
