"""Coletor de métricas do N8N"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..logger import get_logger
from .n8n_client import N8NClient
from .n8n_metrics import (
    n8n_workflow_executions_total,
    n8n_workflow_execution_duration,
    n8n_workflow_execution_status,
    n8n_workflow_active_status,
    n8n_node_execution_duration,
    n8n_node_execution_errors
)

logger = get_logger(__name__)


class N8NCollector:
    """Coletor de métricas do N8N"""

    def __init__(self, client: N8NClient):
        """
        Inicializa o coletor

        Args:
            client: Cliente N8N configurado
        """
        self.client = client
        self._last_execution_ids: set = set()
        self._workflows_cache: Dict[str, Dict[str, Any]] = {}

        logger.info("n8n_collector_initialized")

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

                logger.debug("workflow_metric_collected",
                           workflow_id=workflow_id,
                           workflow_name=workflow_name,
                           active=is_active)

            logger.info("workflow_metrics_collected_successfully",
                       workflow_count=len(workflows))

        except Exception as e:
            logger.error("workflow_metrics_collection_failed",
                       error=str(e),
                       error_type=type(e).__name__)

    async def collect_execution_metrics(self, limit: int = 100) -> None:
        """
        Coleta métricas de execuções

        Args:
            limit: Número máximo de execuções a processar
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

            # Limitar tamanho do cache (manter apenas últimas 1000 execuções)
            if len(self._last_execution_ids) > 1000:
                # Converter para lista, manter apenas as últimas 500
                execution_ids_list = list(self._last_execution_ids)
                self._last_execution_ids = set(execution_ids_list[-500:])

            logger.info("processing_new_executions",
                       new_count=len(new_executions),
                       cached_count=len(self._last_execution_ids))

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

    async def _process_execution(self, execution: Dict[str, Any]) -> None:
        """
        Processa uma execução e atualiza métricas

        Args:
            execution: Dados da execução
        """
        try:
            execution_id = execution.get('id', 'unknown')
            workflow_id = execution.get('workflowId', 'unknown')
            status = execution.get('status', 'unknown')  # success, error, waiting, running

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
                    logger.warning("execution_duration_parse_failed",
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

            # Status da execução (1=success, 0=error, -1=running/waiting)
            status_value = 1 if status == 'success' else (0 if status == 'error' else -1)
            n8n_workflow_execution_status.labels(
                workflow_id=workflow_id,
                workflow_name=workflow_name
            ).set(status_value)

            # Processar nodes se disponível
            data = execution.get('data', {})
            if data and 'resultData' in data:
                await self._process_execution_nodes(
                    workflow_id,
                    workflow_name,
                    data['resultData']
                )

            logger.debug("execution_processed",
                       execution_id=execution_id,
                       workflow_id=workflow_id,
                       workflow_name=workflow_name,
                       status=status,
                       duration_seconds=duration_seconds)

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
        Processa métricas de nodes de uma execução

        Args:
            workflow_id: ID do workflow
            workflow_name: Nome do workflow
            result_data: Dados de resultado da execução
        """
        try:
            runs_data = result_data.get('runData', {})

            for node_name, node_runs in runs_data.items():
                if not isinstance(node_runs, list):
                    continue

                for run in node_runs:
                    if not isinstance(run, dict):
                        continue

                    # Obter tipo do node
                    node_type = run.get('source', [{}])[0].get('type', 'unknown') if run.get('source') else 'unknown'

                    # Calcular duração do node
                    start_time = run.get('startTime')
                    execution_time = run.get('executionTime')

                    if execution_time is not None:
                        duration_seconds = execution_time / 1000.0  # Converter ms para segundos

                        n8n_node_execution_duration.labels(
                            workflow_id=workflow_id,
                            workflow_name=workflow_name,
                            node_name=node_name,
                            node_type=node_type
                        ).observe(duration_seconds)

                    # Verificar erros no node
                    error = run.get('error')
                    if error:
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
        logger.info("starting_n8n_metrics_collection")

        try:
            # Coletar métricas de workflows
            await self.collect_workflow_metrics()

            # Coletar métricas de execuções
            await self.collect_execution_metrics(limit=100)

            logger.info("n8n_metrics_collection_completed")

        except Exception as e:
            logger.error("n8n_metrics_collection_failed",
                       error=str(e),
                       error_type=type(e).__name__)

    async def run_periodic_collection(self, interval: int = 60) -> None:
        """
        Executa coleta periódica de métricas

        Args:
            interval: Intervalo entre coletas em segundos
        """
        logger.info("starting_periodic_n8n_collection",
                   interval=interval)

        # Fazer health check inicial
        is_healthy = await self.client.health_check()
        if not is_healthy:
            logger.error("n8n_api_not_available_skipping_collection")
            return

        while True:
            try:
                await self.collect_all_metrics()
            except Exception as e:
                logger.error("periodic_collection_error",
                           error=str(e),
                           error_type=type(e).__name__)

            await asyncio.sleep(interval)
