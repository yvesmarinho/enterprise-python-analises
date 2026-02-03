# Alternativas para Coleta de Métricas (Sem Prometheus/Grafana)

## Visão Geral

Como não temos stack Prometheus/Grafana disponível, utilizaremos métodos diretos de coleta:

## 1. Métricas de Sistema (Docker Stats)

### Coleta via Docker CLI

```bash
# Coleta contínua a cada 30 segundos
while true; do
  echo "=== $(date -Iseconds) ===" >> n8n-tuning/data/docker_metrics.log
  docker stats n8n_n8n --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" >> n8n-tuning/data/docker_metrics.log
  sleep 30
done
```

### Coleta via Python

```python
# scripts/docker_metrics_collector.py
import subprocess
import json
import time
from datetime import datetime

def collect_docker_stats():
    result = subprocess.run(
        ['docker', 'stats', 'n8n_n8n', '--no-stream', '--format', '{{json .}}'],
        capture_output=True,
        text=True
    )
    
    stats = json.loads(result.stdout)
    stats['timestamp'] = datetime.now().isoformat()
    
    return stats

# Coletar a cada 30 segundos
while True:
    stats = collect_docker_stats()
    with open('data/docker_stats.jsonl', 'a') as f:
        json.dump(stats, f)
        f.write('\n')
    time.sleep(30)
```

## 2. Métricas do N8N (API)

### Via N8N API

```python
# Já implementado em scripts/n8n_metrics_collector.py
collector = N8NMetricsCollector(
    base_url="https://workflow.vya.digital",
    api_key="sua-api-key",
    output_dir="data/n8n_metrics"
)

# Coleta workflows e execuções
workflows = collector.collect_workflows()
executions = collector.collect_executions(limit=100)
```

### Métricas disponíveis via API:
- Total de workflows ativos/inativos
- Execuções por período (últimas 24h, 7d, 30d)
- Taxa de sucesso/erro
- Tempo médio de execução
- Workflows com mais execuções

## 3. Métricas do PostgreSQL

### Queries Diretas no Banco

```sql
-- Tamanho do banco de dados
SELECT pg_size_pretty(pg_database_size('n8n')) as db_size;

-- Top 10 queries mais lentas (requer pg_stat_statements)
SELECT 
  query,
  calls,
  total_exec_time,
  mean_exec_time,
  max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Tamanho das tabelas
SELECT 
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Conexões ativas
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';
```

### Script Python para coleta automática

```python
# scripts/postgres_metrics_collector.py
import psycopg2
import json
from datetime import datetime

def collect_postgres_metrics(credentials):
    conn = psycopg2.connect(**credentials['postgresql'])
    cur = conn.cursor()
    
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'metrics': {}
    }
    
    # Tamanho do banco
    cur.execute("SELECT pg_database_size('n8n')")
    metrics['metrics']['db_size_bytes'] = cur.fetchone()[0]
    
    # Conexões ativas
    cur.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
    metrics['metrics']['active_connections'] = cur.fetchone()[0]
    
    # Top 5 tabelas maiores
    cur.execute("""
        SELECT tablename, pg_total_relation_size(schemaname||'.'||tablename) as size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY size DESC
        LIMIT 5
    """)
    metrics['metrics']['top_tables'] = [
        {'table': row[0], 'size_bytes': row[1]} 
        for row in cur.fetchall()
    ]
    
    conn.close()
    return metrics
```

## 4. Logs do N8N

### Coleta de Logs Docker

```bash
# Exportar logs dos últimos 7 dias
docker logs n8n_n8n --since 7d > n8n-tuning/data/logs/n8n_7days.log

# Monitoramento contínuo
docker logs n8n_n8n -f --tail 100 | tee -a n8n-tuning/data/logs/n8n_realtime.log
```

### Análise de Logs Python

```python
import re
from collections import Counter

def analyze_logs(log_file):
    errors = []
    warnings = []
    execution_times = []
    
    with open(log_file) as f:
        for line in f:
            if 'ERROR' in line:
                errors.append(line)
            elif 'WARN' in line:
                warnings.append(line)
            
            # Extrair tempos de execução (se logados)
            match = re.search(r'execution time: (\d+)ms', line)
            if match:
                execution_times.append(int(match.group(1)))
    
    return {
        'total_errors': len(errors),
        'total_warnings': len(warnings),
        'avg_execution_time_ms': sum(execution_times) / len(execution_times) if execution_times else 0
    }
```

## 5. Métricas do Sistema Operacional

### Via SSH + comandos Linux

```bash
# CPU
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1

# Memória
free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }'

# Disco
df -h | grep '/dev/sda1' | awk '{print $5}'

# Processos N8N
ps aux | grep n8n
```

### Script Python com SSH

```python
import paramiko

def collect_system_metrics(credentials):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    ssh.connect(
        hostname=credentials['server']['host'],
        username=credentials['server']['ssh_user'],
        key_filename=credentials['server']['ssh_key_path']
    )
    
    # CPU
    stdin, stdout, stderr = ssh.exec_command("top -bn1 | grep 'Cpu(s)'")
    cpu_output = stdout.read().decode()
    
    # Memória
    stdin, stdout, stderr = ssh.exec_command("free -m")
    mem_output = stdout.read().decode()
    
    ssh.close()
    
    return {
        'cpu': cpu_output,
        'memory': mem_output
    }
```

## 6. Visualização Simples

### Gerar Relatórios HTML com Pandas

```python
import pandas as pd
import matplotlib.pyplot as plt

# Carregar dados coletados
df = pd.read_json('data/docker_stats.jsonl', lines=True)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Criar gráficos
fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# CPU
axes[0, 0].plot(df['timestamp'], df['CPUPerc'])
axes[0, 0].set_title('CPU Usage %')
axes[0, 0].tick_params(axis='x', rotation=45)

# Memória
axes[0, 1].plot(df['timestamp'], df['MemPerc'])
axes[0, 1].set_title('Memory Usage %')
axes[0, 1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('reports/metrics_overview.png')
```

## 7. Cronograma de Coleta Recomendado

### Setup Inicial

```bash
# 1. Criar estrutura de dados
mkdir -p n8n-tuning/data/{docker_stats,n8n_metrics,postgres_metrics,logs,system_metrics}

# 2. Iniciar coleta Docker (background)
nohup bash -c 'while true; do docker stats n8n_n8n --no-stream --format "{{json .}}" >> n8n-tuning/data/docker_stats/$(date +%Y%m%d).jsonl; sleep 30; done' &

# 3. Coletar logs
docker logs n8n_n8n --since 7d > n8n-tuning/data/logs/n8n_baseline.log
```

### Coleta Diária (Cron)

```cron
# Crontab: coletar métricas N8N via API (diariamente às 2h)
0 2 * * * cd /path/to/n8n-tuning && .venv/bin/python scripts/n8n_metrics_collector.py

# Coletar métricas PostgreSQL (a cada 6 horas)
0 */6 * * * cd /path/to/n8n-tuning && .venv/bin/python scripts/postgres_metrics_collector.py

# Backup de logs (diariamente às 23h)
0 23 * * * docker logs n8n_n8n --since 24h > /path/to/n8n-tuning/data/logs/n8n_$(date +%Y%m%d).log
```

## 8. Dependências Adicionais

Adicionar ao pyproject.toml:

```toml
dependencies = [
    "pandas>=3.0.0",
    "psycopg2-binary>=2.9.11",
    "requests>=2.32.5",
    "matplotlib>=3.8.0",      # Para gráficos
    "paramiko>=3.4.0",        # Para SSH (opcional)
]
```

## Vantagens desta Abordagem

✅ **Sem dependências externas**: Usa ferramentas nativas (Docker, psql)  
✅ **Leve**: Não requer servidores adicionais  
✅ **Customizável**: Scripts Python sob seu controle  
✅ **Dados brutos**: Formato JSON/CSV para análise posterior  
✅ **Portável**: Pode exportar para Grafana depois se necessário  

## Próximos Passos

1. ✅ Remover seções Grafana/Prometheus do credentials.json
2. Configurar coleta Docker em background
3. Obter API Key do N8N
4. Configurar acesso read-only ao PostgreSQL
5. Iniciar coleta de baseline (7 dias)
