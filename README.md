# 🐳 Enterprise Python Analysis

**Análise e Otimização de Infraestrutura Docker + Monitoramento N8N**

**Última Atualização**: 17/03/2026 19:00 | **Sessão**: 2026-03-17 (encerrada)

---

## 🎯 Objetivo

Análise técnica de 4 servidores Docker em produção para identificar oportunidades de consolidação e redução de custos através do desligamento de servidor subutilizado.

## 📊 Resultado

✅ **Servidor Identificado**: `wf005.vya.digital`
💰 **Economia Projetada**: R$ 7,800-12,600/ano
📈 **Redução**: 25% de servidores (4→3)
⏱️ **ROI**: < 1 mês

## 📈 Status Atual

| Módulo | Status | Progresso |
|---|---|---|
| Análise Infraestrutura | ✅ Completo | 100% |
| Plano de Migração | ✅ Completo | 100% |
| Integração Prometheus | ✅ Completo | 100% |
| **ANA-001 N8N Analyzer** | ✅ **Implementado** | **100%** |
| Grafana Dashboards N8N | ⚠️ Sem dados | 50% |
| Deploy N8N Collector | ⏳ Pendente | 0% |
| Execução Migração wf005 | ⏳ Pendente | 0% |

---

## 📦 Projetos Relacionados

> ⚠️ **Os coletores e módulos de observability foram migrados para o projeto [`enterprise-observability`](../enterprise-observability/)**

| Componente | Destino | Data |
|---|---|---|
| `n8n-prometheus-wfdb01/` (collector-api, ping-service, deploy) | `../enterprise-observability/` | fev/2026 |
| `n8n-tuning/` (scripts de análise N8N) | `../enterprise-observability/` | mar/2026 |
| `wfdb01-docker-folder/` (volume SSHFS) | Removida (pasta vazia) | 17/03/2026 |

**Este repositório mantém**: análise de infraestrutura Docker, plano de migração wf005, scripts de análise e documentação de sessões.

---

## 🚀 Quick Start

### 1. Análise de Performance N8N (ANA-001)
```bash
# Instalar CLI
pip install -e .

# Dry-run (sem conectividade necessária)
analyze-n8n --dry-run --from 2026-01-01 --to 2026-01-31

# Análise real (requer VictoriaMetrics acessível)
analyze-n8n --from 2026-01-01 --to 2026-01-31 --output-format markdown
```

### 2. Análise Docker
```bash
python scripts/docker_analyzer.py
```

### 3. Gerar Relatório
```bash
python scripts/generate_report.py
```

### 4. Ver Documentação
```bash
cat docs/SUMMARY.md
```

---

## 🤖 ANA-001 — N8N Performance Analyzer

CLI tool que consulta VictoriaMetrics + Loki e gera relatórios de performance N8N com classificação de causa raiz.

```bash
analyze-n8n [OPTIONS]
  --from DATETIME        Início do período (ISO 8601 / YYYY-MM-DD)
  --to DATETIME          Fim do período
  --output-format        markdown|json [default: markdown]
  --output-dir DIR       Pasta de saída [default: reports/]
  --step-global DURATION Step fase global [default: 5m]
  --dry-run              Mostrar configuração sem executar
```

**Labels de causa raiz**: `QUEUE_DEPTH_SPIKE`, `DB_SLOW_QUERY`, `EXTERNAL_API_TIMEOUT`, `NETWORK_LATENCY`, `N8N_INTERNAL_ERROR`, `UNKNOWN`

**Status**: ✅ 40/40 tasks implementados — aguardando deploy de infra para run em produção

---

## 📁 Estrutura do Projeto

```
enterprise-python-analysis/
├── docs/                   # 📚 Documentação completa
│   ├── SUMMARY.md          # Sumário executivo
│   ├── INDEX.md            # Índice navegável
│   ├── TODO.md             # Lista de tarefas
│   ├── sessions/           # Relatórios de sessões
│   ├── N8N/                # Documentação N8N
│   └── Prometheus/         # Documentação Prometheus
├── src/n8n_analyzer/       # 🤖 ANA-001 N8N Analyzer
│   ├── analyzers/          # Latency, Correlation, Geographic, Loki
│   ├── collectors/         # VictoriaMetrics, Loki
│   ├── reporters/          # Markdown, JSON
│   ├── models/             # Pydantic v2 models
│   └── cli.py              # analyze-n8n CLI
├── scripts/                # 🔧 Scripts Python
├── specs/                  # 📐 Especificações ANA-001
├── reports/                # 📈 Relatórios gerados
├── data/                   # 📊 Dados de entrada
└── migration_plan.json     # 🗺️ Plano de migração
```

---

## 📋 Servidores Analisados

| Servidor | Containers | CPU % | RAM GB | Status |
|----------|-----------|-------|--------|--------|
| wf001 | 22 | 12.52% | ~11 | ✅ Target |
| wf002 | 7 | 11.85% | ~10 | ✅ Target |
| wf005 | 13 | 6.32% | 4.81 | 🎯 **Desligar** |
| wf006 | 8 | 54.66% | 12.78 | ⚠️ Alta carga |

---

## 🗺️ Plano de Migração

### wf005 → wf001 (8 containers)
- n8n, rabbitmq, minio, redis
- grafana, prometheus, loki, temporal

### wf005 → wf002 (5 containers)
- caddy, postgres, waha, keycloak, metabase

**Impacto Projetado**:
- wf001: 12.52% → 18.25% CPU (+5.73%)
- wf002: 11.85% → 12.44% CPU (+0.59%)
- Margem livre: >80% em ambos

---

## 🔧 Ferramentas Criadas

### docker_analyzer.py
Análise automatizada de recursos Docker:
- Processa JSONs de métricas
- Identifica servidor subutilizado
- Gera plano de migração balanceado

### generate_report.py
Gerador de relatórios markdown:
- Compara servidores
- Lista containers com detalhes
- Inclui volumes e bind mounts

### docker_compose_ports_scanner.py
Scanner de conflitos de portas:
- Busca compose files recursivamente
- Detecta conflitos de portas
- Export para CSV

---

## 📚 Documentação

Toda a documentação está em [`docs/`](docs/):

- **[SUMMARY.md](docs/SUMMARY.md)** - Visão geral executiva
- **[INDEX.md](docs/INDEX.md)** - Índice completo do projeto
- **[TODO.md](docs/TODO.md)** - Lista de tarefas pendentes
- **[Sessions](docs/sessions/)** - Relatórios detalhados de sessões

---

## ✅ Próximas Ações

### Esta Semana (Prioridade ALTA)
- [ ] Aprovar plano de migração
- [ ] Agendar janela de manutenção
- [ ] Backup completo de wf005
- [ ] Executar port scanner

### Próxima Semana
- [ ] Migrar containers críticos
- [ ] Monitorar por 72h
- [ ] Desligar wf005

---

## 💡 Status do Projeto

**Fase Atual**: ✅ ANA-001 Completo — Deploy N8N Pendente
**Próxima Fase**: Deploy Collector-API N8N + Run `analyze-n8n` em produção
**Data da Análise**: 16/01/2026
**Última Sessão**: 17/03/2026 (encerrada — 40/40 tasks ANA-001 completos)
**Confiança**: Alta (baseada em dados sólidos)

---

## 📞 Contatos

**Servidores**:
- wf001.vya.digital - Target (87% livre)
- wf002.vya.digital - Target (88% livre)
- wf005.vya.digital - Source (desligar)
- wf006.vya.digital - Não mexer

**Database**: wfdb02.vya.digital:5432
**Credenciais**: `.secrets/postgresql_destination_config.json`

---

## 📊 Métricas

- **Total de Containers Analisados**: 50
- **Servidores**: 4
- **Scripts Python Criados**: 3
- **Documentos Gerados**: 7
- **Tempo de Análise**: ~5 horas
- **Economia Projetada**: R$ 7,800-12,600/ano

---

**Última Atualização**: 16/01/2026 20:50
**Versão**: 1.0
**Status**: ✅ Pronto para Execução
