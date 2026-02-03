# 📊 Guia de Análise e Coleta de Dados - N8N Performance

**Versão**: 1.0  
**Data**: 02/02/2026  
**Objetivo**: Documentar procedimentos para coleta e análise de dados do N8N

---

## 📋 Checklist de Coleta de Dados

### ✅ Pré-requisitos

#### Acessos Necessários
- [ ] SSH para wf005.vya.digital
- [ ] Credenciais N8N Admin
- [ ] API Key do N8N
- [ ] Acesso read-only ao PostgreSQL
- [ ] Acesso ao Grafana/Prometheus
- [ ] Acesso aos logs (Loki ou diretamente)

#### Ferramentas Necessárias
- [ ] Python 3.12+ instalado
- [ ] Bibliotecas: requests, pandas, psycopg2
- [ ] jq (para parse de JSON no CLI)
- [ ] curl ou httpie
- [ ] PostgreSQL client (psql)

---

## 🔍 Coleta de Dados do Sistema

### 1. Informações do Container

```bash
# Acessar servidor
ssh user@wf005.vya.digital

# Informações básicas do container
docker inspect n8n_n8n | jq '.[0] | {
  Name: .Name,
  Image: .Config.Image,
  Created: .Created,
  Status: .State.Status,
  RestartCount: .RestartCount
}'

# Recursos do container
docker stats n8n_n8n --no-stream --format \
  "CPU: {{.CPUPerc}}\nMemory: {{.MemUsage}}\nNet I/O: {{.NetIO}}\nBlock I/O: {{.BlockIO}}"

# Variáveis de ambiente (CUIDADO: pode conter secrets)
docker exec n8n_n8n env | grep -E "N8N_|EXECUTIONS_|QUEUE_" | sort

# Versão do N8N
docker exec n8n_n8n n8n --version
```

### 2. Monitoramento Contínuo (7 dias)

```bash
# Script para coletar métricas a cada hora
#!/bin/bash
while true; do
  timestamp=$(date +%Y%m%d_%H%M%S)
  docker stats n8n_n8n --no-stream >> ./data/metrics/docker_stats_${timestamp}.txt
  sleep 3600  # 1 hora
done
```

### 3. Logs do Container

```bash
# Últimas 1000 linhas de logs
docker logs n8n_n8n --tail 1000 > ./data/logs/n8n_recent.log

# Logs com timestamp
docker logs n8n_n8n --timestamps --tail 5000 > ./data/logs/n8n_timestamped.log

# Seguir logs em tempo real
docker logs -f n8n_n8n

# Filtrar erros
docker logs n8n_n8n --tail 10000 | grep -i "error\|exception\|failed" \
  > ./data/logs/n8n_errors.log
```

---

## 🎯 Coleta de Dados do N8N

### 1. API do N8N

#### Configuração da API

```bash
# Definir variáveis
export N8N_URL="https://n8n.sua-empresa.com"
export N8N_API_KEY="sua-api-key-aqui"

# Testar conexão
curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
  $N8N_URL/api/v1/workflows | jq '.data | length'
```

#### Exportar Workflows

```bash
# Listar todos os workflows
curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_URL/api/v1/workflows" \
  > ./data/workflows/all_workflows.json

# Exportar workflow específico
WORKFLOW_ID="123"
curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_URL/api/v1/workflows/$WORKFLOW_ID" \
  > ./data/workflows/workflow_${WORKFLOW_ID}.json

# Exportar todos (script)
#!/bin/bash
workflow_ids=$(curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_URL/api/v1/workflows" | jq -r '.data[].id')

for id in $workflow_ids; do
  echo "Exportando workflow $id..."
  curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
    "$N8N_URL/api/v1/workflows/$id" \
    > "./data/workflows/workflow_${id}.json"
done
```

#### Coletar Estatísticas de Execução

```bash
# Execuções recentes
curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_URL/api/v1/executions?limit=100" \
  > ./data/metrics/recent_executions.json

# Execuções de um workflow específico
curl -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "$N8N_URL/api/v1/executions?workflowId=$WORKFLOW_ID&limit=100" \
  > ./data/metrics/workflow_${WORKFLOW_ID}_executions.json

# Análise rápida de sucesso/falha
cat ./data/metrics/recent_executions.json | \
  jq '[.data[] | {id: .id, workflow: .workflowData.name, finished: .finished, status: .status}] | group_by(.status) | map({status: .[0].status, count: length})'
```

### 2. Análise de Workflows (Python)

```python
# scripts/workflow_analyzer.py
import json
from collections import Counter
from pathlib import Path

def analyze_workflows(data_dir="./data/workflows"):
    workflows = []
    
    for file in Path(data_dir).glob("workflow_*.json"):
        with open(file) as f:
            workflow = json.load(f)
            workflows.append(workflow)
    
    # Estatísticas básicas
    print(f"Total de workflows: {len(workflows)}")
    
    # Nodes mais utilizados
    all_nodes = []
    for wf in workflows:
        if 'nodes' in wf:
            all_nodes.extend([n['type'] for n in wf['nodes']])
    
    node_counts = Counter(all_nodes)
    print("\nTop 10 nodes mais utilizados:")
    for node, count in node_counts.most_common(10):
        print(f"  {node}: {count}")
    
    # Workflows por status
    active = sum(1 for wf in workflows if wf.get('active', False))
    print(f"\nWorkflows ativos: {active}/{len(workflows)}")
    
    # Complexidade (número de nodes)
    complexities = [len(wf.get('nodes', [])) for wf in workflows]
    print(f"\nComplexidade média: {sum(complexities)/len(complexities):.1f} nodes")
    print(f"Workflow mais complexo: {max(complexities)} nodes")
    
    return workflows

if __name__ == "__main__":
    analyze_workflows()
```

---

## 🗄️ Coleta de Dados do Banco de Dados

### 1. Configuração de Acesso

```bash
# Variáveis de conexão
export PGHOST="localhost"
export PGPORT="5432"
export PGDATABASE="n8n"
export PGUSER="n8n_readonly"
export PGPASSWORD="sua-senha"

# Testar conexão
psql -c "SELECT version();"
```

### 2. Habilitar Monitoramento de Queries

```sql
-- Habilitar pg_stat_statements (requer superuser)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Verificar se está habilitado
SELECT * FROM pg_stat_statements LIMIT 1;
```

### 3. Análise de Tabelas

```sql
-- Tamanho de todas as tabelas
SELECT
    schemaname as schema,
    tablename as table,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY size_bytes DESC;

-- Salvar resultado
\o ./data/database/table_sizes.txt
-- executar query acima
\o
```

### 4. Queries Lentas

```sql
-- Top 20 queries mais lentas
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time,
    stddev_exec_time
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Salvar em CSV
\copy (SELECT query, calls, total_exec_time, mean_exec_time, max_exec_time FROM pg_stat_statements WHERE query NOT LIKE '%pg_stat_statements%' ORDER BY mean_exec_time DESC LIMIT 50) TO './data/database/slow_queries.csv' WITH CSV HEADER;
```

### 5. Análise de Execuções

```sql
-- Estatísticas da tabela execution_entity
SELECT
    COUNT(*) as total_executions,
    COUNT(*) FILTER (WHERE finished = true) as finished,
    COUNT(*) FILTER (WHERE finished = false) as running,
    COUNT(*) FILTER (WHERE "stoppedAt" IS NOT NULL) as stopped,
    MIN("startedAt") as oldest_execution,
    MAX("startedAt") as newest_execution
FROM execution_entity;

-- Execuções por workflow
SELECT
    w.name as workflow_name,
    COUNT(e.id) as execution_count,
    AVG(EXTRACT(EPOCH FROM (e."stoppedAt" - e."startedAt"))) as avg_duration_seconds,
    MAX(EXTRACT(EPOCH FROM (e."stoppedAt" - e."startedAt"))) as max_duration_seconds
FROM execution_entity e
JOIN workflow_entity w ON e."workflowId" = w.id
WHERE e."stoppedAt" IS NOT NULL
GROUP BY w.id, w.name
ORDER BY execution_count DESC
LIMIT 20;
```

### 6. Análise de Índices

```sql
-- Índices não utilizados
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Índices sugeridos (queries que fazem seq scan)
SELECT
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    seq_tup_read / seq_scan as avg_seq_tup
FROM pg_stat_user_tables
WHERE seq_scan > 0
AND schemaname = 'public'
ORDER BY seq_tup_read DESC
LIMIT 10;
```

---

## 📈 Coleta de Métricas via Prometheus

### 1. Métricas do N8N

```bash
# Assumindo que N8N expõe métricas em /metrics
curl http://localhost:5678/metrics > ./data/metrics/n8n_metrics_$(date +%Y%m%d_%H%M%S).txt

# Via Prometheus (se configurado)
# Exemplo de query para tempo de execução
curl -G http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=n8n_workflow_execution_duration_seconds' \
  | jq '.' > ./data/metrics/execution_duration.json
```

### 2. Queries Úteis do Prometheus

```promql
# CPU do container
rate(container_cpu_usage_seconds_total{name="n8n_n8n"}[5m])

# Memória do container
container_memory_usage_bytes{name="n8n_n8n"}

# Execuções por minuto
rate(n8n_workflow_executions_total[5m]) * 60

# Taxa de erro
rate(n8n_workflow_executions_failed_total[5m]) / 
rate(n8n_workflow_executions_total[5m])
```

---

## 📊 Processamento e Análise

### 1. Script de Consolidação

```python
# scripts/consolidate_data.py
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def consolidate_workflow_data():
    """Consolida dados de workflows em um único CSV"""
    workflows = []
    
    for file in Path("./data/workflows").glob("workflow_*.json"):
        with open(file) as f:
            wf = json.load(f)
            workflows.append({
                'id': wf.get('id'),
                'name': wf.get('name'),
                'active': wf.get('active', False),
                'nodes_count': len(wf.get('nodes', [])),
                'connections_count': len(wf.get('connections', {})),
                'created_at': wf.get('createdAt'),
                'updated_at': wf.get('updatedAt')
            })
    
    df = pd.DataFrame(workflows)
    df.to_csv('./data/consolidated_workflows.csv', index=False)
    print(f"Consolidado {len(workflows)} workflows")
    return df

def consolidate_execution_data():
    """Consolida dados de execuções"""
    executions = []
    
    for file in Path("./data/metrics").glob("*_executions.json"):
        with open(file) as f:
            data = json.load(f)
            for ex in data.get('data', []):
                executions.append({
                    'id': ex.get('id'),
                    'workflow_id': ex.get('workflowId'),
                    'workflow_name': ex.get('workflowData', {}).get('name'),
                    'started_at': ex.get('startedAt'),
                    'stopped_at': ex.get('stoppedAt'),
                    'finished': ex.get('finished'),
                    'status': ex.get('status'),
                    'mode': ex.get('mode')
                })
    
    df = pd.DataFrame(executions)
    # Calcular duração
    df['started_at'] = pd.to_datetime(df['started_at'])
    df['stopped_at'] = pd.to_datetime(df['stopped_at'])
    df['duration_seconds'] = (df['stopped_at'] - df['started_at']).dt.total_seconds()
    
    df.to_csv('./data/consolidated_executions.csv', index=False)
    print(f"Consolidado {len(executions)} execuções")
    return df

if __name__ == "__main__":
    print("Consolidando dados...")
    wf_df = consolidate_workflow_data()
    ex_df = consolidate_execution_data()
    
    print("\n=== Resumo ===")
    print(f"Workflows: {len(wf_df)}")
    print(f"Execuções: {len(ex_df)}")
    print(f"Taxa de sucesso: {(ex_df['finished']==True).sum() / len(ex_df) * 100:.1f}%")
```

---

## 📅 Cronograma de Coleta

### Dia 1: Setup
- Validar todos os acessos
- Executar coletas manuais
- Verificar qualidade dos dados

### Dias 2-8: Coleta Contínua
- Métricas de sistema a cada hora
- Logs diários
- Snapshots de workflows e execuções

### Dia 9: Consolidação
- Executar scripts de consolidação
- Validar completude dos dados
- Gerar relatório de baseline

---

## ⚠️ Cuidados e Considerações

### Segurança
- ❌ NÃO versionar credenciais
- ❌ NÃO commitar dados sensíveis
- ✅ Usar variáveis de ambiente
- ✅ Adicionar `data/` ao `.gitignore`

### Performance
- Coletar dados fora de horário de pico quando possível
- Queries read-only apenas
- Limitar tamanho de logs coletados

### Backup
- Fazer backup antes de qualquer análise destrutiva
- Manter dados brutos originais

---

**Próximo Passo**: Executar checklist de pré-requisitos e iniciar coleta de baseline  
**Duração Estimada**: 7-10 dias  
**Responsável**: DevOps Team
