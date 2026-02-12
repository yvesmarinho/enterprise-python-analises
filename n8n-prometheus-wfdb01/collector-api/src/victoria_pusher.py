"""
Victoria Metrics Pusher - Wrapper para compatibilidade com código legado
Agora usa Prometheus Pushgateway como backend
"""
import asyncio
from typing import Optional, Dict, Any
from prometheus_client import Gauge
from .config import settings
from .logger import get_logger
from .metrics import PrometheusPusher

logger = get_logger(__name__)

# Singleton instance
_victoria_pusher_instance: Optional['VictoriaPusher'] = None


class VictoriaPusher:
    """
    Wrapper para manter compatibilidade com código legado que usava VictoriaMetrics.
    Agora envia métricas para Prometheus Pushgateway.
    """
    
    def __init__(self):
        """Inicializa o pusher"""
        self.prometheus_pusher: Optional[PrometheusPusher] = None
        self.enabled = settings.prometheus_pushgateway_enabled
        
        # Métricas Prometheus para ping data
        self.ping_network_rtt = Gauge(
            'ping_network_rtt_milliseconds',
            'Network round-trip time in milliseconds',
            ['source_location', 'source_datacenter', 'source_country']
        )
        
        self.ping_processing_time = Gauge(
            'ping_processing_time_milliseconds', 
            'Ping processing time in milliseconds',
            ['source_location', 'source_datacenter', 'source_country']
        )
        
        if self.enabled:
            self.prometheus_pusher = PrometheusPusher(
                pushgateway_url=settings.prometheus_pushgateway_url,
                job_name=f"{settings.prometheus_job_name}_ping_data",
                instance_name=f"{settings.api_host}:{settings.api_port}"
            )
            logger.info("victoria_pusher_initialized",
                       pushgateway_url=settings.prometheus_pushgateway_url,
                       mode="prometheus_pushgateway")
        else:
            logger.info("victoria_pusher_disabled")
    
    async def push_ping_metrics(self, ping_metrics: Dict[str, Any]) -> bool:
        """
        Envia métricas de ping para Prometheus Pushgateway
        
        Args:
            ping_metrics: Dicionário com dados do ping:
                - ping_id: str
                - network_rtt_ms: float | None
                - processing_time_ms: float
                - source_location: str
                - source_datacenter: str
                - source_country: str
        
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        if not self.enabled or not self.prometheus_pusher:
            logger.debug("victoria_pusher_skip", reason="disabled")
            return False
        
        try:
            # Extrair labels
            source_location = ping_metrics.get('source_location', 'unknown')
            source_datacenter = ping_metrics.get('source_datacenter', 'unknown')
            source_country = ping_metrics.get('source_country', 'unknown')
            
            # Atualizar métricas Prometheus
            if ping_metrics.get('network_rtt_ms') is not None:
                self.ping_network_rtt.labels(
                    source_location=source_location,
                    source_datacenter=source_datacenter,
                    source_country=source_country
                ).set(ping_metrics['network_rtt_ms'])
            
            self.ping_processing_time.labels(
                source_location=source_location,
                source_datacenter=source_datacenter,
                source_country=source_country
            ).set(ping_metrics['processing_time_ms'])
            
            # Enviar para Pushgateway
            success = await self.prometheus_pusher.push_metrics_async()
            
            if success:
                logger.debug("ping_metrics_pushed",
                           ping_id=ping_metrics.get('ping_id'),
                           source_location=source_location)
            else:
                logger.warning("ping_metrics_push_failed",
                             ping_id=ping_metrics.get('ping_id'))
            
            return success
            
        except Exception as e:
            logger.error("push_ping_metrics_error",
                        ping_id=ping_metrics.get('ping_id'),
                        error=str(e),
                        error_type=type(e).__name__)
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do pusher"""
        if self.prometheus_pusher:
            return self.prometheus_pusher.get_stats()
        return {
            'enabled': False,
            'push_count': 0,
            'error_count': 0,
            'last_push_time': None
        }


def get_victoria_pusher() -> VictoriaPusher:
    """
    Retorna singleton instance do VictoriaPusher
    
    Returns:
        VictoriaPusher: Instância global do pusher
    """
    global _victoria_pusher_instance
    
    if _victoria_pusher_instance is None:
        _victoria_pusher_instance = VictoriaPusher()
    
    return _victoria_pusher_instance
