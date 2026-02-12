"""Pusher de métricas para Prometheus Pushgateway"""
import asyncio
import time
from typing import Optional
import httpx
from prometheus_client import generate_latest, CollectorRegistry, REGISTRY
from ..config import settings
from ..logger import get_logger

logger = get_logger(__name__)


class PrometheusPusher:
    """Classe para enviar métricas ao Prometheus Pushgateway"""
    
    def __init__(
        self,
        pushgateway_url: str,
        job_name: str,
        instance_name: Optional[str] = None,
        registry: CollectorRegistry = REGISTRY
    ):
        """
        Inicializa o Pusher
        
        Args:
            pushgateway_url: URL do Pushgateway (ex: http://wfdb01.vya.digital:9091)
            job_name: Nome do job (ex: collector_api)
            instance_name: Nome opcional da instância
            registry: Registry do Prometheus (default: REGISTRY global)
        """
        self.pushgateway_url = pushgateway_url.rstrip('/')
        self.job_name = job_name
        self.instance_name = instance_name or f"collector_api_{int(time.time())}"
        self.registry = registry
        self.push_count = 0
        self.error_count = 0
        self.last_push_time = None
        
        logger.info("prometheus_pusher_initialized",
                   pushgateway_url=self.pushgateway_url,
                   job_name=self.job_name,
                   instance_name=self.instance_name)
    
    def push_metrics(self) -> bool:
        """
        Envia métricas para o Pushgateway de forma síncrona
        
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            # Gerar métricas
            metrics_data = generate_latest(self.registry)
            
            # Construir URL
            url = f"{self.pushgateway_url}/metrics/job/{self.job_name}/instance/{self.instance_name}"
            
            # Enviar via HTTP POST
            import requests
            response = requests.post(
                url,
                data=metrics_data,
                headers={'Content-Type': 'text/plain; version=0.0.4'},
                timeout=10,  # Timeout aumentado para HTTPS
                verify=True  # Verificação SSL explícita
            )
            response.raise_for_status()
            
            self.push_count += 1
            self.last_push_time = time.time()
            
            logger.debug("prometheus_metrics_pushed",
                        url=url,
                        push_count=self.push_count,
                        metrics_size=len(metrics_data))
            
            return True
            
        except Exception as e:
            self.error_count += 1
            logger.error("prometheus_push_error",
                        error=str(e),
                        error_type=type(e).__name__,
                        error_count=self.error_count,
                        pushgateway_url=self.pushgateway_url)
            return False
    
    async def push_metrics_async(self) -> bool:
        """
        Envia métricas para o Pushgateway de forma assíncrona
        
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            # Gerar métricas
            metrics_data = generate_latest(self.registry)
            
            # Construir URL
            url = f"{self.pushgateway_url}/metrics/job/{self.job_name}/instance/{self.instance_name}"
            
            # Enviar via HTTP POST (async)
            async with httpx.AsyncClient(timeout=10.0, verify=True) as client:
                response = await client.post(
                    url,
                    content=metrics_data,
                    headers={'Content-Type': 'text/plain; version=0.0.4'}
                )
                response.raise_for_status()
            
            self.push_count += 1
            self.last_push_time = time.time()
            
            logger.debug("prometheus_metrics_pushed",
                        url=url,
                        push_count=self.push_count,
                        metrics_size=len(metrics_data))
            
            return True
            
        except Exception as e:
            self.error_count += 1
            logger.error("prometheus_push_error",
                        error=str(e),
                        error_type=type(e).__name__,
                        error_count=self.error_count,
                        pushgateway_url=self.pushgateway_url)
            return False
    
    async def run_periodic_push(self, interval: int = 60):
        """
        Executa push periódico de métricas
        
        Args:
            interval: Intervalo em segundos entre cada push
        """
        logger.info("prometheus_periodic_push_started",
                   interval=interval,
                   job_name=self.job_name)
        
        while True:
            try:
                await self.push_metrics_async()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("prometheus_periodic_push_cancelled")
                break
            except Exception as e:
                logger.error("prometheus_periodic_push_error",
                           error=str(e),
                           error_type=type(e).__name__)
                await asyncio.sleep(interval)
    
    def delete_metrics(self) -> bool:
        """
        Remove métricas do Pushgateway
        
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            url = f"{self.pushgateway_url}/metrics/job/{self.job_name}/instance/{self.instance_name}"
            
            import requests
            response = requests.delete(url, timeout=10, verify=True)
            response.raise_for_status()
            
            logger.info("prometheus_metrics_deleted",
                       url=url)
            
            return True
            
        except Exception as e:
            logger.error("prometheus_delete_error",
                        error=str(e),
                        error_type=type(e).__name__)
            return False
    
    def get_stats(self) -> dict:
        """
        Retorna estatísticas do pusher
        
        Returns:
            Dict com estatísticas
        """
        return {
            "pushgateway_url": self.pushgateway_url,
            "job_name": self.job_name,
            "instance_name": self.instance_name,
            "push_count": self.push_count,
            "error_count": self.error_count,
            "last_push_time": self.last_push_time,
            "last_push_ago_seconds": time.time() - self.last_push_time if self.last_push_time else None
        }
