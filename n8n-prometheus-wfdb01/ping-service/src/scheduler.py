"""Scheduler para executar pings periodicamente"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .config import settings
from .logger import get_logger
from .ping_client import PingClient

logger = get_logger(__name__)


class PingScheduler:
    """Scheduler para executar pings em intervalos regulares"""
    
    def __init__(self, ping_client: PingClient):
        self.ping_client = ping_client
        self.scheduler = AsyncIOScheduler()
        self.ping_count = 0
        self.success_count = 0
        self.error_count = 0
        
        logger.info("ping_scheduler_initialized",
                   interval=settings.ping_interval)
    
    async def execute_ping(self):
        """Executa uma tentativa de ping"""
        self.ping_count += 1
        
        logger.debug("executing_scheduled_ping",
                    ping_number=self.ping_count)
        
        try:
            success, response = await self.ping_client.send_ping()
            
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
            
            # Log stats periodicamente
            if self.ping_count % 10 == 0:
                success_rate = (self.success_count / self.ping_count) * 100 if self.ping_count > 0 else 0
                logger.info("ping_statistics",
                           total_pings=self.ping_count,
                           successful=self.success_count,
                           errors=self.error_count,
                           success_rate_percent=round(success_rate, 2))
                
        except Exception as e:
            self.error_count += 1
            logger.error("ping_execution_error",
                        ping_number=self.ping_count,
                        error=str(e))
    
    def start(self):
        """Inicia o scheduler"""
        # Adiciona job de ping
        self.scheduler.add_job(
            self.execute_ping,
            trigger=IntervalTrigger(seconds=settings.ping_interval),
            id='ping_job',
            name='Periodic Ping',
            replace_existing=True,
            max_instances=1
        )
        
        self.scheduler.start()
        
        logger.info("ping_scheduler_started",
                   interval_seconds=settings.ping_interval,
                   pings_per_hour=3600 / settings.ping_interval)
    
    def stop(self):
        """Para o scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            
            logger.info("ping_scheduler_stopped",
                       total_pings=self.ping_count,
                       successful=self.success_count,
                       errors=self.error_count)
    
    async def run_once(self):
        """Executa um ping único (usado para testes)"""
        await self.execute_ping()
