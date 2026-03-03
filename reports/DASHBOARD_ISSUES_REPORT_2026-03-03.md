# 🚨 LEVANTAMENTO DE PROBLEMAS - Dashboards Grafana
**Data**: 03/03/2026
**Análise**: Completa
**Status**: 🔴 CRÍTICO - Múltiplos dashboards não funcionais

---

## 📊 RESUMO EXECUTIVO

### Dashboards Analisados
- **Total**: 17 dashboards encontrados (com duplicatas)
- **✅ Funcionais**: 8 dashboards (PostgreSQL, MySQL, Docker)
- **❌ Com Problemas**: 9 dashboards (todos N8N)
- **Taxa de Falha**: 53% dos dashboards

### Problema Principal
**Dashboards N8N sem datasource configurado**: 21 painéis afetados

---

## 🔍 PROBLEMAS IDENTIFICADOS

### 1. ⚠️ Dashboards N8N Sem Datasource (CRÍTICO)

#### Dashboard: N8N Performance Overview
- **Arquivo**: `n8n-performance-overview.json`
- **Painéis Afetados**: 6 de 6 (100%)
- **Painéis com Problema**:
  - Total Executions
  - Success Rate
  - Total Workflows
  - Active Workflows
  - Execution Duration
  - Error Rate

**Causa**: Nenhum painel tem datasource configurado

---

#### Dashboard: N8N Performance Analysis (Detailed)
- **Arquivo**: `n8n-performance-detailed.json`
- **Painéis Afetados**: 12 de 12 (100%)
- **Painéis com Problema**:
  - Total Workflows
  - Active Workflows
  - Success Rate
  - Avg Execution Duration
  - Node Executions
  - Workflow Executions Timeline
  - API Requests
  - API Response Time
  - API Error Rate
  - Top Failing Workflows
  - Slowest Workflows
  - Error Distribution

**Causa**: Nenhum painel tem datasource configurado

---

#### Dashboard: N8N Node Performance Analysis
- **Arquivo**: `n8n-node-performance.json`
- **Painéis Afetados**: 3 de 4 (75%)
- **Painéis com Problema**:
  - Top 20 Slowest Nodes (Average Time)
  - Average Time by Node Type (milliseconds)
  - All Nodes Performance

**Causa**: Apenas 1 painel tem datasource, 3 sem configuração

**Problema Adicional**:
- Um dos arquivos usa UID incorreto: `P4169E866C3094E38` (de outro ambiente)

---

### 2. 🔑 Datasource Sem UID Explícito (ALTO)

**Arquivo**: `n8n-prometheus-wfdb01/infrastructure/grafana/provisioning/datasources/victoria-metrics.yml`

```yaml
datasources:
  - name: VictoriaMetrics
    type: prometheus
    access: proxy
    url: http://victoria-metrics:8428
    isDefault: true
    editable: false
    # ❌ PROBLEMA: Sem UID definido
```

**Impacto**:
- Grafana gera UID automaticamente a cada provisionamento
- UIDs podem mudar entre restarts
- Dashboards ficam desconfigurados se UID mudar

**UID Esperado nos Dashboards**: `prometheus` (minúsculo)

---

### 3. 📁 Dashboards Duplicados em Múltiplas Localizações (MÉDIO)

**Localizações Encontradas**:
1. `n8n-prometheus-wfdb01/grafana/dashboards/` (7 arquivos)
2. `n8n-prometheus-wfdb01/grafana_data/dashboards/` (7 arquivos)
3. `n8n-tuning/docker/grafana/dashboards/` (3 arquivos)

**Problema**: Mesmos dashboards em 3 locais diferentes, dificultando manutenção

**Dashboards Duplicados**:
- N8N Performance Overview (3 cópias)
- N8N Performance Detailed (3 cópias)
- N8N Node Performance (3 cópias)
- MySQL Dashboard (2 cópias)
- PostgreSQL Dashboard (2 cópias)
- Docker Monitoring (2 cópias)

---

### 4. 🔄 UIDs Inconsistentes (BAIXO)

**UIDs Encontrados**:
- ✅ `prometheus` - Usado em 8 dashboards funcionais
- ❌ `P4169E866C3094E38` - UID de outro ambiente (1 dashboard)
- ❌ (vazio) - Dashboards N8N sem datasource (9 dashboards)

---

## 📊 DASHBOARDS FUNCIONAIS (Referência)

### ✅ Sem Problemas:
1. **PostgreSQL Database** (`prometheus` UID)
   - 35 painéis, 32 com queries

2. **MySQL Dashboard** (2 versões, ambas OK)
   - Versão 1: 18 painéis, 13 com queries
   - Versão 2: 101 painéis, 94 com queries

3. **Docker Monitoring** (`prometheus` UID)
   - 8 painéis, 8 com queries

---

## 🎯 ANÁLISE DE IMPACTO

### Impacto nos Usuários
- ❌ **N8N Monitoring**: 100% não funcional (21 painéis vazios)
- ✅ **Database Monitoring**: 100% funcional (MySQL + PostgreSQL)
- ✅ **Container Monitoring**: 100% funcional (Docker)

### Métricas Afetadas
**N8N Metrics (Não Visíveis)**:
- `n8n_workflow_active_status`
- `n8n_workflow_executions_total`
- `n8n_workflow_execution_duration_seconds`
- `n8n_workflow_execution_status`
- `n8n_node_execution_duration_seconds`
- `n8n_node_execution_errors_total`
- `n8n_api_request_total`
- `n8n_api_request_duration_seconds`
- `n8n_api_request_errors_total`

### Criticidade
- 🔴 **CRÍTICA**: Dashboards N8N (monitoramento de workflows não funciona)
- 🟡 **MÉDIA**: Datasource sem UID (pode causar problemas futuros)
- 🟢 **BAIXA**: Dashboards duplicados (apenas organização)

---

## 📈 ESTATÍSTICAS

| Métrica | Valor |
|---------|-------|
| Dashboards únicos | ~7 diferentes |
| Dashboards duplicados | 17 arquivos |
| Painéis totais | ~196 painéis |
| Painéis funcionais | 175 painéis (89%) |
| Painéis quebrados | 21 painéis (11%) |
| Datasources únicos | 1 (VictoriaMetrics) |
| UIDs em uso | 2 (prometheus + P4169E866C3094E38) |

---

## 🔧 PRÓXIMOS PASSOS

Ver arquivo: `DASHBOARD_FIX_PLAN_2026-03-03.md` para lista completa de tarefas de correção.

---

**Relatório gerado por**: analyze_dashboards_issues.py
**Arquivo de análise**: reports/dashboard_analysis_2026-03-03.txt
