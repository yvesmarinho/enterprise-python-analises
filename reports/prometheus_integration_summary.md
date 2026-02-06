# Resumo das Alterações - Integração com Prometheus

## 📅 Data: 06 de fevereiro de 2026

## 🎯 Objetivo

Integrar os sistemas de coleta de métricas do N8N com a stack Prometheus instalada no servidor **wfdb01.vya.digital** (IP: 86.48.31.149).

## 📦 Sistemas Atualizados

### 1. n8n-tuning (Scripts de coleta via API)
### 2. collector-api (API de coleta de métricas)

---

## 🔧 Alterações Realizadas

### 1. n8n-tuning: Scripts de Exportação

#### 📝 Arquivos Modificados:

1. **`.secrets/credentials.template.json`**
   - Adicionado seção `prometheus` com configurações:
     ```json
     "prometheus": {
       "pushgateway_url": "http://wfdb01.vya.digital:9091",
       "remote_write_url": "http://wfdb01.vya.digital:9090/api/v1/write",
       "server_ip": "86.48.31.149",
       "job_name": "n8n_metrics"
     }
     ```

2. **`scripts/n8n_metrics_exporter.py`**
   - Adicionado suporte ao Prometheus Pushgateway
   - Novo parâmetro `--backend` para escolher destino (victoria_metrics ou prometheus)
   - Funções adicionadas:
     - `push_to_prometheus_pushgateway()`: Envia métricas para Pushgateway
     - `push_metrics()`: Abstração para enviar para backend configurado
   - Default: **prometheus**

3. **`scripts/n8n_node_metrics_exporter.py`**
   - Adicionado suporte ao Prometheus Pushgateway  
   - Novo parâmetro `--backend` para escolher destino
   - Parâmetros `--hours` e `--limit` para controlar coleta
   - Default: **prometheus**

4. **`scripts/cron_executions.sh`**
   - Atualizado para usar `--backend prometheus` por padrão

5. **`scripts/cron_node_metrics.sh`**
   - Atualizado para usar `--backend prometheus` por padrão

#### ✨ Arquivo Novo:

6. **`scripts/test_prometheus_connection.py`**
   - Script de teste para validar conectividade com Pushgateway
   - Testa:
     - Conectividade HTTP
     - Envio de métrica de teste
     - Listagem de métricas
     - Remoção de métricas de teste

#### 💻 Como Usar:

```bash
# Coletar métricas gerais e enviar para Prometheus
cd n8n-tuning
python scripts/n8n_metrics_exporter.py --backend prometheus --limit 1000

# Coletar métricas de nodes e enviar para Prometheus
python scripts/n8n_node_metrics_exporter.py --backend prometheus --hours 6 --limit 500

# Testar conexão com Prometheus Pushgateway
python scripts/test_prometheus_connection.py
```

---

### 2. collector-api: API de Coleta de Métricas

#### 📝 Arquivos Modificados:

1. **`src/config.py`**
   - Adicionadas configurações do Prometheus:
     ```python
     prometheus_pushgateway_url: str = "http://wfdb01.vya.digital:9091"
     prometheus_pushgateway_enabled: bool = True
     prometheus_pushgateway_interval: int = 60
     prometheus_job_name: str = "collector_api"
     ```

2. **`src/metrics/__init__.py`**
   - Exporta novo `PrometheusPusher`

3. **`src/main.py`**
   - Integrado `PrometheusPusher` no lifecycle da aplicação
   - Task assíncrona para push periódico de métricas
   - Habilitado por padrão (configurável via env var)

#### ✨ Arquivos Novos:

4. **`src/metrics/prometheus_pusher.py`**
   - Classe `PrometheusPusher` para gerenciar envio de métricas
   - Suporta push síncrono e assíncrono
   - Método `run_periodic_push()` para envio automático
   - Logging estruturado de todas as operações
   - Estatísticas de push (contador, erros, última execução)

5. **`.env.example`**
   - Template de configuração com todas as variáveis
   - Inclui seção de configuração do Prometheus

6. **`PROMETHEUS_SETUP.md`**
   - Documentação completa da integração
   - Guia de configuração passo a passo
   - Troubleshooting
   - Exemplos de queries e alertas
   - Configuração de segurança

#### 💻 Como Usar:

```bash
# 1. Configurar variáveis de ambiente
cd collector-api
mkdir -p .secrets
cp .env.example .secrets/.env
# Editar .secrets/.env com suas credenciais

# 2. Executar aplicação
uvicorn src.main:app --host 0.0.0.0 --port 5000

# Ou com Docker
docker build -t collector-api:latest .
docker run -d \
  --name collector-api \
  -p 5000:5000 \
  -p 9102:9102 \
  -v $(pwd)/.secrets:/app/.secrets:ro \
  collector-api:latest
```

---

## 🌐 Servidor Prometheus

### Informações do Servidor:
- **Hostname**: wfdb01.vya.digital
- **IP**: 86.48.31.149
- **Pushgateway**: http://wfdb01.vya.digital:9091
- **Prometheus**: http://wfdb01.vya.digital:9090

### Verificações:

```bash
# Testar conectividade
curl http://wfdb01.vya.digital:9091/

# Ver métricas no Pushgateway
curl http://wfdb01.vya.digital:9091/metrics

# Ver métricas específicas do job
curl http://wfdb01.vya.digital:9091/metrics | grep 'job="n8n_metrics"'
curl http://wfdb01.vya.digital:9091/metrics | grep 'job="collector_api"'
```

---

## 📊 Métricas Disponíveis

### n8n-tuning (via n8n_metrics_exporter.py):
- `n8n_workflows_total`: Total de workflows
- `n8n_workflows_active`: Workflows ativos
- `n8n_workflow_info`: Informações detalhadas por workflow
- `n8n_executions_total`: Total de execuções
- `n8n_workflow_executions_*`: Métricas de execução por workflow
- `n8n_workflow_execution_duration_seconds`: Duração das execuções
- `n8n_success_rate_percent`: Taxa de sucesso global

### n8n-tuning (via n8n_node_metrics_exporter.py):
- `n8n_node_execution_time_ms`: Tempo de execução por node
- `n8n_node_executions_total`: Total de execuções por node
- `n8n_node_execution_time_max_ms`: Tempo máximo por node
- `n8n_node_type_avg_time_ms`: Tempo médio por tipo de node
- `n8n_node_type_executions_total`: Total de execuções por tipo

### collector-api:
- `api_requests_total`: Requisições da API
- `api_request_duration_seconds`: Duração das requisições
- `network_latency_rtt_seconds`: Latência de rede (RTT)
- `database_query_latency_seconds`: Latência de queries
- `database_connection_errors_total`: Erros de conexão
- `database_available`: Status de disponibilidade do banco
- `collector_api_up`: Status do serviço

---

## ✅ Checklist de Deploy

### Pré-requisitos:
- [ ] Prometheus stack instalada em wfdb01.vya.digital
- [ ] Pushgateway rodando na porta 9091
- [ ] Firewall configurado (permitir porta 9091)
- [ ] Credenciais do N8N configuradas
- [ ] Credenciais do PostgreSQL configuradas (para node metrics)

### n8n-tuning:
- [ ] Copiar e configurar `.secrets/credentials.json`
- [ ] Testar conexão: `python scripts/test_prometheus_connection.py`
- [ ] Executar coleta manual: `python scripts/n8n_metrics_exporter.py --backend prometheus`
- [ ] Configurar cron jobs para coleta automática

### collector-api:
- [ ] Criar `.secrets/.env` baseado em `.env.example`
- [ ] Configurar variáveis de ambiente do Prometheus
- [ ] Testar aplicação localmente
- [ ] Deploy com Docker/Docker Compose
- [ ] Verificar métricas no Pushgateway

### Prometheus:
- [ ] Verificar scraping do Pushgateway está configurado
- [ ] Importar dashboards no Grafana
- [ ] Configurar alertas (opcional)
- [ ] Documentar queries úteis

---

## 🚀 Próximos Passos

1. **Configurar Grafana**
   - Importar dashboards para visualizar métricas
   - Criar painéis personalizados

2. **Configurar Alertas**
   - Alertas de disponibilidade de database
   - Alertas de latência alta
   - Alertas de falhas de workflow

3. **Otimização**
   - Ajustar intervalos de coleta conforme necessidade
   - Monitorar uso de recursos
   - Implementar retenção de métricas

4. **Segurança**
   - Implementar autenticação no Pushgateway
   - Configurar TLS/SSL
   - Restringir acesso via firewall

---

## 📚 Documentação

### Documentos Criados:
1. **`n8n-monitoring-local/collector-api/PROMETHEUS_SETUP.md`**
   - Guia completo de configuração do Prometheus
   - Troubleshooting
   - Exemplos de queries

2. **`n8n-tuning/.secrets/credentials.template.json`**
   - Template atualizado com configurações Prometheus

3. **`n8n-monitoring-local/collector-api/.env.example`**
   - Template de variáveis de ambiente

### Scripts de Teste:
- `n8n-tuning/scripts/test_prometheus_connection.py`
- Validação completa da integração

---

## 🛠️ Comandos Úteis

### Verificar Status:
```bash
# Status do Pushgateway
curl http://wfdb01.vya.digital:9091/

# Métricas do N8N
curl http://wfdb01.vya.digital:9091/metrics | grep n8n

# Métricas do Collector API
curl http://wfdb01.vya.digital:9091/metrics | grep collector_api
```

### Deletar Métricas (se necessário):
```bash
# Deletar todas as métricas de um job
curl -X DELETE http://wfdb01.vya.digital:9091/metrics/job/n8n_metrics
curl -X DELETE http://wfdb01.vya.digital:9091/metrics/job/n8n_node_metrics
curl -X DELETE http://wfdb01.vya.digital:9091/metrics/job/collector_api
```

### Logs:
```bash
# Collector API logs
docker logs collector-api | grep prometheus

# Ver última execução dos scripts
tail -f n8n-tuning/logs/cron_node_metrics.log
```

---

## ⚠️ Notas Importantes

1. **Compatibilidade**: Ambos os backends (Victoria Metrics e Prometheus) continuam funcionando. Você pode escolher qual usar via parâmetro `--backend`.

2. **Default**: Por padrão, os scripts agora usam **prometheus** como backend.

3. **Migração Suave**: Não há breaking changes. O código anterior continua funcionando.

4. **Performance**: O push de métricas é assíncrono e não bloqueia a aplicação.

5. **Fallback**: Se o Pushgateway estiver indisponível, os erros são logados mas o serviço continua funcionando.

---

## 📞 Contato

Para dúvidas ou problemas, consulte:
- Documentação do Prometheus: https://prometheus.io/docs/
- Documentação do Pushgateway: https://github.com/prometheus/pushgateway
- Arquivo `PROMETHEUS_SETUP.md` para guia detalhado
