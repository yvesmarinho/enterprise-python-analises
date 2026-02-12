"""Main entry point do Ping Service"""
import asyncio
import signal
import sys
from .config import settings
from .logger import configure_logging, get_logger
from .metrics import MetricsCollector, start_metrics_server
from .ping_client import PingClient
from .scheduler import PingScheduler

# Configurar logging
configure_logging()
logger = get_logger(__name__)


class PingService:
    """Serviço principal de ping"""
    
    def __init__(self):
        self.metrics_collector = None
        self.ping_client = None
        self.scheduler = None
        self.shutdown_event = asyncio.Event()
        
    async def start(self):
        """Inicia o serviço"""
        logger.info("ping_service_starting",
                   version="1.0.0",
                   environment=settings.environment,
                   target_url=settings.target_url,
                   ping_interval=settings.ping_interval)
        
        try:
            # Inicia servidor de métricas
            start_metrics_server(settings.metrics_port)
            
            # Inicializa componentes
            self.metrics_collector = MetricsCollector(
                source_location=settings.source_location,
                source_datacenter=settings.source_datacenter,
                source_country=settings.source_country
            )
            
            self.ping_client = PingClient(self.metrics_collector)
            self.scheduler = PingScheduler(self.ping_client)
            
            # Executa primeiro ping imediatamente
            logger.info("executing_initial_ping")
            await self.scheduler.run_once()
            
            # Inicia scheduler
            self.scheduler.start()
            
            logger.info("ping_service_started_successfully")
            
            # Aguarda sinal de shutdown
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error("ping_service_start_failed",
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def stop(self):
        """Para o serviço gracefully"""
        logger.info("ping_service_stopping")
        
        try:
            # Para scheduler
            if self.scheduler:
                self.scheduler.stop()
            
            # Fecha cliente HTTP
            if self.ping_client:
                await self.ping_client.close()
            
            # Shutdown métricas
            if self.metrics_collector:
                self.metrics_collector.shutdown()
            
            logger.info("ping_service_stopped_successfully")
            
        except Exception as e:
            logger.error("ping_service_stop_error",
                        error=str(e))
        
        finally:
            self.shutdown_event.set()
    
    def handle_signal(self, signum, frame):
        """Trata sinais do sistema"""
        signal_name = signal.Signals(signum).name
        logger.info("signal_received", signal=signal_name)
        
        # Cria task para parar o serviço
        asyncio.create_task(self.stop())


async def main():
    """Função main"""
    service = PingService()
    
    # Registra handlers de sinal
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(service.stop())
        )
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt_received")
        await service.stop()
    except Exception as e:
        logger.error("main_error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    try:
        # Usa uvloop se disponível para melhor performance
        try:
            import uvloop
            uvloop.install()
            logger.info("uvloop_enabled")
        except ImportError:
            logger.info("uvloop_not_available")
        
        asyncio.run(main())
        
    except Exception as e:
        logger.error("fatal_error", error=str(e))
        sys.exit(1)
