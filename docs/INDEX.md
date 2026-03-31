# 📑 INDEX - Enterprise Python Analysis

**Projeto**: Análise de Performance do N8N — Diagnóstico de Lentidão
**Última Atualização**: 31/03/2026
**Status**: ▶️ Sessão 2026-03-31 iniciada | ✅ Sessão 2026-03-30 encerrada | ✅ ANA001 concluída (sem violações p95 >= 1s no período analisado)

---

## 🎯 Objetivo do Projeto

> **⚠️ ESCOPO**: Este projeto é de **ANÁLISE APENAS**. Operações de deploy, migração de containers ou gerenciamento de servidores não são tratadas aqui.

**Problema a resolver**: Diagnosticar a **lentidão no N8N** — cada etapa de workflow levando ≥ 1 segundo para executar. Problema reportado desde **janeiro/2026**.

**Abordagem**: Consultar dados históricos do **Prometheus/VictoriaMetrics + Loki** usando a ferramenta `analyze-n8n` (ANA-001), identificar violações de latência, correlacionar com eventos de infraestrutura (Redis, PostgreSQL, APIs externas) e produzir relatório estruturado com causa raiz.

**Fontes de dados**:
- `Prometheus` (`https://prometheus.vya.digital`) — scraping engine, **15 dias de retenção**, público HTTPS. Dados disponíveis: **2026-03-04 → 2026-03-14** (10 dias, 68 séries, 2 instâncias).
- `VictoriaMetrics` (interno `http://victoriametrics:8428`) — **12 meses de retenção**, sem DNS público. Acesso via SSH SPA: `source .secrets/wfdb01_connection.sh && wfdb01_tunnel_vm`.
- `Loki` (`https://loki.vya.digital`) — logs de erro do N8N
- Dois pontos de coleta: **wf001** (USA) e **wf008** (Brasil) — estratégia geográfica deliberada para capturar delays distintos por região. Collectors já executando; código e deploy gerenciados em `../enterprise-observability/`.

---

## 📂 Estrutura do Projeto

```
enterprise-python-analysis/
├── docs/                           # 📚 Documentação (migrado de .docs/ em 17/03/2026)
│   ├── INDEX.md                    # Este arquivo
│   ├── TODO.md                     # Lista de tarefas
│   ├── TODAY_ACTIVITIES.md         # Log diário de atividades
│   ├── SUMMARY.md                  # Sumário executivo
│   ├── README.md                   # Guia de navegação
│   ├── N8N/                        # Documentação N8N
│   ├── Prometheus/                 # Documentação Prometheus + collector-api
│   └── sessions/                   # Documentação de sessões
│       ├── 2026-01-16/ … 2026-03-03/
│       ├── 2026-03-17/              # Sessão anterior
│       │   ├── SESSION_RECOVERY_2026-03-17.md
│       │   ├── TODAY_ACTIVITIES_2026-03-17.md
│       │   ├── SESSION_REPORT_2026-03-17.md
│       │   └── FINAL_STATUS_2026-03-17.md
│       ├── 2026-03-18/              # Sessão anterior
│       ├── 2026-03-30/              # Sessão encerrada
│       └── 2026-03-31/              # ⭐ Sessão atual
│           ├── SESSION_RECOVERY_2026-03-31.md
│           ├── TODAY_ACTIVITIES_2026-03-31.md
│           ├── SESSION_REPORT_2026-03-31.md
│           └── FINAL_STATUS_2026-03-31.md
│
├── src/n8n_analyzer/               # 🤖 ANA-001 N8N Performance Analyzer (novo)
│   ├── analyzers/                  # LatencyAnalyzer, CorrelationAnalyzer, Geographic, Loki
│   ├── collectors/                 # VictoriaMetrics, Loki, Base
│   ├── labels/                     # RootCauseLabel + classify()
│   ├── models/                     # Pydantic v2 models
│   ├── reporters/                  # MarkdownReporter, JsonReporter
│   ├── cli.py                      # analyze-n8n CLI entry-point
│   └── config.py                   # Config + secrets loader
│
├── scripts/                        # 🔧 Scripts Python
│   ├── analyze_n8n_performance.py  # analyze-n8n shim entry-point (novo)
│   ├── docker_analyzer.py          # Analisador principal
│   ├── generate_report.py          # Gerador de relatórios
│   └── docker_compose_ports_scanner.py
│
├── specs/001-n8n-performance-analyzer/ # 📐 Specs ANA-001 (novo)
│   ├── plan.md
│   └── tasks.md                    # 40/40 tasks ✅
│
├── .secrets/                       # 🔐 Credenciais (não versionado)
├── data/                           # 📊 Dados de entrada
├── reports/                        # 📈 Relatórios gerados
├── tests/                          # 🧪 Testes (unit + integration)
├── migration_plan.json             # 🗺️ Plano de migração
├── main.py                         # Script principal
├── pyproject.toml                  # Dependências Python (v0.2.0)
├── README.md                       # Documentação principal
└── uv.lock                         # Lock de dependências
```

---

## 📊 Infraestrutura de Servidores

### 🟢 Servidores Ativos

#### wf001.vya.digital — Docker Host USA
- **Containers**: 22 (ref. jan/2026)
- **CPU**: 12.52% | **RAM**: ~11 GB / 86.63 GB (13%)
- **Papel**: N8N principal + Collector-API + Observability Stack (Grafana, VictoriaMetrics, Loki)
- **Coletor**: ✅ **Ativo** — ponto de referência de latência USA
- **Status**: ✅ Operacional

#### wf008.vya.digital — Docker Host Brasil
- **Papel**: VPS Brasil + Collector-API
- **Coletor**: ✅ **Ativo** — ponto de referência de latência Brasil
- **Status**: ✅ Operacional
- **Observação**: Dados cruzados wf001 (USA) + wf008 (BR) → referência de latência geográfica N8N

#### wfdb01.vya.digital — Docker Host USA
- **Papel**: Docker host adicional USA — **hospeda stack de observabilidade** (Prometheus, VictoriaMetrics, Loki, Grafana)
- **Containers ativos**: enterprise-prometheus, enterprise-victoriametrics, enterprise-postgres, enterprise-grafana, loki-read/write/backend, cAdvisor, node-exporter, alertmanager
- **Acesso SSH**: SPA via fwknop (`source .secrets/wfdb01_connection.sh` para helpers)
- **Rede Docker interna**: `enterprise-observability_loki` (compartilhada entre todos os containers)
- **VictoriaMetrics**: `http://victoriametrics:8428` (interno) — 12 meses de dados; tunnel local: `wfdb01_tunnel_vm`
- **enterprise-postgres**: pertence ao stack observabilidade (Grafana + Loki) — **não modificar**
- **Status**: ✅ Operacional

#### wfdb02.vya.digital — Database Server
- **Papel**: Servidor de banco de dados — PostgreSQL 16.10 (N8N DB + serviços) + MySQL 8.4.6
- **Importante**: wfdb02 hospeda **dados de aplicação de produção** — não é destino para dados de análise
- **Status**: ✅ Operacional

### 🔴 Servidores Cancelados (VPS encerrado)

| Servidor | Cancelado em | Motivo | Impacto |
|---|---|---|---|
| wf002.vya.digital | Mar/2026 | Contrato VPS cancelado | N8N secundário desativado |
| wf005.vya.digital | Mar/2026 | Contrato VPS cancelado | Era candidato a shutdown |
| wf006.vya.digital | Mar/2026 | Contrato VPS cancelado | Alta utilização, encerrado |
| wfdb03.vya.digital | Mar/2026 | Contrato VPS cancelado | DB server desativado |

---

## 🔧 Scripts Disponíveis

### docker_analyzer.py
**Propósito**: Análise automatizada de recursos Docker
**Uso**: `python scripts/docker_analyzer.py`
**Output**: `migration_plan.json`

**Funcionalidades**:
- Processa JSONs de métricas Docker
- Calcula uso total por servidor
- Identifica servidor subutilizado
- Gera plano de migração balanceado

### generate_report.py
**Propósito**: Geração de relatórios markdown
**Uso**: `python scripts/generate_report.py`
**Output**: `reports/servidores_desligamento_report.md`

**Funcionalidades**:
- Compara servidores lado a lado
- Lista containers com detalhes
- Inclui volumes e bind mounts

### docker_compose_ports_scanner.py
**Propósito**: Detectar conflitos de portas
**Uso**: `python scripts/docker_compose_ports_scanner.py`
**Status**: Aguardando arquivos docker-compose.yml

**Funcionalidades**:
- Busca recursiva de compose files
- Extrai mapeamentos de portas
- Detecta conflitos
- Export para CSV

---

## � Componentes Migrados para enterprise-observability

> ℹ️ Os seguintes subprojetos foram movidos para [`../enterprise-observability/`](../enterprise-observability/)

| Componente | Conteúdo | Migrado em |
|---|---|---|
| `n8n-prometheus-wfdb01/` | collector-api (módulo N8N), ping-service, deploy scripts | fev/2026 |
| `n8n-tuning/` | Scripts análise N8N, dados de performance, relatórios | mar/2026 |
| `wfdb01-docker-folder/` | Volume SSHFS remoto (estava vazio) | 17/03/2026 |

**Acesso ao código dos coletores**: `../enterprise-observability/`

---

## 📋 Documentos Importantes

### Sessão 31/03/2026

- Sessao iniciada com artefatos em `docs/sessions/2026-03-31/`
- Arquivos: `SESSION_RECOVERY_2026-03-31.md`, `TODAY_ACTIVITIES_2026-03-31.md`, `SESSION_REPORT_2026-03-31.md`, `FINAL_STATUS_2026-03-31.md`, `CHAT_LOG_2026-03-31.md`
- Estado inicial: contexto recuperado de 30/03, worktree preservado e alerta historico de seguranca registrado

### Sessão 23/03/2026

- Encerramento concluido com artefatos em `docs/sessions/2026-03-23/`
- Arquivos: `SESSION_RECOVERY_2026-03-23.md`, `TODAY_ACTIVITIES_2026-03-23.md`, `SESSION_REPORT_2026-03-23.md`, `FINAL_STATUS_2026-03-23.md`

### Sessão 16/01/2026

#### [SESSION_RECOVERY_2026-01-16.md](docs/sessions/SESSION_RECOVERY_2026-01-16.md)
Contexto completo para recuperar trabalho:
- Infraestrutura analisada
- Ferramentas desenvolvidas
- Análise de resultados
- Plano de migração
- Incidente Metabase (resolvido externamente)

#### [SESSION_REPORT_2026-01-16.md](docs/sessions/SESSION_REPORT_2026-01-16.md)
Relatório executivo detalhado:
- Resumo executivo
- Objetivos vs resultados
- Métricas de utilização
- Timeline de atividades
- Lições aprendidas

#### [FINAL_STATUS_2026-01-16.md](docs/sessions/FINAL_STATUS_2026-01-16.md)
Status final e próximos passos:
- Entregas realizadas
- Resultados quantitativos
- Plano de ação futuro (4 fases)
- Riscos identificados
- Checklist de execução

---

## ✅ Progresso Atual

### Fase 1: Análise de Infraestrutura ✅ 100%
- [x] Análise de recursos de 4 servidores
- [x] Identificação de servidor alvo (wf005)
- [x] Geração de plano de migração
- [x] Desenvolvimento de ferramentas análise
- [x] Documentação completa

### Fase 2: Observability Stack ✅ 100%
- [x] Integração Prometheus Pushgateway
- [x] Collector API enviando métricas (109 séries)
- [x] Stack completa validada (Grafana, Prometheus, Loki)
- [x] Zero falhas de push desde deploy

### Fase 3: N8N Monitoring ✅ 85% implementação | ⏳ Deploy
- [x] **Implementação Módulo N8N** (09/02/2026)
  - [x] n8n_metrics.py, n8n_client.py, n8n_collector.py
  - [x] Build e push Docker
- [x] **ANA-001 N8N Performance Analyzer** ✅ 40/40 tasks (17/03/2026)
  - [x] CLI `analyze-n8n` com VictoriaMetrics + Loki
  - [x] LatencyAnalyzer + CorrelationAnalyzer + GeographicAnalyzer
  - [x] MarkdownReporter + JsonReporter
  - [x] --dry-run validado, SC-001 benchmark < 5 min
  - [x] Bugs corrigidos (le PromQL, math.isnan, repr(exc)) — 18/03/2026
- [x] **Agentes Copilot especializados** ✅ 5 agentes criados (18/03/2026)
  - [x] dba, prometheus, observability, victoriametrics, python-dev
  - [x] Prompts correspondentes em `.github/prompts/`
- [x] **Debate arquitetura coleta wfdb01** ✅ Consenso v2 (18/03/2026)
  - [x] `reports/DEBATE_COLETA_WFDB01_2026-03-18.md` — 11 seções, consenso final
  - [x] Solução aprovada: venv SSH direto no wfdb01 → `victoriametrics:8428` → scp reports
  - [x] `reports/PROMETHEUS_RECORDING_RULES_N8N_2026-03-18.md` — para enterprise-observability-dashboards
- [ ] ⏳ Executar `analyze-n8n` no wfdb01 (Run 1 histórico + Run 2 drill-down) — **PRÓXIMO**
- [ ] ⏳ Deploy Collector-API em **wf001** (N8N principal) — pendente
- [ ] ⏳ Deploy Collector-API em **wf008** (VPS Brasil) — pendente
- [ ] ⏳ Cruzar dados wf001 + wf008 para análise de latência geográfica
- [ ] ⏳ Dashboards N8N populando dados

> ⚠️ **wf002 cancelado** — deploy em wf002 não é mais necessário.

### Fase 4: Migração wf005 ✅ RESOLVIDA (Mar/2026)
- [x] wf005 teve contrato VPS cancelado — migração não precisou de execução manual
- [x] wf002 e wfdb03 também cancelados — consolidação natural da infraestrutura

### Fase 5: Organização & Segurança ✅ 100% (17/03/2026)
- [x] Varredura completa de credenciais hardcoded (2 rodadas)
- [x] Verificação .secrets/ no .gitignore ✅
- [x] **Migração `.docs/` → `docs/`** ✅
- [x] Todas referências `.docs/` → `docs/` atualizadas
- [x] `.gitignore` atualizado com padrões IDE/OS
- [x] Atualização README, INDEX, TODO
- [x] Documentação sessão 2026-03-17 criada e finalizada

---

## 🎯 Próximas Ações

### Prioridade ALTA (Esta Semana)
1. ⏳ Deploy Collector-API em wf001 (N8N principal)
2. ⏳ Deploy Collector-API em wf008 (VPS Brasil)
3. ⏳ Validar coleta das 9 métricas N8N em wf001
4. ⏳ Cruzar dados wf001 + wf008 para latência geográfica
5. ⏳ Verificar dashboards N8N populando no Grafana

### Prioridade MÉDIA (Próxima Semana)
1. ⏳ Executar `analyze-n8n` em produção com dados reais
2. ⏳ Configurar alertas Prometheus
3. ⏳ Dashboard de latência geográfica Brasil × USA

### Resolvidas Automaticamente (Mar/2026)
- ✅ ~~Migração wf005~~ — servidor cancelado
- ✅ ~~Deploy em wf002~~ — servidor cancelado
- ✅ ~~Monitorar wf006~~ — servidor cancelado
- ✅ ~~Aprovação de migração~~ — encerramento de contrato

---

## 📚 Referências Rápidas

### Comandos Úteis

```bash
# Análise de recursos
python scripts/docker_analyzer.py

# Gerar relatório
python scripts/generate_report.py

# Ver containers
docker ps --format "table {{.Names}}\t{{.Status}}"

# Monitorar recursos em tempo real
docker stats

# Backup de volume
docker run --rm -v VOLUME:/data -v $(pwd):/backup \
  alpine tar czf /backup/VOLUME.tar.gz -C /data .
```

### Arquivos Chave

- **Plano de Migração**: `migration_plan.json`
- **Relatório Comparativo**: `reports/servidores_desligamento_report.md`
- **Credenciais DB**: `.secrets/postgresql_destination_config.json`

---

## 💰 Impacto Financeiro

| Métrica | Valor |
|---------|-------|
| Economia Mensal | R$ 650-1,050 |
| Economia Anual | R$ 7,800-12,600 |
| Servidores Antes | 4 |
| Servidores Depois | 3 |
| Redução | 25% |
| ROI | < 1 mês |

---

## 🚨 Riscos Principais

1. **Perda de Dados** - Mitigação: Backup completo antes de iniciar
2. **Downtime** - Mitigação: Janela de manutenção em horário de baixo uso
3. **Conflitos de Porta** - Mitigação: Executar port scanner primeiro
4. **Sobrecarga** - Mitigação: Monitoramento ativo por 72h

---

## 📞 Contatos e Recursos

### Servidores
- wf001.vya.digital - Target (Alta Capacidade)
- wf002.vya.digital - Target (Alta Capacidade)
- wf005.vya.digital - Source (Para Desligamento)
- wf006.vya.digital - Produção (Não Mexer)

### Database
- Host: wfdb02.vya.digital:5432
- Database: metabase_db
- Config: `.secrets/postgresql_destination_config.json`

### Ambiente
- Python: 3.12
- Package Manager: uv
- Virtual Env: `.venv/`

---

## 📝 Notas de Versão

### v1.0 - 16/01/2026
- ✅ Análise inicial completa
- ✅ Plano de migração gerado
- ✅ Ferramentas desenvolvidas
- ✅ Documentação completa
- ✅ Projeto organizado

---

**Última Atualização**: 19/03/2026
**Status**: ✅ Encerramento formal da sessão 2026-03-19 concluído
**Próximo Milestone**: validação de cobertura contínua pós-ajustes do collector (projeto externo)

---

## 📌 Encerramento da Sessão 2026-03-19

- Inventário de dados ANA001 concluído: `reports/ana001_data_inventory_20260319T150604Z.md`
- Execução remota no wfdb01 confirmada: `reports-wfdb01/n8n_perf_ANA001_20260101_20260319_20260319T122748.md`
- Conclusão ANA001 consolidada: `reports/ANA001_CONCLUSAO.md`
- Recomendações para time do collector: `reports/COLLECTOR_CODE_RECOMMENDATIONS_2026-03-19.md`
- Documentação da sessão:
  - `docs/sessions/2026-03-19/TODAY_ACTIVITIES_2026-03-19.md`
  - `docs/sessions/2026-03-19/SESSION_REPORT_2026-03-19.md`
  - `docs/sessions/2026-03-19/FINAL_STATUS_2026-03-19.md`
