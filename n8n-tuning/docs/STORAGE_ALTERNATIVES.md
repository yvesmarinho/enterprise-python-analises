# 📊 Alternativas para Armazenamento de Métricas do N8N

**Última Atualização**: 03/02/2026  
**Objetivo**: Armazenar dados de performance do N8N para análise temporal

---

## 🎯 Alternativas Disponíveis

### 1. 🐘 PostgreSQL (RECOMENDADO) ⭐⭐⭐

**Vantagens:**
- ✅ Você já tem acesso ao servidor (wfdb02.vya.digital)
- ✅ Usuário read-only existente (n8n_tuning_read)
- ✅ Pode criar schema separado para métricas
- ✅ Excelente para análises com SQL
- ✅ Suporta TimescaleDB (extensão time-series)
- ✅ Fácil integração com ferramentas de BI

**Estrutura Proposta:**
```sql
-- Schema para métricas
CREATE SCHEMA IF NOT EXISTS n8n_metrics;

-- Tabela de snapshots de workflows
CREATE TABLE n8n_metrics.workflow_snapshots (
    id SERIAL PRIMARY KEY,
    collected_at TIMESTAMP DEFAULT NOW(),
    workflow_id VARCHAR(50),
    workflow_name VARCHAR(255),
    active BOOLEAN,
    nodes_count INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    raw_data JSONB
);

-- Tabela de execuções
CREATE TABLE n8n_metrics.execution_metrics (
    id SERIAL PRIMARY KEY,
    collected_at TIMESTAMP DEFAULT NOW(),
    execution_id VARCHAR(50) UNIQUE,
    workflow_id VARCHAR(50),
    workflow_name VARCHAR(255),
    started_at TIMESTAMP,
    stopped_at TIMESTAMP,
    duration_ms INTEGER,
    finished BOOLEAN,
    success BOOLEAN,
    mode VARCHAR(50),
    raw_data JSONB
);

-- Índices para queries rápidas
CREATE INDEX idx_execution_workflow ON n8n_metrics.execution_metrics(workflow_id);
CREATE INDEX idx_execution_started ON n8n_metrics.execution_metrics(started_at);
CREATE INDEX idx_workflow_collected ON n8n_metrics.workflow_snapshots(collected_at);
```

**Uso:**
- Coletar dados via API a cada X minutos/horas
- Inserir no PostgreSQL
- Queries SQL para análise
- Grafana conectado ao PostgreSQL para visualização

---

### 2. 📦 SQLite Local ⭐⭐⭐

**Vantagens:**
- ✅ Não precisa de servidor
- ✅ Arquivo único e portável
- ✅ Suporte completo a SQL
- ✅ Fácil backup e compartilhamento
- ✅ Bibliotecas Python nativas

**Estrutura:**
```
n8n-tuning/
└── data/
    └── metrics_db/
        └── n8n_metrics.db  (SQLite)
```

**Uso:**
```python
import sqlite3
from datetime import datetime

# Conectar ao banco
conn = sqlite3.connect('data/metrics_db/n8n_metrics.db')

# Inserir métricas
cursor.execute("""
    INSERT INTO execution_metrics 
    (execution_id, workflow_id, duration_ms, success, collected_at)
    VALUES (?, ?, ?, ?, ?)
""", (exec_id, wf_id, duration, success, datetime.now()))
```

---

### 3. 📈 InfluxDB (Time-Series DB) ⭐⭐

**Vantagens:**
- ✅ Especializado em time-series
- ✅ Queries otimizadas para métricas
- ✅ Retenção automática de dados
- ✅ Integração com Grafana

**Desvantagens:**
- ❌ Requer instalação de servidor
- ❌ Mais complexo que SQLite/PostgreSQL

**Quando usar:**
- Se você pretende coletar métricas em alta frequência (< 1 min)
- Se precisa de dashboards em tempo real
- Se vai coletar milhões de data points

---

### 4. 📊 Parquet Files (Análise de Dados) ⭐⭐

**Vantagens:**
- ✅ Formato colunar eficiente
- ✅ Compressão excelente
- ✅ Integração com pandas/polars
- ✅ Compatível com Spark, DuckDB

**Uso:**
```python
import pandas as pd

# Salvar métricas
df = pd.DataFrame(metrics)
df.to_parquet('data/metrics_db/executions_2026-02.parquet')

# Ler e analisar
df = pd.read_parquet('data/metrics_db/executions_2026-02.parquet')
df.groupby('workflow_id')['duration_ms'].mean()
```

---

### 5. 🔥 Hybrid: JSON + DuckDB ⭐⭐⭐

**Vantagens:**
- ✅ Melhor dos dois mundos
- ✅ JSON para coleta (já estamos fazendo)
- ✅ DuckDB para análise SQL rápida
- ✅ Não precisa importar dados

**Uso:**
```python
import duckdb

# Query diretamente nos JSONs
conn = duckdb.connect()
result = conn.execute("""
    SELECT 
        workflowId,
        COUNT(*) as executions,
        AVG(duration) as avg_duration
    FROM read_json_auto('data/metrics/executions_*.json')
    GROUP BY workflowId
    ORDER BY avg_duration DESC
""").fetchdf()
```

---

## 🚀 Usando Partes da Stack Prometheus

### Opção A: Formato Prometheus (sem servidor)

**Usar bibliotecas Python:**
```python
from prometheus_client import CollectorRegistry, Gauge, write_to_textfile

registry = CollectorRegistry()

# Definir métricas
workflow_duration = Gauge(
    'n8n_workflow_duration_seconds',
    'Duração do workflow',
    ['workflow_id', 'workflow_name'],
    registry=registry
)

# Registrar métricas
workflow_duration.labels(
    workflow_id='abc123',
    workflow_name='my-workflow'
).set(45.5)

# Salvar em arquivo
write_to_textfile('data/metrics/n8n_metrics.prom', registry)
```

**Vantagens:**
- Formato padrão da indústria
- Pode ser importado depois no Prometheus
- Node Exporter pode ler os arquivos

---

### Opção B: Prometheus + Node Exporter (Textfile Collector)

**Se você tiver Node Exporter rodando:**
```bash
# Gerar métricas em formato Prometheus
python scripts/generate_prometheus_metrics.py > /var/lib/node_exporter/n8n.prom

# Node Exporter expõe automaticamente
curl http://localhost:9100/metrics | grep n8n_
```

---

## 📋 Recomendação Final

### Para o seu caso (N8N Tuning):

**🥇 Opção 1: PostgreSQL + DuckDB**
```
Coleta → API N8N → Save JSON → PostgreSQL (histórico)
                              ↘ DuckDB (análise rápida)
```

**Por quê:**
1. PostgreSQL - Você já tem acesso, pode criar schema `n8n_metrics`
2. DuckDB - Query rápida nos JSONs sem importar
3. Grafana - Pode conectar no PostgreSQL para dashboards

**🥈 Opção 2: SQLite + JSON**
```
Coleta → API N8N → Save JSON (raw)
                  → SQLite (estruturado)
```

**Por quê:**
1. Simples e portátil
2. Não precisa de servidor adicional
3. Fácil análise com Python/pandas

---

## 🛠️ Implementação Sugerida

**Fase 1: Coleta Básica (Agora)**
- ✅ Salvar JSONs timestamped (já está fazendo)
- ✅ DuckDB para queries ad-hoc

**Fase 2: Armazenamento Estruturado (Semana 1)**
- PostgreSQL schema `n8n_metrics`
- Script de ingestão automática
- Retenção de 90 dias

**Fase 3: Visualização (Semana 2)**
- Grafana + PostgreSQL
- Dashboards de performance
- Alertas de anomalias

---

## 💡 Quer que eu implemente qual opção?

1. **PostgreSQL schema + ingestor** (recomendado para produção)
2. **SQLite local** (recomendado para testes rápidos)
3. **DuckDB queries** (recomendado para análise imediata)
4. **Hybrid (JSON + PostgreSQL + DuckDB)** (melhor dos mundos)

Escolha uma e eu implemento agora! 🚀
