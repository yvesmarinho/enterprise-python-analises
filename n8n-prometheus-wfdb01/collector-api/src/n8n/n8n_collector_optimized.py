"""Coletor de métricas do N8N - VERSÃO OTIMIZADA"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..logger import get_logger
from .n8n_client import N8NClient
from .n8n_metrics import (
    n8n_node_execution_duration,
    n8n_node_execution_errors,
    n8n_workflow_active_status,
    n8n_workflow_execution_duration,
    n8n_workflow_execution_status,
    n8n_workflow_executions_total,
)

logger = get_logger(__name__)


class N8NCollector:
    """Coletor de métricas do N8N - OTIMIZADO"""

    def __init__(self, client: N8NClient):
        """
        Inicializa o coletor

        Args:
            client: Cliente N8N configurado
        """
        self.client = client
        self._last_execution_ids: set = set()
        self._workflows_cache: Dict[str, Dict[str, Any]] = {}

        # Circuit breaker state
        self._failure_count = 0
        self._max_failures = 5
        self._is_circuit_open = False
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 minutos

        # Performance tracking
        self._collection_count = 0
        self._skip_count = 0

        logger.info("n8n_collector_initialized_optimized",
                   max_failures=self._max_failures,
                   health_check_interval_seconds=self._health_check_interval)

    async def _check_circuit_breaker(self) -> bool:
        """
        Verifica e gerencia o circuit breaker

        Returns:
            True se pode continuar, False se circuit está aberto
        """
        if self._is_circuit_open:
            # Tentar fechar circuit após 5 minutos
            import time
            if time.time() - self._last_health_check > 300:
                logger.info("circuit_breaker_attempting_reset")
                is_healthy = await self.client.health_check()
                if is_healthy:
                    self._is_circuit_open = False
                    self._failure_count = 0
                    logger.info("circuit_breaker_reset_success")
                    return True
                else:
                    self._last_health_check = time.time()
                    logger.warning("circuit_breaker_reset_failed")
                    return False
            return False
        return True

    async def _handle_failure(self) -> None:
        """Gerencia falhas e abre circuit se necessário"""
        self._failure_count += 1
        logger.warning("collection_failure_detected",
                      failure_count=self._failure_count,
                      max_failures=self._max_failures)

        if self._failure_count >= self._max_failures:
            self._is_circuit_open = True
            import time
            self._last_health_check = time.time()
            logger.error("circuit_breaker_opened",
                        consecutive_failures=self._failure_count)

    async def _reset_failure_count(self) -> None:
        """Reseta contador de falhas após sucesso"""
        if self._failure_count > 0:
            logger.info("collection_success_resetting_failures",
                       previous_failures=self._failure_count)
            self._failure_count = 0

    async def collect_workflow_metrics(self) -> None:
        """Coleta métricas de workflows"""
        try:
            workflows = await self.client.get_workflows()

            logger.info("collecting_workflow_metrics",
                       workflow_count=len(workflows))

            for workflow in workflows:
                workflow_id = workflow.get('id', 'unknown')
                workflow_name = workflow.get('name', 'unnamed')
                is_active = workflow.get('active', False)

                # Atualizar cache de workflows
                self._workflows_cache[workflow_id] = {
                    'name': workflow_name,
                    'active': is_active
                }

                # Métrica de status ativo
                n8n_workflow_active_status.labels(
                    workflow_id=workflow_id,
                    workflow_name=workflow_name
                ).set(1 if is_active else 0)

            logger.info("workflow_metrics_collected_successfully",
                       workflow_count=len(workflows),
                       active_count=sum(1 for w in workflows if w.get('active', False)))

        except Exception as e:
            logger.error("workflow_metrics_collection_failed",
                       error=str(e),
                       error_type=type(e).__name__)
            raise

    async def collect_execution_metrics(self, limit: int = 50) -> None:
        """
        Coleta métricas de execuções - OTIMIZADO

        Args:
            limit: Número máximo de execuções a processar (reduzido de 100 para 50)
        """
        try:
            # Obter execuções recentes
            executions = await self.client.get_executions(limit=limit)

            logger.info("collecting_execution_metrics",
                       execution_count=len(executions))

            new_executions = []

            for execution in executions:
                execution_id = execution.get('id', 'unknown')

                # Processar apenas novas execuções
                if execution_id in self._last_execution_ids:
                    continue

                new_executions.append(execution)
                self._last_execution_ids.add(execution_id)

            # Limitar tamanho do cache de forma mais agressiva (500 -> 300)
            if len(self._last_execution_ids) > 500:
                execution_ids_list = list(self._last_execution_ids)
                self._last_execution_ids = set(execution_ids_list[-300:])
                logger.info("execution_cache_trimmed",
                           previous_size=len(execution_ids_list),
                           new_size=len(self._last_execution_ids))

            logger.info("processing_new_executions",
                       new_count=len(new_executions),
                       cached_count=len(self._last_execution_ids),
                       skipped_count=len(executions) - len(new_executions))

            # Processar novas execuções
            for execution in new_executions:
                await self._process_execution(execution)

            logger.info("execution_metrics_collected_successfully",
                       new_executions=len(new_executions),
                       total_processed=len(self._last_execution_ids))

        except Exception as e:
            logger.error("execution_metrics_collection_failed",
                       error=str(e),
                       error_type=type(e).__name__)
            raise

    async def _process_execution(self, execution: Dict[str, Any]) -> None:
        """
        Processa uma execução e atualiza métricas

        Args:
            execution: Dados da execução
        """
        try:
            execution_id = execution.get('id', 'unknown')
            workflow_id = execution.get('workflowId', 'unknown')
            status = execution.get('status', 'unknown')

            # Obter nome do workflow do cache ou usar ID
            workflow_name = self._workflows_cache.get(workflow_id, {}).get('name', workflow_id)

            # Calcular duração se disponível
            started_at = execution.get('startedAt')
            stopped_at = execution.get('stoppedAt')

            duration_seconds = None
            if started_at and stopped_at:
                try:
                    start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    stop = datetime.fromisoformat(stopped_at.replace('Z', '+00:00'))
                    duration_seconds = (stop - start).total_seconds()
                except Exception as e:
                    logger.debug("execution_duration_parse_failed",
                                execution_id=execution_id,
                                error=str(e))

            # Incrementar contador de execuções
            n8n_workflow_executions_total.labels(
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                status=status
            ).inc()

            # Registrar duração se disponível
            if duration_seconds is not None:
                n8n_workflow_execution_duration.labels(
                    workflow_id=workflow_id,
                    workflow_name=workflow_name
                ).observe(duration_seconds)

            # Status da execução
            status_value = 1 if status == 'success' else (0 if status == 'error' else -1)
            n8n_workflow_execution_status.labels(
                workflow_id=workflow_id,
                workflow_name=workflow_name
            ).set(status_value)

            # Processar nodes APENAS se houver dados (evitar processamento desnecessário)
            data = execution.get('data', {})
            if data and 'resultData' in data and data['resultData'].get('runData'):
                await self._process_execution_nodes(
                    workflow_id,
                    workflow_name,
                    data['resultData']
                )

        except Exception as e:
            logger.error("execution_processing_failed",
                       execution_id=execution.get('id', 'unknown'),
                       error=str(e),
                       error_type=type(e).__name__)

    async def _process_execution_nodes(
        self,
        workflow_id: str,
        workflow_name: str,
        result_data: Dict[str, Any]
    ) -> None:
        """
        Processa métricas de nodes de uma execução - OTIMIZADO

        Args:
            workflow_id: ID do workflow
            workflow_name: Nome do workflow
            result_data: Dados de resultado da execução
        """
        try:
            runs_data = result_data.get('runData', {})

            # Limitar processamento a 50 nodes por execução
            node_count = 0
            max_nodes = 50

            for node_name, node_runs in runs_data.items():
                if node_count >= max_nodes:
                    logger.warning("node_processing_limit_reached",
                                 workflow_id=workflow_id,
                                 max_nodes=max_nodes)
                    break

                if not isinstance(node_runs, list):
                    continue

                for run in node_runs:
                    if not isinstance(run, dict):
                        continue

                    node_count += 1

                    # Obter tipo do node
                    node_type = 'unknown'
                    if run.get('source') and isinstance(run['source'], list) and len(run['source']) > 0:
                        node_type = run['source'][0].get('type', 'unknown')

                    # Calcular duração do node
                    execution_time = run.get('executionTime')

                    if execution_time is not None:
                        duration_seconds = execution_time / 1000.0

                        n8n_node_execution_duration.labels(
                            workflow_id=workflow_id,
                            workflow_name=workflow_name,
                            node_name=node_name,
                            node_type=node_type
                        ).observe(duration_seconds)

                    # Verificar erros no node
                    if run.get('error'):
                        n8n_node_execution_errors.labels(
                            workflow_id=workflow_id,
                            workflow_name=workflow_name,
                            node_name=node_name,
                            node_type=node_type
                        ).inc()

        except Exception as e:
            logger.error("node_processing_failed",
                       workflow_id=workflow_id,
                       error=str(e),
                       error_type=type(e).__name__)

    async def collect_all_metrics(self) -> None:
        """Coleta todas as métricas do N8N"""
        logger.info("starting_n8n_metrics_collection",
                   collection_number=self._collection_count + 1)

        try:
            # Coletar métricas de workflows
            await self.collect_workflow_metrics()

            # Coletar métricas de execuções (limite reduzido)
            await self.collect_execution_metrics(limit=50)

            self._collection_count += 1
            await self._reset_failure_count()

            logger.info("n8n_metrics_collection_completed",
                       total_collections=self._collection_count,
                       total_skips=self._skip_count)

        except Exception as e:
            await self._handle_failure()
            logger.error("n8n_metrics_collection_failed",
                       error=str(e),
                       error_type=type(e).__name__)
            raise

    async def run_periodic_collection(self, interval: int = 60) -> None:
        """
        Executa coleta periódica de métricas - OTIMIZADO

        Args:
            interval: Intervalo entre coletas em segundos (mínimo 60)
        """
        # Garantir intervalo mínimo de 60 segundos
        interval = max(60, interval)

        logger.info("starting_periodic_n8n_collection_optimized",
                   interval_seconds=interval,
                   min_interval=60)

        # Health check inicial
        is_healthy = await self.client.health_check()
        if not is_healthy:
            logger.error("n8n_api_not_available_skipping_collection")
            return

        backoff_time = interval
        max_backoff = interval * 10  # Máximo 10x o intervalo base

        while True:
            try:
                # Verificar circuit breaker
                if not await self._check_circuit_breaker():
                    logger.warning("circuit_breaker_open_skipping_collection",
                                 skip_count=self._skip_count + 1)
                    self._skip_count += 1
                    await asyncio.sleep(60)  # Wait 1 min antes de checar novamente
                    continue

                # Health check periódico (a cada 5 minutos)
                import time
                if time.time() - self._last_health_check > self._health_check_interval:
                    is_healthy = await self.client.health_check()
                    self._last_health_check = time.time()

                    if not is_healthy:
                        logger.warning("periodic_health_check_failed")
                        await self._handle_failure()
                        await asyncio.sleep(backoff_time)
                        backoff_time = min(backoff_time * 2, max_backoff)
                        continue

                # Coletar métricas
                await self.collect_all_metrics()

                # Reset backoff após sucesso
                backoff_time = interval

                # Log de status periódico (a cada 10 coletas)
                if self._collection_count % 10 == 0:
                    logger.info("collector_status_update",
                               collections=self._collection_count,
                               skips=self._skip_count,
                               cached_executions=len(self._last_execution_ids),
                               cached_workflows=len(self._workflows_cache),
                               failure_count=self._failure_count)

            except Exception as e:
                logger.error("periodic_collection_error",
                           error=str(e),
                           error_type=type(e).__name__,
                           backoff_time=backoff_time)

                # Aumentar backoff exponencialmente
                backoff_time = min(backoff_time * 2, max_backoff)

            # Sleep com backoff
            await asyncio.sleep(backoff_time)
