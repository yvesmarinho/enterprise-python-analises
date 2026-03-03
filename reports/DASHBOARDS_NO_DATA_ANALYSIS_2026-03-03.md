# 🔍 ANÁLISE: Dashboards N8N Sem Dados
## Data: 03/03/2026 | Hora: 16:15

---

## 📊 SITUAÇÃO ATUAL

### ✅ O Que Está Funcionando

1. **Dashboards Deployados Corretamente**
   - ✅ 3 dashboards N8N instalados em wfdb01
   - ✅ Grafana carregou os dashboards sem erros
   - ✅ Datasource "VictoriaMetrics" configurado (UID: `victoriametrics`)
   - ✅ Logs do Grafana sem erros

   ```
   logger=live msg="Initialized channel handler"
     channel=grafana/dashboard/uid/n8n-performance-overview
     channel=grafana/dashboard/uid/n8n-performance-detailed
     channel=grafana/dashboard/uid/n8n-node-analysis
   ```

2. **Infraestrutura N8N Ativa**
   - ✅ 8 containers N8N rodando no wf001 (editor, webhooks, workers, mcp)
   - ✅ Collector-api rodando (Up 3 weeks, healthy)
   - ✅ Variáveis de ambiente N8N configuradas:
     - `N8N_URL=https://workflow.vya.digital/`
     - `N8N_API_KEY=<valid JWT token>`

3. **VictoriaMetrics Operacional**
   - ✅ Endpoint API respondendo
   - ✅ Prometheus scraping configurado

---

## ❌ PROBLEMA IDENTIFICADO

### Métricas N8N Não Existem no VictoriaMetrics

**Comando de Verificação**:
```bash
ssh-wfdb01 "curl -s 'http://victoria-metrics:8428/api/v1/label/__name__/values' | grep n8n"
# Resultado: (vazio)
```

**Consequência**: Dashboards N8N mostram "No data" porque não há métricas `n8n_*` disponíveis.

---

## 🔍 CAUSA RAIZ

### Módulo N8N Não Está no Container de Produção

**Timeline do Problema**:

| Data | Evento | Status |
|------|---------|--------|
| **06/02/2026** | Imagem Docker buildada e enviada ao Hub | ✅ `adminvyadigital/n8n-collector-api:latest` |
| **06/02/2026** | Container `prod-collector-api` criado no wf001 | ✅ Rodando (Up 3 weeks) |
| **09/02/2026** | Módulo N8N desenvolvido (641 linhas) | ✅ Código pronto |
| **09/02/2026** | ⚠️ **IMAGEM NÃO FOI RECRIADA** | ❌ Docker Hub desatualizado |
| **03/03/2026** | Deploy dashboards sem métricas | ❌ "No data" |

### Verificação no Container

```bash
# Verificar se módulo N8N existe no container atual
ssh-wf001 "docker exec prod-collector-api curl -s http://localhost:9102/metrics | grep n8n"
# Resultado: (vazio) ❌

ssh-wf001 "docker logs prod-collector-api --tail 50 | grep -i n8n"
# Resultado: (vazio) ❌
```

**Conclusão**: Container rodando versão antiga do código **SEM módulo N8N**.

---

## 📂 CÓDIGO DISPONÍVEL (Local)

### Módulo N8N Completo e Testado

```
n8n-prometheus-wfdb01/collector-api/
├── Dockerfile                          ✅ Pronto
├── requirements.txt                    ✅ Atualizado
├── src/
│   ├── main.py                        ✅ Integração N8N pronta (linha 14-67)
│   ├── config.py                      ✅ Configuração N8N (linha 16-17)
│   └── n8n/
│       ├── __init__.py                ✅ Exports configurados
│       ├── n8n_client.py              ✅ Cliente HTTP N8N
│       ├── n8n_collector.py           ✅ Coletor (296 linhas)
│       └── n8n_metrics.py             ✅ 9 métricas Prometheus
```

### Métricas Implementadas (9 total)

```python
# Workflow Metrics
n8n_workflow_executions_total          # Counter
n8n_workflow_executions_success        # Counter
n8n_workflow_executions_failed         # Counter
n8n_workflow_active_status             # Gauge
n8n_workflow_execution_duration_seconds # Histogram

# Node Metrics
n8n_node_execution_duration_seconds    # Histogram
n8n_node_execution_errors              # Counter

# API Metrics
n8n_api_total_workflows                # Gauge
n8n_api_active_workflows               # Gauge
n8n_api_execution_count                # Gauge
```

### Integração no main.py

```python
# Código presente - linhas 47-67
if settings.n8n_api_key and settings.n8n_url:
    logger.info("n8n_collector_enabled")

    n8n_client = N8NClient(
        base_url=settings.n8n_url,
        api_key=settings.n8n_api_key
    )

    n8n_collector = N8NCollector(client=n8n_client)

    n8n_task = asyncio.create_task(
        n8n_collector.run_periodic_collection(settings.db_probe_interval)
    )
```

---

## ✅ SOLUÇÃO

### Fase 1: Rebuild e Push da Imagem Docker (10 min)

```bash
# 1. Navegar para diretório do collector
cd n8n-prometheus-wfdb01/collector-api

# 2. Build nova imagem com módulo N8N
docker build -t adminvyadigital/n8n-collector-api:latest .

# 3. Verificar que imagem foi criada
docker images | grep n8n-collector-api

# 4. Push para Docker Hub
docker push adminvyadigital/n8n-collector-api:latest

# 5. Confirmar push
docker pull adminvyadigital/n8n-collector-api:latest
```

**Resultado Esperado**: Imagem no Docker Hub com módulo N8N

---

### Fase 2: Deploy no Servidor wf001 (10 min)

```bash
# 1. Conectar ao servidor
ssh-wf001

# 2. Pull nova imagem
docker pull adminvyadigital/n8n-collector-api:latest

# 3. Verificar nova imagem
docker images | grep n8n-collector-api

# 4. Backup configuração (opcional)
docker inspect prod-collector-api > ~/prod-collector-api-backup.json

# 5. Restart container (aplica nova imagem)
docker restart prod-collector-api

# 6. Aguardar healthcheck (30s)
sleep 30

# 7. Verificar status
docker ps | grep prod-collector-api
# Deve mostrar: Up X seconds (healthy)
```

---

### Fase 3: Validação da Coleta (5 min)

```bash
# 1. Verificar logs de inicialização
docker logs prod-collector-api --tail 100 | grep -i n8n
# Deve mostrar: "n8n_collector_enabled"

# 2. Verificar métricas expostas
docker exec prod-collector-api curl -s http://localhost:9102/metrics | grep n8n_
# Deve retornar ~30 linhas com métricas n8n_*

# 3. Exemplo de métricas esperadas:
# n8n_workflow_executions_total{workflow_id="...",workflow_name="...",status="success"} 42
# n8n_workflow_active_status{workflow_id="...",workflow_name="..."} 1.0
# n8n_node_execution_duration_seconds_bucket{...} 0.156
```

---

### Fase 4: Validação no VictoriaMetrics (5 min)

```bash
# 1. Aguardar 1 ciclo de scrape (30-60s)
sleep 60

# 2. Verificar métricas no VictoriaMetrics
ssh-wfdb01 "curl -s 'http://victoria-metrics:8428/api/v1/label/__name__/values' | grep n8n"

# Deve retornar:
# n8n_workflow_executions_total
# n8n_workflow_active_status
# n8n_node_execution_duration_seconds
# ... (9 métricas base)

# 3. Query específica de teste
ssh-wfdb01 "curl -s 'http://victoria-metrics:8428/api/v1/query?query=n8n_workflow_active_status' | jq"

# Deve retornar JSON com dados dos workflows ativos
```

---

### Fase 5: Validação nos Dashboards Grafana (5 min)

1. **Acessar Grafana**
   - URL: http://wfdb01.vya.digital:3002
   - Login: admin

2. **Abrir Dashboard N8N Performance Overview**
   - Navegar: Dashboards → Browse → N8N/
   - Abrir: "N8N Performance Overview"

3. **Verificar Painéis Populados**
   - ✅ **Total Executions**: Deve mostrar número (não "No data")
   - ✅ **Success Rate**: Deve mostrar % (ex: 95.2%)
   - ✅ **Total Workflows**: Deve mostrar count
   - ✅ **Active Workflows**: Deve mostrar count
   - ✅ **Avg Duration**: Deve mostrar tempo (segundos)
   - ✅ **Top 5 Slowest Workflows**: Deve mostrar tabela

4. **Repetir para Outros Dashboards**
   - N8N Performance Detailed (12 painéis)
   - N8N Node Performance (3-4 painéis)

---

## 📊 MÉTRICAS DE SUCESSO

| Validação | Critério | Como Verificar |
|-----------|----------|----------------|
| **Imagem Atualizada** | SHA diferente no Docker Hub | `docker images` |
| **Container Atualizado** | Created = hoje | `docker inspect prod-collector-api` |
| **Módulo Inicializado** | Log "n8n_collector_enabled" | `docker logs` |
| **Métricas Expostas** | >20 linhas com `n8n_` | `/metrics` endpoint |
| **VictoriaMetrics** | 9 métricas N8N listadas | API query |
| **Grafana** | Painéis com dados (não "No data") | UI visual |

---

## 🎯 RESULTADOS ESPERADOS

### Antes (Atual)
```
Grafana N8N Dashboards:  "No data" em todos os painéis ❌
VictoriaMetrics:         0 métricas n8n_* ❌
Collector container:     Versão antiga (06/02) ❌
```

### Depois (Pós Deploy)
```
Grafana N8N Dashboards:  Dados populados ✅
VictoriaMetrics:         9 métricas n8n_* ✅
Collector container:     Versão nova (03/03) ✅
```

---

## ⏱️ TEMPO ESTIMADO

| Fase | Atividade | Tempo |
|------|-----------|-------|
| 1 | Build + Push Docker | 10 min |
| 2 | Deploy wf001 | 10 min |
| 3 | Validação Coleta | 5 min |
| 4 | Validação VictoriaMetrics | 5 min |
| 5 | Validação Grafana | 5 min |
| **TOTAL** | | **35 min** |

---

## 🔄 ROLLBACK (Se Necessário)

Caso algo dê errado após o deploy:

```bash
# 1. Conectar ao servidor
ssh-wf001

# 2. Ver qual imagem está sendo usada
docker inspect prod-collector-api | grep Image

# 3. Se necessário, voltar para versão anterior
# (Não recomendado - versão antiga não tem módulo N8N)

# 4. Alternativa: Desabilitar módulo N8N temporariamente
docker exec prod-collector-api sh -c "unset N8N_API_KEY && docker restart prod-collector-api"
```

---

## 📞 PRÓXIMOS PASSOS

### Imediatos (Hoje)
1. ✅ **Análise concluída** - Problema identificado
2. ⏳ **Obter aprovação** para rebuild + deploy
3. ⏳ **Executar Fases 1-5** conforme documentado

### Curto Prazo
1. Configurar CI/CD para build automático
2. Adicionar testes de integração
3. Monitorar performance do coletor
4. Configurar alertas para métricas N8N

---

## 📝 NOTAS IMPORTANTES

1. **Credenciais**: N8N_API_KEY válido já configurado no container
2. **API N8N**: Endpoint https://workflow.vya.digital/ acessível
3. **Downtime**: ~30 segundos durante restart do container
4. **Impacto**: Nenhum (collector não afeta N8N em execução)
5. **Reversibilidade**: Alta (restart reverte para versão em memória)

---

## 📚 REFERÊNCIAS

**Documentos**:
- [SESSION_RECOVERY_2026-03-03.md](.docs/sessions/2026-03-03/SESSION_RECOVERY_2026-03-03.md)
- [DEPLOY_COMPLETED_2026-03-03.md](DEPLOY_COMPLETED_2026-03-03.md)

**Código Fonte**:
- [n8n_collector.py](../n8n-prometheus-wfdb01/collector-api/src/n8n/n8n_collector.py)
- [main.py](../n8n-prometheus-wfdb01/collector-api/src/main.py)
- [Dockerfile](../n8n-prometheus-wfdb01/collector-api/Dockerfile)

---

*Análise concluída em 03/03/2026 às 16:15*
*Agente: GitHub Copilot | Modelo: Claude Sonnet 4.5*
