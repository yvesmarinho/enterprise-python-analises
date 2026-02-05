"""Cliente HTTP para enviar pings ao Collector API"""
import httpx
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from .config import settings
from .logger import get_logger
from .metrics import MetricsCollector

logger = get_logger(__name__)


class PingClient:
    """Cliente para enviar requisições ping"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.target_url = settings.target_url
        self.api_key = settings.collector_api_key
        self.timeout = settings.request_timeout
        self.metrics = metrics_collector
        
        # HTTP Client com retry
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            follow_redirects=True
        )
        
        logger.info("ping_client_initialized",
                   target_url=self.target_url,
                   timeout=self.timeout)
    
    async def send_ping(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Envia uma requisição ping ao Collector API
        
        Returns:
            Tuple[bool, Optional[Dict]]: (sucesso, dados_resposta)
        """
        ping_id = str(uuid.uuid4())
        timestamp_start = datetime.now(timezone.utc)
        timestamp_start_iso = timestamp_start.isoformat().replace('+00:00', 'Z')
        
        payload = {
            "timestamp_start": timestamp_start_iso,
            "source": {
                "location": settings.source_location,
                "datacenter": settings.source_datacenter,
                "country": settings.source_country
            },
            "ping_id": ping_id
        }
        
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "PingService/1.0.0"
        }
        
        logger.debug("sending_ping",
                    ping_id=ping_id,
                    target_url=self.target_url,
                    timestamp_start=timestamp_start_iso)
        
        try:
            # Medir tempo de requisição
            start_time = time.perf_counter()
            
            response = await self.client.post(
                self.target_url,
                json=payload,
                headers=headers
            )
            
            end_time = time.perf_counter()
            rtt_seconds = end_time - start_time
            
            # Parse response
            response_data = response.json()
            
            if response.status_code == 200:
                # Extrair dados de latência da resposta
                api_processing_ms = response_data.get('processing_time_ms', 0)
                
                # Registrar métricas
                self.metrics.record_ping_success(
                    rtt_seconds=rtt_seconds,
                    api_processing_ms=api_processing_ms,
                    status_code=response.status_code
                )
                
                logger.info("ping_success",
                           ping_id=ping_id,
                           rtt_seconds=round(rtt_seconds, 4),
                           rtt_ms=round(rtt_seconds * 1000, 2),
                           api_processing_ms=api_processing_ms,
                           status_code=response.status_code)
                
                return True, response_data
            else:
                self.metrics.record_ping_error(f"http_{response.status_code}")
                
                logger.warning("ping_failed",
                             ping_id=ping_id,
                             status_code=response.status_code,
                             response=response_data)
                
                return False, response_data
                
        except httpx.TimeoutException as e:
            self.metrics.record_ping_error("timeout")
            logger.error("ping_timeout",
                        ping_id=ping_id,
                        timeout=self.timeout,
                        error=str(e))
            return False, None
            
        except httpx.ConnectError as e:
            self.metrics.record_ping_error("connection_error")
            logger.error("ping_connection_error",
                        ping_id=ping_id,
                        target_url=self.target_url,
                        error=str(e))
            return False, None
            
        except Exception as e:
            self.metrics.record_ping_error("unknown_error")
            logger.error("ping_unknown_error",
                        ping_id=ping_id,
                        error=str(e),
                        error_type=type(e).__name__)
            return False, None
    
    async def close(self):
        """Fecha o cliente HTTP"""
        await self.client.aclose()
        logger.info("ping_client_closed")
