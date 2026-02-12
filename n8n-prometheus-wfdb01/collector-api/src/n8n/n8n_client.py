"""Cliente para comunicação com a API do N8N"""
import asyncio
import time
from typing import List, Dict, Any, Optional
import httpx
from ..logger import get_logger
from .n8n_metrics import (
    n8n_api_request_total,
    n8n_api_request_duration,
    n8n_api_request_errors
)

logger = get_logger(__name__)


class N8NClient:
    """Cliente HTTP para a API do N8N"""

    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        """
        Inicializa o cliente N8N

        Args:
            base_url: URL base da API do N8N (ex: https://workflow.vya.digital/)
            api_key: API key para autenticação
            timeout: Timeout para requisições em segundos
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

        # Headers padrão
        self.headers = {
            'X-N8N-API-KEY': api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        logger.info("n8n_client_initialized",
                   base_url=self.base_url,
                   timeout=timeout)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Faz uma requisição HTTP à API do N8N

        Args:
            method: Método HTTP (GET, POST, etc)
            endpoint: Endpoint da API (sem barra inicial)
            params: Query parameters
            json_data: Body JSON para POST/PUT

        Returns:
            Resposta JSON da API

        Raises:
            httpx.HTTPError: Em caso de erro HTTP
        """
        url = f"{self.base_url}/{endpoint}"

        start_time = time.time()
        status_code = 0
        error_type = None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_data
                )

                status_code = response.status_code
                response.raise_for_status()

                duration = time.time() - start_time

                # Registrar métricas de sucesso
                n8n_api_request_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).inc()

                n8n_api_request_duration.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)

                logger.debug("n8n_api_request_success",
                           method=method,
                           endpoint=endpoint,
                           status_code=status_code,
                           duration_seconds=duration)

                return response.json()

        except httpx.HTTPStatusError as e:
            error_type = f"http_{e.response.status_code}"
            status_code = e.response.status_code

            n8n_api_request_errors.labels(
                method=method,
                endpoint=endpoint,
                error_type=error_type
            ).inc()

            logger.error("n8n_api_request_http_error",
                       method=method,
                       endpoint=endpoint,
                       status_code=status_code,
                       error=str(e))
            raise

        except httpx.TimeoutException as e:
            error_type = "timeout"

            n8n_api_request_errors.labels(
                method=method,
                endpoint=endpoint,
                error_type=error_type
            ).inc()

            logger.error("n8n_api_request_timeout",
                       method=method,
                       endpoint=endpoint,
                       timeout=self.timeout,
                       error=str(e))
            raise

        except Exception as e:
            error_type = "unknown"

            n8n_api_request_errors.labels(
                method=method,
                endpoint=endpoint,
                error_type=error_type
            ).inc()

            logger.error("n8n_api_request_error",
                       method=method,
                       endpoint=endpoint,
                       error_type=type(e).__name__,
                       error=str(e))
            raise

    async def get_workflows(self, active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Obtém lista de workflows

        Args:
            active: Filtrar por workflows ativos (True) ou inativos (False)

        Returns:
            Lista de workflows
        """
        params = {}
        if active is not None:
            params['active'] = 'true' if active else 'false'

        response = await self._make_request('GET', 'api/v1/workflows', params=params)

        # A API do N8N retorna {"data": [...]}
        workflows = response.get('data', [])

        logger.info("n8n_workflows_fetched",
                   count=len(workflows),
                   active_filter=active)

        return workflows

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Obtém detalhes de um workflow específico

        Args:
            workflow_id: ID do workflow

        Returns:
            Dados do workflow
        """
        response = await self._make_request('GET', f'api/v1/workflows/{workflow_id}')
        return response.get('data', {})

    async def get_executions(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém histórico de execuções

        Args:
            workflow_id: Filtrar por ID do workflow (opcional)
            limit: Número máximo de execuções a retornar
            status: Filtrar por status (success, error, waiting, running)

        Returns:
            Lista de execuções
        """
        params = {'limit': limit}

        if workflow_id:
            params['workflowId'] = workflow_id
        if status:
            params['status'] = status

        response = await self._make_request('GET', 'api/v1/executions', params=params)

        executions = response.get('data', [])

        logger.info("n8n_executions_fetched",
                   count=len(executions),
                   workflow_id=workflow_id,
                   status=status)

        return executions

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Obtém detalhes de uma execução específica

        Args:
            execution_id: ID da execução

        Returns:
            Dados da execução incluindo nodes
        """
        response = await self._make_request('GET', f'api/v1/executions/{execution_id}')
        return response.get('data', {})

    async def health_check(self) -> bool:
        """
        Verifica se a API do N8N está acessível

        Returns:
            True se a API está OK, False caso contrário
        """
        try:
            # Tenta obter workflows como health check
            await self.get_workflows()
            logger.info("n8n_health_check_success")
            return True
        except Exception as e:
            logger.error("n8n_health_check_failed", error=str(e))
            return False
