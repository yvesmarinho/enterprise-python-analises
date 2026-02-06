"""Main FastAPI application"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from datetime import datetime, timezone
from .config import settings
from .logger import configure_logging, get_logger
from .models import HealthResponse, ErrorResponse
from .api import router as ping_router
from .database.postgres_probe import PostgresProbe
from .database import MySQLProbe
from .metrics import MetricsExporter, service_up, PrometheusPusher

# Configurar logging
configure_logging()
logger = get_logger(__name__)

# Tasks de background
background_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia lifecycle da aplicação"""
    logger.info("collector_api_starting",
               version="1.0.0",
               environment=settings.environment,
               api_host=settings.api_host,
               api_port=settings.api_port)
    
    # Inicializar probes de database
    postgres_probe = PostgresProbe()
    mysql_probe = MySQLProbe()
    
    # Criar tasks de background para probes
    postgres_task = asyncio.create_task(
        postgres_probe.run_periodic_probe(settings.db_probe_interval)
    )
    mysql_task = asyncio.create_task(
        mysql_probe.run_periodic_probe(settings.db_probe_interval)
    )
    
    background_tasks.extend([postgres_task, mysql_task])
    
    # Inicializar Prometheus Pusher (se habilitado)
    prometheus_task = None
    if settings.prometheus_pushgateway_enabled:
        logger.info("prometheus_pusher_enabled",
                   pushgateway_url=settings.prometheus_pushgateway_url,
                   interval=settings.prometheus_pushgateway_interval)
        
        prometheus_pusher = PrometheusPusher(
            pushgateway_url=settings.prometheus_pushgateway_url,
            job_name=settings.prometheus_job_name,
            instance_name=f"{settings.api_host}:{settings.api_port}"
        )
        
        prometheus_task = asyncio.create_task(
            prometheus_pusher.run_periodic_push(settings.prometheus_pushgateway_interval)
        )
        background_tasks.append(prometheus_task)
    else:
        logger.info("prometheus_pusher_disabled")
    
    logger.info("collector_api_started_successfully")
    
    yield
    
    # Shutdown
    logger.info("collector_api_shutting_down")
    
    # Cancelar tasks de background
    for task in background_tasks:
        task.cancel()
    
    await asyncio.gather(*background_tasks, return_exceptions=True)
    
    service_up.set(0)
    logger.info("collector_api_shutdown_complete")


# Criar aplicação FastAPI
app = FastAPI(
    title="N8N Collector API",
    description="API para coletar métricas de latência e dados do N8N",
    version="1.0.0",
    lifespan=lifespan
)

# Incluir routers
app.include_router(ping_router, prefix="/api", tags=["ping"])


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        services={
            "api": "up",
            "database_probes": "running",
            "metrics": "collecting"
        }
    )


@app.get("/metrics")
async def metrics():
    """Endpoint de métricas Prometheus"""
    metrics_data = MetricsExporter.get_metrics()
    return Response(
        content=metrics_data,
        media_type=MetricsExporter.get_content_type()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global de exceções"""
    logger.error("unhandled_exception",
                error=str(exc),
                error_type=type(exc).__name__,
                path=request.url.path,
                method=request.method)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc),
            timestamp=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        ).model_dump()
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "N8N Collector API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }
