# 📑 INDEX - N8N Performance Tuning

**Projeto**: Análise e Otimização de Performance do N8N  
**Data de Início**: 02/02/2026  
**Última Atualização**: 2026-02-03  
**Status**: 🚀 Em Desenvolvimento - Monitoramento Ativo

---

## 🎯 Objetivo do Projeto

Analisar o sistema N8N em produção para identificar gargalos de performance e oportunidades de otimização, visando melhorar:
- Tempo de resposta dos workflows
- Utilização eficiente de recursos (CPU, Memória)
- Throughput de processamento
- Confiabilidade e estabilidade

**Servidor Atual**: wf005.vya.digital  
**Container**: n8n_n8n  
**Monitoramento**: Grafana (localhost:3100) + VictoriaMetrics (localhost:8428)

---

## 📊 Status Atual (03/02/2026)

### ✅ Implementado
- **Stack de Monitoramento**: Grafana 12.3.2 + VictoriaMetrics + Python Collector
- **Coleta de Métricas**: n8n_metrics_exporter.py (a cada 3 min)
- **Dashboards Criados**:
  - N8N Performance Overview
  - N8N Performance Detailed (Bottleneck Score Ranking)
  - N8N Node Performance (All Nodes Performance)
- **Métricas Coletadas**:
  - Execuções de workflow (total, taxa de sucesso/falha)
  - Duração de execução (média, P50, P95, P99)
  - Performance de nodes individuais
  - Bottleneck Score (duration × ln(executions))

### 🔧 Ajustes Realizados Hoje
- ✅ Corrigido gráfico "Bottleneck Score Ranking" (duplicatas removidas)
- ✅ Simplificado "Score Components" (single query)
- ✅ Adicionado sortBy em "All Nodes Performance"
- ✅ Configurado provisioning: allowUiUpdates=false, disableDeletion=true

### 🎯 Próximos Passos
Ver [NEXT_STEPS.md](NEXT_STEPS.md) para roadmap detalhado

---

## 📂 Estrutura do Projeto

```
n8n-tuning/
├── docs/                           # 📚 Documentação
│   ├── INDEX.md                    # Este arquivo - Índice geral
│   ├── TODO.md                     # Lista de tarefas
│   ├── NEXT_STEPS.md               # Roadmap de próximas features
│   ├── ANALYSIS_GUIDE.md           # Guia de análise
│   ├── METRICS_ALTERNATIVES.md     # Opções de métricas
│   └── sessions/                   # 📁 Documentação de sessões
│       └── YYYY-MM-DD/             # Pasta por data
│           ├── SESSION_RECOVERY_*.md
│           ├── SESSION_REPORT_*.md
│           ├── FINAL_STATUS_*.md
│           └── TODAY_ACTIVITIES_*.md
│
├── data/                           # 📊 Dados coletados
│   ├── metrics/                    # Métricas exportadas
│   ├── logs/                       # Logs de coleta
│   ├── workflows/                  # Exports de workflows (JSON)
│   └── database/                   # Análise de banco de dados
│
├── scripts/                        # 🔧 Scripts de coleta e análise
│   ├── n8n_metrics_collector.py   # Coleta de métricas via API
│   ├── workflow_analyzer.py       # Análise de workflows
│   └── credentials_helper.py      # Helper de credenciais
│
├── docker/                         # 🐳 Stack de monitoramento
│   ├── docker-compose.yml          # Grafana + VictoriaMetrics
│   ├── grafana/
│   │   ├── dashboards/             # JSON dos dashboards
│   │   └── provisioning/           # Configuração de provisioning
│   └── victoria-metrics/           # Dados do VictoriaMetrics
│
├── reports/                        # 📈 Relatórios gerados
│
└── README.md                       # Documentação inicial
```

---

## 🔍 Métricas e Análises

### 1. Bottleneck Score Ranking
**Fórmula**: `duration × ln(executions + 1) / ln(10)`

**Top Workflows (03/02/2026)**:
1. sdr_agent_planejados-v2: 12.18
2. hub-whatsapp-api-validate-reseller: 4.81
3. hub-whatsapp-api-validate-client: 4.34
4. hub-whatsapp-api-gateway-evolution-api: 3.77
5. 121Labs PABX call-analytics: 0.29

**Interpretação**: Workflows com score alto requerem atenção (alto tempo × alto volume)

### 2. Node Performance
**Nós mais lentos (tempo médio de execução)**:
1. Select rows from a table (setCacheReseller): 2684ms
2. Select rows from a table (validate-client): 1764ms
3. Select rows from a table (gateway): 1185ms
4. setCacheClient: 1143ms

**Ação**: Otimizar queries de banco de dados, considerar cache Redis

### 3. Taxa de Sucesso
- Taxa geral de sucesso dos workflows
- Identificação de workflows com falhas frequentes
- Análise de causas de falha

---

## 🎯 Métricas-Chave (KPIs)

### Performance
- **Tempo médio de execução**: < 5s (target)
- **Taxa de sucesso**: > 98%
- **Throughput**: workflows/minuto
- **Tempo de resposta**: P50, P95, P99

### Recursos
- **CPU Usage**: < 50% em operação normal
- **Memory Usage**: < 80% do limite
- **Disk I/O**: Monitorar picos

### Disponibilidade
- **Uptime**: > 99.5%
- **Error Rate**: < 2%
- **Recovery Time**: < 5min

---

## 🔗 Links Importantes

### Monitoramento
- **Grafana**: http://localhost:3100 (admin / W123Mudar)
- **VictoriaMetrics**: http://localhost:8428
- **N8N Metrics Endpoint**: http://wf005.vya.digital:5678/metrics

### Documentação
- [Guia de Análise](ANALYSIS_GUIDE.md)
- [TODO - Tarefas Pendentes](TODO.md)
- [Próximos Passos](NEXT_STEPS.md)
- [Alternativas de Métricas](METRICS_ALTERNATIVES.md)

### Repositórios
- N8N Docs: https://docs.n8n.io
- VictoriaMetrics: https://docs.victoriametrics.com
- Grafana: https://grafana.com/docs

---

## 📞 Contatos

**Responsável Técnico**: Yves Marinho  
**Servidor**: wf005.vya.digital  
**Ambiente**: Produção (cuidado com alterações)

---

**Última Sincronização**: 2026-02-03
