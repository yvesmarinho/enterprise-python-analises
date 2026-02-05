"""Endpoint de ping para receber requisições"""
import time
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from ..models import PingRequest, PingResponse, ErrorResponse
from ..config import settings
from ..logger import get_logger
from ..metrics import api_requests_total, api_request_duration_seconds, network_latency_rtt_seconds
from ..victoria_pusher import get_victoria_pusher

logger = get_logger(__name__)
router = APIRouter()


def verify_api_key(x_api_key: str = Header(...)):
    """Verifica a API Key"""
    if x_api_key != settings.api_key:
        logger.warning("invalid_api_key_attempt", provided_key=x_api_key[:10] + "...")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


@router.post("/ping", response_model=PingResponse)
async def receive_ping(
    request: Request,
    ping_data: PingRequest,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """
    Recebe uma requisição de ping e calcula latência
    """
    start_time = time.perf_counter()
    timestamp_received = datetime.now(timezone.utc)
    
    # Verificar API Key
    verify_api_key(x_api_key)
    
    logger.info("ping_received",
               ping_id=ping_data.ping_id,
               source_location=ping_data.source.location,
               source_country=ping_data.source.country,
               timestamp_start=ping_data.timestamp_start)
    
    try:
        # Parse timestamp do cliente
        try:
            client_timestamp = datetime.fromisoformat(
                ping_data.timestamp_start.replace('Z', '+00:00')
            )
        except Exception as e:
            logger.error("invalid_timestamp_format",
                        ping_id=ping_data.ping_id,
                        timestamp=ping_data.timestamp_start,
                        error=str(e))
            client_timestamp = None
        
        # Calcular RTT (se timestamp válido)
        network_rtt_ms = None
        if client_timestamp:
            rtt_seconds = (timestamp_received - client_timestamp).total_seconds()
            network_rtt_ms = rtt_seconds * 1000
            
            # Registrar métrica de latência
            network_latency_rtt_seconds.labels(
                source_location=ping_data.source.location,
                source_datacenter=ping_data.source.datacenter,
                source_country=ping_data.source.country,
                target_location="collector_api_usa"
            ).observe(rtt_seconds)
            
            logger.debug("network_rtt_calculated",
                        ping_id=ping_data.ping_id,
                        rtt_ms=round(network_rtt_ms, 2),
                        rtt_seconds=round(rtt_seconds, 4))
        
        # Simular pequeno processamento (para métricas de API)
        timestamp_processed = datetime.now(timezone.utc)
        
        # Calcular tempo de processamento
        processing_time = time.perf_counter() - start_time
        processing_time_ms = processing_time * 1000
        
        # Registrar métrica de API
        api_request_duration_seconds.labels(
            endpoint="/api/ping",
            method="POST"
        ).observe(processing_time)
        
        api_requests_total.labels(
            endpoint="/api/ping",
            method="POST",
            status_code="200"
        ).inc()
        
        # Preparar resposta
        response = PingResponse(
            status="success",
            ping_id=ping_data.ping_id,
            timestamp_received=timestamp_received.isoformat().replace('+00:00', 'Z'),
            timestamp_processed=timestamp_processed.isoformat().replace('+00:00', 'Z'),
            processing_time_ms=round(processing_time_ms, 3),
            network_rtt_ms=round(network_rtt_ms, 2) if network_rtt_ms else None,
            message="Ping received successfully"
        )
        
        logger.info("ping_processed",
                   ping_id=ping_data.ping_id,
                   processing_time_ms=round(processing_time_ms, 2),
                   network_rtt_ms=round(network_rtt_ms, 2) if network_rtt_ms else None)
        
        # Enviar métricas para VictoriaMetrics (não aguarda resposta)
        try:
            victoria_pusher = get_victoria_pusher()
            ping_metrics = {
                'ping_id': ping_data.ping_id,
                'network_rtt_ms': network_rtt_ms,
                'processing_time_ms': processing_time_ms,
                'source_location': ping_data.source.location,
                'source_datacenter': ping_data.source.datacenter,
                'source_country': ping_data.source.country
            }
            # Fire and forget - não bloqueia a resposta
            asyncio.create_task(victoria_pusher.push_ping_metrics(ping_metrics))
        except Exception as e:
            logger.warning("victoria_push_skipped", error=str(e))
        
        return response
        
    except Exception as e:
        api_requests_total.labels(
            endpoint="/api/ping",
            method="POST",
            status_code="500"
        ).inc()
        
        logger.error("ping_processing_error",
                    ping_id=ping_data.ping_id,
                    error=str(e),
                    error_type=type(e).__name__)
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing ping: {str(e)}"
        )


@router.get("/ping/stats")
async def get_ping_stats(x_api_key: str = Header(..., alias="X-API-Key")):
    """Retorna estatísticas de ping"""
    verify_api_key(x_api_key)
    
    # TODO: Implementar coleta de estatísticas do VictoriaMetrics
    return {
        "status": "success",
        "message": "Statistics endpoint - to be implemented"
    }
