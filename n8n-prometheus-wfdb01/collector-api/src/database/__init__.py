"""Probe para MySQL"""
import time
import asyncio
from typing import Optional, Tuple
import aiomysql
from ..config import settings
from ..logger import get_logger
from ..metrics import database_query_latency_seconds, database_connection_errors_total, database_available

logger = get_logger(__name__)


class MySQLProbe:
    """Probe para monitorar MySQL"""
    
    def __init__(self):
        self.host = settings.mysql_host
        self.port = settings.mysql_port
        self.user = settings.mysql_user
        self.password = settings.mysql_password
        self.db = settings.mysql_db
        self.db_type = "mysql"
        logger.info("mysql_probe_initialized", host=self.host)
    
    async def check_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Verifica conectividade com MySQL
        
        Returns:
            Tuple[bool, Optional[str]]: (sucesso, mensagem_erro)
        """
        start_time = time.perf_counter()
        
        try:
            # Conecta ao banco
            conn = await aiomysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.db,
                connect_timeout=5
            )
            
            try:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    result = await cur.fetchone()
                
                elapsed = time.perf_counter() - start_time
                
                # Registrar métrica
                database_query_latency_seconds.labels(
                    db_type=self.db_type,
                    operation="health_check",
                    status="success"
                ).observe(elapsed)
                
                database_available.labels(db_type=self.db_type).set(1)
                
                logger.debug("mysql_health_check_success",
                           latency_ms=round(elapsed * 1000, 2))
                
                return True, None
                
            finally:
                conn.close()
                
        except aiomysql.Error as e:
            elapsed = time.perf_counter() - start_time
            error_msg = str(e)
            
            database_connection_errors_total.labels(
                db_type=self.db_type,
                error_type="connection_error"
            ).inc()
            
            database_available.labels(db_type=self.db_type).set(0)
            
            logger.error("mysql_connection_error",
                        error=error_msg,
                        latency_ms=round(elapsed * 1000, 2))
            
            return False, error_msg
            
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            error_msg = str(e)
            
            database_connection_errors_total.labels(
                db_type=self.db_type,
                error_type="unknown_error"
            ).inc()
            
            database_available.labels(db_type=self.db_type).set(0)
            
            logger.error("mysql_unknown_error",
                        error=error_msg,
                        error_type=type(e).__name__,
                        latency_ms=round(elapsed * 1000, 2))
            
            return False, error_msg
    
    async def execute_test_query(self) -> Tuple[bool, Optional[float]]:
        """
        Executa uma query de teste e mede latência
        
        Returns:
            Tuple[bool, Optional[float]]: (sucesso, latência_ms)
        """
        start_time = time.perf_counter()
        
        try:
            conn = await aiomysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.db,
                connect_timeout=5
            )
            
            try:
                async with conn.cursor() as cur:
                    # Query na tabela health_check
                    await cur.execute("SELECT * FROM health_check LIMIT 1")
                    result = await cur.fetchone()
                
                elapsed = time.perf_counter() - start_time
                latency_ms = elapsed * 1000
                
                database_query_latency_seconds.labels(
                    db_type=self.db_type,
                    operation="test_query",
                    status="success"
                ).observe(elapsed)
                
                logger.debug("mysql_test_query_success",
                           latency_ms=round(latency_ms, 2))
                
                return True, latency_ms
                
            finally:
                conn.close()
                
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            
            database_query_latency_seconds.labels(
                db_type=self.db_type,
                operation="test_query",
                status="error"
            ).observe(elapsed)
            
            logger.error("mysql_test_query_error",
                        error=str(e),
                        latency_ms=round(elapsed * 1000, 2))
            
            return False, None
    
    async def run_periodic_probe(self, interval: int = 60):
        """
        Executa probe periodicamente
        
        Args:
            interval: Intervalo em segundos
        """
        logger.info("mysql_periodic_probe_started", interval_seconds=interval)
        
        while True:
            try:
                # Health check
                await self.check_connection()
                
                # Test query
                await self.execute_test_query()
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                logger.info("mysql_periodic_probe_cancelled")
                break
            except Exception as e:
                logger.error("mysql_periodic_probe_error", error=str(e))
                await asyncio.sleep(interval)
