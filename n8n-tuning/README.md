# 🔧 N8N Performance Tuning

**Análise e Otimização de Performance do N8N**

---

## 🎯 Objetivo

Analisar o sistema N8N em produção para identificar gargalos de performance e oportunidades de otimização, visando melhorar tempo de resposta, throughput e confiabilidade.

---

## 📂 Estrutura do Projeto

```
n8n-tuning/
├── docs/                    # 📚 Documentação
│   ├── INDEX.md            # Índice e visão geral
│   ├── TODO.md             # Lista de tarefas
│   └── ANALYSIS_GUIDE.md   # Guia de coleta e análise
│
├── data/                    # 📊 Dados coletados
│   ├── metrics/            # Métricas de performance
│   ├── workflows/          # Workflows exportados
│   └── database/           # Análise de banco de dados
│
├── scripts/                 # 🔧 Scripts de análise
│   ├── n8n_metrics_collector.py
│   └── workflow_analyzer.py
│
├── reports/                 # 📈 Relatórios gerados
│
└── README.md               # Este arquivo
```

---

## 🚀 Quick Start

### 1. Configurar Ambiente

```bash
# Definir variáveis de ambiente
export N8N_URL="https://n8n.sua-empresa.com"
export N8N_API_KEY="sua-api-key-aqui"

# Validar conexão
curl -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_URL/api/v1/workflows" | jq '.data | length'
```

### 2. Coletar Métricas

```bash
cd n8n-tuning

# Coletar workflows e execuções
python scripts/n8n_metrics_collector.py

# Analisar workflows
python scripts/workflow_analyzer.py
```

### 3. Consultar Documentação

- [📑 INDEX](docs/INDEX.md) - Visão geral completa
- [✅ TODO](docs/TODO.md) - Lista de tarefas e timeline
- [📊 ANALYSIS_GUIDE](docs/ANALYSIS_GUIDE.md) - Guia detalhado de coleta

---

## 📋 Fases do Projeto

| Fase | Duração | Status |
|------|---------|--------|
| 1. Coleta de Baseline | Semana 1 | ⏳ Pendente |
| 2. Análise & Diagnóstico | Semana 2 | ⏳ Pendente |
| 3. Recomendações | Semana 2-3 | ⏳ Pendente |
| 4. Implementação | Semana 3-4 | ⏳ Pendente |
| 5. Validação | Semana 4 | ⏳ Pendente |

---

## 🎯 Áreas de Análise

### 1. Performance de Workflows
- Tempo de execução
- Taxa de sucesso/falha
- Workflows lentos
- Nodes mais utilizados

### 2. Utilização de Recursos
- CPU e Memória
- Disco I/O
- Rede e latência

### 3. Banco de Dados
- Queries lentas
- Índices faltantes
- Tamanho de tabelas

### 4. Configuração
- Variáveis de ambiente
- Docker resources
- Queue settings

---

## 📊 Métricas-Chave (KPIs)

| Métrica | Target | Baseline | Atual |
|---------|--------|----------|-------|
| Tempo médio execução | < 5s | TBD | TBD |
| Taxa de sucesso | > 98% | TBD | TBD |
| CPU Usage | < 50% | 2.06% | TBD |
| Memory Usage | < 80% | 485 MB | TBD |

---

## 🛠️ Scripts Disponíveis

### n8n_metrics_collector.py
Coleta métricas via API do N8N
- Workflows
- Execuções
- Performance

**Uso**:
```bash
export N8N_URL="https://n8n.example.com"
export N8N_API_KEY="your-key"
python scripts/n8n_metrics_collector.py
```

### workflow_analyzer.py
Analisa workflows exportados
- Complexidade
- Nodes utilizados
- Oportunidades de otimização

**Uso**:
```bash
python scripts/workflow_analyzer.py [data_dir]
```

---

## 📝 Contexto do Projeto

Este N8N está atualmente no servidor **wf005.vya.digital** que será desligado após migração para **wf001**. Esta análise é crucial para:

1. ✅ Dimensionar recursos adequados no novo servidor
2. ✅ Otimizar antes da migração
3. ✅ Garantir transição sem perda de performance
4. ✅ Estabelecer baseline para monitoramento futuro

**Recursos Atuais**: 2.06% CPU, 485 MB RAM  
**Target**: wf001.vya.digital

---

## 🔗 Links Úteis

### Documentação N8N
- [N8N Docs](https://docs.n8n.io/)
- [N8N API](https://docs.n8n.io/api/)
- [Performance Best Practices](https://docs.n8n.io/hosting/configuration/)

### Projeto Principal
- [Projeto Enterprise Analysis](../.docs/INDEX.md)
- [Migration Plan](../migration_plan.json)

---

## 📅 Timeline

**Início**: 02/02/2026  
**Duração**: 4 semanas  
**Status**: 🚀 Setup Inicial

```
Semana 1: Setup e Coleta de Baseline
Semana 2: Análise e Diagnóstico
Semana 3: Implementação de Otimizações
Semana 4: Validação e Documentação
```

---

## 👥 Equipe

**Responsável**: DevOps Team  
**Data de Criação**: 02/02/2026  
**Última Atualização**: 02/02/2026

---

## ⚠️ Notas Importantes

### Segurança
- ❌ NÃO commitar credenciais
- ❌ NÃO versionar dados sensíveis
- ✅ Usar variáveis de ambiente
- ✅ Backup antes de mudanças

### Performance
- Coletar dados fora de horário de pico
- Queries read-only apenas
- Monitorar impacto das mudanças

---

**Para começar, veja**: [docs/TODO.md](docs/TODO.md)
