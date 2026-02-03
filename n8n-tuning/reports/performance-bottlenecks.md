# N8N Performance Analysis - Identificação de Gargalos

**Data da Análise**: 2026-02-03
**Período Analisado**: Últimas 200 execuções

## 📊 Resumo Executivo

- **Total de Workflows**: 100
- **Workflows Ativos**: 55
- **Total de Execuções Analisadas**: 200
- **Workflows com Métricas de Duração**: 5

## 🐌 Top 5 Workflows Mais Lentos (Gargalos de Performance)

| Workflow | Duração Média | Execuções | Observação |
|----------|---------------|-----------|------------|
| unknown | 6.09s | 1 | ⚠️ Nome não identificado - necessita investigação |
| hub-whatsapp-api-validate-client | 4.82s | 1 | API WhatsApp - validação de cliente |
| hub-whatsapp-api-validate-reseller | 4.68s | 1 | API WhatsApp - validação de reseller |
| unknown | 1.15s | 1 | ⚠️ Nome não identificado |
| 121Labs PABX call-analytics | 1.07s | 196 | **GARGALO CRÍTICO**: Alto volume + duração moderada |

## 🔥 Top 5 Workflows Mais Executados (Volume)

| Workflow | Execuções | % do Total | Status |
|----------|-----------|------------|--------|
| 121Labs PABX call-analytics | 196 | 98% | ⚠️ ALTO VOLUME |
| hub-whatsapp-api-validate-client | 1 | 0.5% | OK |
| hub-whatsapp-api-validate-reseller | 1 | 0.5% | OK |
| unknown | 1 | 0.5% | ⚠️ Identificação necessária |
| unknown | 1 | 0.5% | ⚠️ Identificação necessária |

## 🎯 Principais Gargalos Identificados

### 1. **CRÍTICO**: 121Labs PABX call-analytics
- **Problema**: Responsável por 98% das execuções analisadas
- **Duração**: 1.07s por execução
- **Impacto Total**: ~209s (3min 29s) de processamento nas últimas 200 execuções
- **Recomendações**:
  - ✅ Prioridade ALTA: Otimizar este workflow
  - Investigar possibilidade de processamento em batch
  - Avaliar cache de resultados repetidos
  - Verificar queries ao banco de dados
  - Considerar índices nas tabelas envolvidas

### 2. **MÉDIO**: hub-whatsapp-api-validate-client (4.82s)
- **Problema**: Duração individual alta (quase 5 segundos)
- **Causa Provável**: Chamadas externas à API do WhatsApp
- **Recomendações**:
  - Implementar timeout mais agressivo
  - Avaliar necessidade de todas as validações
  - Considerar cache de validações recentes

### 3. **MÉDIO**: hub-whatsapp-api-validate-reseller (4.68s)
- **Problema**: Similar ao anterior
- **Recomendações**: Mesmas do item #2

### 4. **ATENÇÃO**: Workflows "unknown"
- **Problema**: 2 workflows não estão sendo identificados corretamente
- **Causa Provável**: Workflows deletados ou execuções órfãs
- **Recomendação**: Limpeza de dados históricos

## 📈 Métricas Disponíveis no Victoria Metrics

As seguintes métricas estão sendo coletadas e podem ser visualizadas no Grafana:

1. `n8n_workflows_total` - Total de workflows
2. `n8n_workflows_active` - Workflows ativos
3. `n8n_executions_total` - Total de execuções
4. `n8n_success_rate_percent` - Taxa de sucesso global
5. `n8n_workflow_executions_total{workflow_name}` - Execuções por workflow
6. `n8n_workflow_executions_success{workflow_name}` - Execuções bem-sucedidas
7. `n8n_workflow_executions_failed{workflow_name}` - Execuções falhadas
8. `n8n_workflow_execution_duration_seconds{workflow_name}` - Duração média
9. `n8n_workflow_info{workflow_name}` - Informações do workflow

## 🔍 Queries PromQL Úteis

### Top 10 Workflows Mais Lentos
```promql
topk(10, n8n_workflow_execution_duration_seconds)
```

### Top 10 Workflows Mais Executados
```promql
topk(10, n8n_workflow_executions_total)
```

### Taxa de Sucesso por Workflow
```promql
(n8n_workflow_executions_success / n8n_workflow_executions_total) * 100
```

### Workflows com Falhas
```promql
n8n_workflow_executions_failed > 0
```

### Tempo Total de Processamento por Workflow
```promql
n8n_workflow_execution_duration_seconds * n8n_workflow_executions_total
```

## 🚀 Próximos Passos

1. ✅ **IMEDIATO**: Analisar código do workflow "121Labs PABX call-analytics"
2. ⏳ **CURTO PRAZO**: Implementar cache/otimizações
3. ⏳ **MÉDIO PRAZO**: Aumentar período de coleta para 1000+ execuções
4. ⏳ **MÉDIO PRAZO**: Configurar alertas automáticos para workflows lentos
5. ⏳ **LONGO PRAZO**: Automatizar coleta via cron (5 em 5 minutos)

## 📊 Dashboard Grafana

Dashboard disponível em: http://localhost:3100/d/n8n-performance-detailed

Inclui:
- Métricas gerais (totais, success rate)
- Top 10 workflows mais executados
- Top 10 workflows mais lentos
- Distribuição de durações
- Taxa de sucesso por workflow
- Falhas por workflow

---

**Nota**: Este relatório é baseado nas últimas 200 execuções. Para análise mais precisa, recomenda-se aumentar o período de coleta e executar o exporter periodicamente.
