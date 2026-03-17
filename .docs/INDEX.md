# 📑 INDEX - Enterprise Python Analysis

**Projeto**: Análise e Otimização de Infraestrutura Docker + N8N Monitoring
**Última Atualização**: 17/03/2026
**Status**: ✅ Módulo N8N Implementado (85%) | ⏳ Deploy Pendente (15%) | 🔄 Sessão 2026-03-17 em progresso

---

## 🎯 Objetivo do Projeto

Analisar recursos de 4 servidores Docker em produção para identificar oportunidades de consolidação e redução de custos através do desligamento de servidor subutilizado.

**Resultado**: wf005.vya.digital identificado para shutdown - Economia projetada de R$ 7,800-12,600/ano

---

## 📂 Estrutura do Projeto

```
enterprise-python-analysis/
├── .docs/                          # 📚 Documentação
│   ├── INDEX.md                    # Este arquivo
│   ├── TODO.md                     # Lista de tarefas
│   ├── TODAY_ACTIVITIES.md         # Log diário de atividades
│   └── sessions/                   # Documentação de sessões
│       ├── 2026-01-16/
│       │   ├── SESSION_RECOVERY_2026-01-16.md
│       │   ├── SESSION_REPORT_2026-01-16.md
│       │   └── FINAL_STATUS_2026-01-16.md
│       ├── 2026-02-02/
│       │   ├── SESSION_RECOVERY_2026-02-02.md
│       │   ├── TODAY_ACTIVITIES_2026-02-02.md
│       │   └── SESSION_SUMMARY_2026-02-02.md
│       ├── 2026-02-03/
│       │   ├── SESSION_RECOVERY_2026-02-03.md
│       │   ├── TODAY_ACTIVITIES_2026-02-03.md
│       │   ├── SESSION_REPORT_2026-02-03.md
│       │   └── FINAL_STATUS_2026-02-03.md
│       ├── 2026-02-04/
│       │   ├── SESSION_RECOVERY_2026-02-04.md
│       │   └── TODAY_ACTIVITIES_2026-02-04.md
│       ├── 2026-02-05/
│       │   ├── SESSION_RECOVERY_2026-02-05.md
│       │   ├── SESSION_REPORT_2026-02-05.md
│       │   ├── FINAL_STATUS_2026-02-05.md
│       │   └── TODAY_ACTIVITIES_2026-02-05.md
│       ├── 2026-02-06/
│       │   ├── SESSION_RECOVERY_2026-02-06.md
│       │   └── TODAY_ACTIVITIES_2026-02-06.md
│       ├── 2026-02-09/
│       │   ├── SESSION_RECOVERY_2026-02-09.md
│       │   ├── SESSION_REPORT_2026-02-09.md
│       │   ├── FINAL_STATUS_2026-02-09.md
│       │   └── TODAY_ACTIVITIES_2026-02-09.md
│       ├── 2026-03-03/
│       │   ├── SESSION_RECOVERY_2026-03-03.md
│       │   ├── SESSION_REPORT_2026-03-03.md
│       │   └── TODAY_ACTIVITIES_2026-03-03.md
│       └── 2026-03-17/              # ⭐ Sessão atual
│           ├── SESSION_RECOVERY_2026-03-17.md
│           ├── TODAY_ACTIVITIES_2026-03-17.md
│           ├── SESSION_REPORT_2026-03-17.md
│           └── FINAL_STATUS_2026-03-17.md
│
├── .secrets/                       # 🔐 Credenciais (não versionado)
│   └── postgresql_destination_config.json
│
├── data/                           # 📊 Dados de entrada
│   └── docker_collector/
│       ├── wf001.vya.digital_docker_stats_20260116_100205.json
│       ├── wf002.vya.digital_docker_stats_20260116_102230.json
│       ├── wf005.vya.digital_docker_stats_20260116_105355.json
│       └── wf006.vya.digital_docker_stats_20260116_105728.json
│
├── scripts/                        # 🔧 Scripts Python
│   ├── docker_analyzer.py          # Analisador principal
│   ├── generate_report.py          # Gerador de relatórios
│   └── docker_compose_ports_scanner.py
│
├── reports/                        # 📈 Relatórios gerados
│   └── servidores_desligamento_report.md
│
├── migration_plan.json             # 🗺️ Plano de migração
├── main.py                         # Script principal
├── pyproject.toml                  # Dependências Python
├── README.md                       # Documentação inicial
└── uv.lock                         # Lock de dependências
```

---

## 📊 Servidores Analisados

### wf001.vya.digital
- **Containers**: 22
- **CPU**: 12.52%
- **RAM**: ~11 GB / 86.63 GB (13%)
- **Status**: ✅ Target para migração (alta capacidade)

### wf002.vya.digital
- **Containers**: 7
- **CPU**: 11.85%
- **RAM**: ~10 GB / 86.63 GB (12%)
- **Status**: ✅ Target para migração (alta capacidade)

### wf005.vya.digital ⭐
- **Containers**: 13
- **CPU**: 6.32%
- **RAM**: 4.81 GB
- **Status**: 🎯 **CANDIDATO A DESLIGAMENTO**

### wf006.vya.digital
- **Containers**: 8
- **CPU**: 54.66%
- **RAM**: 12.78 GB
- **Status**: ⚠️ Alta utilização (não tocar)

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

### Sessão 16/01/2026

#### [SESSION_RECOVERY_2026-01-16.md](.docs/sessions/SESSION_RECOVERY_2026-01-16.md)
Contexto completo para recuperar trabalho:
- Infraestrutura analisada
- Ferramentas desenvolvidas
- Análise de resultados
- Plano de migração
- Incidente Metabase (resolvido externamente)

#### [SESSION_REPORT_2026-01-16.md](.docs/sessions/SESSION_REPORT_2026-01-16.md)
Relatório executivo detalhado:
- Resumo executivo
- Objetivos vs resultados
- Métricas de utilização
- Timeline de atividades
- Lições aprendidas

#### [FINAL_STATUS_2026-01-16.md](.docs/sessions/FINAL_STATUS_2026-01-16.md)
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

### Fase 3: N8N Monitoring ✅ 85% | ⏳ 15%
- [x] **Implementação Módulo N8N** (09/02/2026)
  - [x] n8n_metrics.py - 9 métricas Prometheus (58 linhas)
  - [x] n8n_client.py - Cliente HTTP completo (266 linhas)
  - [x] n8n_collector.py - Coletor com cache (289 linhas)
  - [x] Integração asyncio tasks no main.py
  - [x] Build e push Docker (digest: 374607f1)
- [ ] ⏳ Deploy no wf001.vya.digital (pendente)
- [ ] ⏳ Validação de métricas
- [ ] ⏳ Dashboards N8N populando dados

### Fase 5: Organização & Segurança ✅ 100% (17/03/2026)
- [x] Varredura completa de credenciais hardcoded
- [x] Verificação .secrets/ no .gitignore ✅
- [x] Atualização README, INDEX, TODO
- [x] Documentação sessão 2026-03-17 criada
- [x] Branch GitHub criada

### Fase 4: Migração wf005 ⏳ 0%
- [ ] Aprovação do plano de migração
- [ ] Agendamento de janela de manutenção
- [ ] Execução da migração
- [ ] Validação pós-migração (72h)
- [ ] Desligamento de wf005

---

## 🎯 Próximas Ações

### Prioridade ALTA (Esta Semana)
1. ⏳ Obter aprovação para migração
2. ⏳ Agendar janela de manutenção
3. ⏳ Executar backup completo de wf005
4. ⏳ Validar conectividade wf005 ↔ wf001/wf002

### Prioridade MÉDIA (Próxima Semana)
1. ⏳ Executar migração de containers
2. ⏳ Monitorar por 72h
3. ⏳ Validar funcionalidades

### Prioridade BAIXA (Após Validação)
1. ⏳ Desligar wf005 definitivamente
2. ⏳ Documentar economia alcançada
3. ⏳ Relatório pós-migração

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

**Última Atualização**: 17/03/2026
**Status**: ⚠️ Deploy N8N Pendente | 🔄 Sessão 2026-03-17 em andamento
**Próximo Milestone**: Deploy Collector-API N8N + Migração wf005
