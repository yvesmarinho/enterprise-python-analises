"""Métricas Prometheus para o Collector API"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from ..logger import get_logger

logger = get_logger(__name__)

# Métricas de API
api_requests_total = Counter(
    'api_requests_total',
    'Total de requisições recebidas',
    ['endpoint', 'method', 'status_code']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'Duração das requisições da API',
    ['endpoint', 'method'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Métricas de latência de rede (calculadas no servidor)
network_latency_rtt_seconds = Histogram(
    'network_latency_rtt_seconds',
    'Round-trip time calculado no servidor',
    ['source_location', 'source_datacenter', 'source_country', 'target_location'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3, 0.5, 0.75, 1.0, 2.0, 5.0]
)

# Métricas de database
database_query_latency_seconds = Histogram(
    'database_query_latency_seconds',
    'Latência de queries no banco de dados',
    ['db_type', 'operation', 'status'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

database_connection_errors_total = Counter(
    'database_connection_errors_total',
    'Total de erros de conexão com banco',
    ['db_type', 'error_type']
)

database_available = Gauge(
    'database_available',
    'Indica se o banco está disponível (1) ou não (0)',
    ['db_type']
)

# Service availability
service_up = Gauge(
    'collector_api_up',
    'Indica se o serviço está ativo (1) ou não (0)'
)

# Set service as up
service_up.set(1)


class MetricsExporter:
    """Classe para exportar métricas"""
    
    @staticmethod
    def get_metrics():
        """Retorna as métricas em formato Prometheus"""
        return generate_latest()
    
    @staticmethod
    def get_content_type():
        """Retorna o content type das métricas"""
        return CONTENT_TYPE_LATEST
