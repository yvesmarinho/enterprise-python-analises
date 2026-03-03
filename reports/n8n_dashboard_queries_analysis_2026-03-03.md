# Análise de Queries dos Dashboards N8N
**Data:** 2026-03-03
**Servidor:** wfdb01 (VictoriaMetrics)

## Resumo Executivo

Todas as queries do dashboard **N8N Performance Overview** estão usando nomes de métricas **INCORRETOS** que não existem no VictoriaMetrics. Isso explica por que os dashboards não exibem dados.

## 1. Queries Extraídas do Dashboard

### Dashboard: N8N Performance Overview

| Panel | Query Atual (Incorreta) |
|-------|--------------------------|
| Total Executions | `n8n_executions_total` |
| Success Rate | `n8n_success_rate_percent` |
| Total Workflows | `n8n_workflows_total` |
| Active Workflows | `n8n_workflows_active` |
| Avg Execution Duration by Workflow | `n8n_workflow_execution_duration_seconds{workflow_name!="unknown"}` |
| Top 10 Slowest Workflows | `topk(10, n8n_workflow_execution_duration_seconds{workflow_name!="unknown"})` |

**Total de queries:** 6

## 2. Métricas N8N Disponíveis no VictoriaMetrics

```
Total de métricas N8N: 14

n8n_api_request_created
n8n_api_request_duration_seconds_bucket
n8n_api_request_duration_seconds_count
n8n_api_request_duration_seconds_created
n8n_api_request_duration_seconds_sum
n8n_api_request_total
n8n_workflow_active_status
n8n_workflow_execution_duration_seconds_bucket
n8n_workflow_execution_duration_seconds_count
n8n_workflow_execution_duration_seconds_created
n8n_workflow_execution_duration_seconds_sum
n8n_workflow_execution_status
n8n_workflow_executions_created
n8n_workflow_executions_total
```

## 3. Análise de Disponibilidade de Queries

| Query do Dashboard | Status | Séries |
|-------------------|--------|---------|
| `n8n_executions_total` | ✗ NÃO EXISTE | 0 |
| `n8n_success_rate_percent` | ✗ NÃO EXISTE | 0 |
| `n8n_workflows_total` | ✗ NÃO EXISTE | 0 |
| `n8n_workflows_active` | ✗ NÃO EXISTE | 0 |
| `n8n_workflow_execution_duration_seconds` | ✗ NÃO EXISTE | 0 |

### Métricas Disponíveis com Dados

| Métrica Real | Séries |
|-------------|---------|
| `n8n_workflow_executions_total` | 14 |
| `n8n_workflow_execution_status` | 12 |
| `n8n_workflow_active_status` | 300 |

## 4. Mapeamento de Correção de Queries

### 4.1 Total Executions
**Query Incorreta:**
```promql
n8n_executions_total
```

**Query Correta:**
```promql
sum(n8n_workflow_executions_total)
```

**Teste:**
- Status: ✓ SUCCESS
- Séries retornadas: 14

---

### 4.2 Success Rate
**Query Incorreta:**
```promql
n8n_success_rate_percent
```

**Query Correta (calculada):**
```promql
(sum(n8n_workflow_execution_status{status="success"}) / sum(n8n_workflow_execution_status)) * 100
```

**Alternativa (taxa de sucesso):**
```promql
sum(rate(n8n_workflow_execution_status{status="success"}[5m])) / sum(rate(n8n_workflow_execution_status[5m])) * 100
```

---

### 4.3 Total Workflows
**Query Incorreta:**
```promql
n8n_workflows_total
```

**Query Correta:**
```promql
count(count by (workflow_name) (n8n_workflow_executions_total))
```

**Alternativa:**
```promql
count(n8n_workflow_active_status)
```

---

### 4.4 Active Workflows
**Query Incorreta:**
```promql
n8n_workflows_active
```

**Query Correta:**
```promql
sum(n8n_workflow_active_status{status="active"})
```

**Alternativa (contar workflows ativos):**
```promql
count(n8n_workflow_active_status == 1)
```

---

### 4.5 Avg Execution Duration by Workflow
**Query Incorreta:**
```promql
n8n_workflow_execution_duration_seconds{workflow_name!="unknown"}
```

**Query Correta (contador de histograma):**
```promql
n8n_workflow_execution_duration_seconds_bucket{workflow_name!="unknown"}
```

**Query Correta (média calculada):**
```promql
sum by (workflow_name) (rate(n8n_workflow_execution_duration_seconds_sum[5m]))
/
sum by (workflow_name) (rate(n8n_workflow_execution_duration_seconds_count[5m]))
```

---

### 4.6 Top 10 Slowest Workflows
**Query Incorreta:**
```promql
topk(10, n8n_workflow_execution_duration_seconds{workflow_name!="unknown"})
```

**Query Correta:**
```promql
topk(10,
  sum by (workflow_name) (rate(n8n_workflow_execution_duration_seconds_sum[5m]))
  /
  sum by (workflow_name) (rate(n8n_workflow_execution_duration_seconds_count[5m]))
)
```

---

## 5. Testes de Validação

### 5.1 Query com Rate (funciona)
```bash
Query: rate(n8n_workflow_executions_total[5m])
Status: ✓ success
Result Count: 14
Has Data: True
```

### 5.2 Métricas Testadas
```
n8n_workflow_executions_total: 14 séries
n8n_workflow_execution_status: 12 séries
n8n_workflow_active_status: 300 séries
```

## 6. Problema Identificado

### Causa Raiz
Os dashboards foram criados com nomes de métricas **customizadas/calculadas** que não correspondem às métricas **reais** exportadas pelo N8N Prometheus Exporter.

### Impacto
- ✗ **100% dos painéis** no dashboard Overview não exibem dados
- ✗ Queries retornam `success` mas com **0 resultados**
- ✗ Métricas reais existem mas não são consultadas

## 7. Ações Corretivas Necessárias

### Prioridade ALTA
1. **Atualizar todas as queries** do dashboard `n8n-performance-overview.json` com as queries corrigidas acima
2. **Testar cada painel** após a correção para validar dados
3. **Verificar e corrigir** os outros dashboards N8N:
   - `n8n-performance-detailed.json`
   - `n8n-node-performance-analysis.json`

### Prioridade MÉDIA
4. Criar queries para métricas não utilizadas:
   - `n8n_api_request_total`
   - `n8n_api_request_duration_seconds_*`

### Prioridade BAIXA
5. Documentar padrões de nomenclatura de métricas N8N
6. Criar alertas baseados nas métricas corretas

## 8. Script de Correção Automática

```bash
# No servidor wfdb01
cd /opt/docker_user/enterprise-observability/grafana/dashboards/N8N

# Backup
cp n8n-performance-overview.json n8n-performance-overview.json.bak

# Aplicar correções usando sed
sed -i 's/"expr":"n8n_executions_total"/"expr":"sum(n8n_workflow_executions_total)"/g' n8n-performance-overview.json
sed -i 's/"expr":"n8n_workflows_active"/"expr":"sum(n8n_workflow_active_status{status=\\"active\\"})"/g' n8n-performance-overview.json

# Recarregar dashboards no Grafana
curl -X POST http://localhost:3000/api/admin/provisioning/dashboards/reload
```

## 9. Conclusão

**Status:** ✗ TODAS AS QUERIES INCORRETAS
**Ação:** CORREÇÃO URGENTE NECESSÁRIA
**Impacto:** Dashboards não funcionais
**Solução:** Aplicar mapeamento de queries corrigidas

---

**Próximos Passos:**
1. Aplicar correções no arquivo JSON do dashboard
2. Validar queries corrigidas uma a uma
3. Atualizar outros dashboards N8N com as mesmas correções
4. Documentar métricas corretas para futuras referências
