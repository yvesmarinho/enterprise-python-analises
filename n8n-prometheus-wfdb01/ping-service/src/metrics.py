"""Métricas Prometheus para o Ping Service"""
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from .logger import get_logger

logger = get_logger(__name__)

# Métricas de latência de rede
network_latency_histogram = Histogram(
    'network_latency_rtt_seconds',
    'Round-trip time da requisição ping',
    ['source_location', 'source_datacenter', 'source_country', 'target_location'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3, 0.5, 0.75, 1.0, 2.0, 5.0]
)

network_latency_gauge = Gauge(
    'network_latency_last_rtt_seconds',
    'Última medição de RTT',
    ['source_location', 'source_datacenter', 'source_country', 'target_location']
)

# Métricas de disponibilidade
ping_requests_total = Counter(
    'ping_requests_total',
    'Total de requisições ping enviadas',
    ['source_location', 'target_location', 'status']
)

ping_errors_total = Counter(
    'ping_errors_total',
    'Total de erros em requisições ping',
    ['source_location', 'target_location', 'error_type']
)

# Métricas de API do Collector
api_response_time_histogram = Histogram(
    'api_collector_response_time_seconds',
    'Tempo de processamento da API Collector',
    ['source_location', 'status_code'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Service availability
service_up = Gauge(
    'ping_service_up',
    'Indica se o serviço está ativo (1) ou não (0)',
    ['source_location']
)


class MetricsCollector:
    """Classe para coletar e gerenciar métricas"""
    
    def __init__(self, source_location: str, source_datacenter: str, source_country: str):
        self.source_location = source_location
        self.source_datacenter = source_datacenter
        self.source_country = source_country
        self.target_location = "collector_api_usa"
        
        # Marca o serviço como ativo
        service_up.labels(source_location=self.source_location).set(1)
        logger.info("metrics_collector_initialized",
                   source_location=self.source_location,
                   source_datacenter=self.source_datacenter)
    
    def record_ping_success(self, rtt_seconds: float, api_processing_ms: float, status_code: int):
        """Registra uma requisição ping bem-sucedida"""
        # Network latency
        network_latency_histogram.labels(
            source_location=self.source_location,
            source_datacenter=self.source_datacenter,
            source_country=self.source_country,
            target_location=self.target_location
        ).observe(rtt_seconds)
        
        network_latency_gauge.labels(
            source_location=self.source_location,
            source_datacenter=self.source_datacenter,
            source_country=self.source_country,
            target_location=self.target_location
        ).set(rtt_seconds)
        
        # API processing
        api_response_time_histogram.labels(
            source_location=self.source_location,
            status_code=str(status_code)
        ).observe(api_processing_ms / 1000.0)
        
        # Request count
        ping_requests_total.labels(
            source_location=self.source_location,
            target_location=self.target_location,
            status='success'
        ).inc()
        
        logger.debug("metrics_recorded",
                    rtt_seconds=rtt_seconds,
                    api_processing_ms=api_processing_ms,
                    status_code=status_code)
    
    def record_ping_error(self, error_type: str):
        """Registra um erro em requisição ping"""
        ping_errors_total.labels(
            source_location=self.source_location,
            target_location=self.target_location,
            error_type=error_type
        ).inc()
        
        ping_requests_total.labels(
            source_location=self.source_location,
            target_location=self.target_location,
            status='error'
        ).inc()
        
        logger.warning("ping_error_recorded", error_type=error_type)
    
    def shutdown(self):
        """Marca o serviço como inativo"""
        service_up.labels(source_location=self.source_location).set(0)
        logger.info("metrics_collector_shutdown")


def start_metrics_server(port: int):
    """Inicia o servidor HTTP de métricas Prometheus"""
    try:
        start_http_server(port)
        logger.info("metrics_server_started", port=port)
    except Exception as e:
        logger.error("metrics_server_start_failed", error=str(e), port=port)
        raise
