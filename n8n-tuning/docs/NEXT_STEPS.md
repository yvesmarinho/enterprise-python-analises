# Próximos Passos - N8N Performance Monitoring

**Última Atualização**: 04/02/2026
**Status**: 📋 Roadmap Completo para 4 Semanas
**Objetivo**: Expandir monitoramento com métricas de infraestrutura

---

## 📊 Visão Geral

Este documento detalha o plano completo para expandir o sistema de monitoramento atual (N8N) para incluir:
- ✅ Métricas de **servidor** (CPU, RAM, Disco, Rede)
- ✅ Métricas do **serviço Docker** (Engine, Daemon)
- ✅ Métricas de **containers individuais** (recursos, health)
- ✅ **Dashboards Grafana** completos e customizados
- ✅ Sistema de **alertas** proativo

---

## 1. Preparar Stack Grafana/Victoria Metrics para Migração

### 1.1 Exportar Dados Coletados
**Objetivo**: Backup dos dados históricos antes da migração

**Passos**:
```bash
# Exportar snapshot do VictoriaMetrics
curl -X POST http://localhost:8428/snapshot/create

# Verificar snapshots disponíveis
ls -lh docker/victoria-metrics-data/snapshots/

# Documentar período e volume
echo "Período: $(date -d '7 days ago' '+%Y-%m-%d') até $(date '+%Y-%m-%d')" > backup_info.txt
du -sh docker/victoria-metrics-data/ >> backup_info.txt
```

**Validação**:
- ✅ Snapshot criado com sucesso
- ✅ Tamanho do backup documentado
- ✅ Integridade verificada (SHA256 checksum)

### 1.2 Configurar Volumes Persistentes
**Objetivo**: Estrutura de diretórios robusta para migração

**Estrutura Proposta**:
```bash
/opt/monitoring/
├── victoria-data/          # Dados do VictoriaMetrics
├── grafana-data/           # Dados do Grafana (dashboards, configs)
│   ├── dashboards/
│   ├── provisioning/
│   └── plugins/
├── scripts/                # Scripts de coleta Python
│   ├── n8n_metrics_collector.py
│   └── health_check.sh
├── logs/                   # Logs de coleta
└── secrets/                # Credenciais (não versionado)
    └── n8n_credentials.json
```

**Comandos de Preparação**:
```bash
# Criar estrutura no servidor de destino (wf001 ou wf002)
sudo mkdir -p /opt/monitoring/{victoria-data,grafana-data,scripts,logs,secrets}

# Configurar permissões
sudo chown -R 472:root /opt/monitoring/grafana-data
sudo chmod 755 /opt/monitoring/scripts
sudo chmod 700 /opt/monitoring/secrets
```

**Atualização do docker-compose.yml**:
```yaml
services:
  victoria-metrics:
    volumes:
      - /opt/monitoring/victoria-data:/victoria-metrics-data

  grafana:
    volumes:
      - /opt/monitoring/grafana-data:/var/lib/grafana
      - /opt/monitoring/grafana-data/provisioning:/etc/grafana/provisioning
```

### 1.3 Containerizar Scripts de Coleta
**Objetivo**: Coleta confiável e isolada via container

**Dockerfile** (`scripts/Dockerfile.collector`):
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Instalar dependências
RUN pip install --no-cache-dir requests prometheus-client

# Copiar scripts
COPY n8n_metrics_collector.py /app/
COPY health_check.sh /app/

# Configurar cron
RUN apt-get update && apt-get install -y cron && \
    echo "*/3 * * * * python /app/n8n_metrics_collector.py >> /logs/collector.log 2>&1" | crontab -

CMD ["cron", "-f"]
```

**Integração ao docker-compose.yml**:
```yaml
  n8n-collector:
    build:
      context: ./scripts
      dockerfile: Dockerfile.collector
    volumes:
      - /opt/monitoring/logs:/logs
      - /opt/monitoring/secrets:/secrets:ro
    environment:
      - N8N_URL=${N8N_URL}
      - VICTORIA_URL=http://victoria-metrics:8428
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "bash", "/app/health_check.sh"]
      interval: 5m
      timeout: 10s
      retries: 3
```

---

## 2. Instalação e Configuração do Node Exporter

### 2.1 Análise de Riscos e Impacto
**Riscos durante instalação em horário comercial**:
- ✅ **Baixo risco**: Node Exporter é processo read-only, não modifica sistema
- ⚠️ **Consumo de recursos**: ~10-20MB RAM, CPU negligível (<0.1%)
- ✅ **Sem downtime**: Instalação não requer reinicialização do N8N
- ⚠️ **Exposição de porta**: Porta 9100 deve ser protegida (firewall/VPN)
- ✅ **Reversível**: Fácil remoção se necessário

**Recomendação**: ✅ Pode ser instalado em horário comercial com impacto mínimo

### 2.2 Instalação via Docker (Método Recomendado)
**Por que Docker?**
- ✅ Isolamento e segurança
- ✅ Fácil atualização e rollback
- ✅ Gerenciamento centralizado com docker-compose
- ✅ Logs estruturados

**Adicionar ao docker-compose.yml**:
```yaml
services:
  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: unless-stopped
    network_mode: host
    pid: host
    volumes:
      - /:/host:ro,rslave
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    command:
      - '--path.rootfs=/host'
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
      - '--collector.netclass.ignored-devices=^(veth.*|br.*|docker.*)$$'
      - '--collector.netdev.device-exclude=^(veth.*|br.*|docker.*)$$'
    labels:
      - "monitoring.type=infrastructure"
      - "monitoring.target=host"
```

**Comandos de Deploy**:
```bash
# Adicionar serviço ao docker-compose
cd /path/to/monitoring/stack
vim docker-compose.yml  # Adicionar configuração acima

# Iniciar Node Exporter
docker-compose up -d node-exporter

# Verificar logs
docker logs node-exporter --tail 50

# Testar endpoint de métricas
curl http://localhost:9100/metrics | head -20
```

**Validação Pós-Instalação**:
```bash
# Verificar se está rodando
docker ps | grep node-exporter

# Testar métricas específicas
curl -s http://localhost:9100/metrics | grep "node_cpu_seconds_total"
curl -s http://localhost:9100/metrics | grep "node_memory_MemAvailable_bytes"
curl -s http://localhost:9100/metrics | grep "node_filesystem_avail_bytes"

# Verificar uso de recursos do próprio exporter
docker stats node-exporter --no-stream
```

### 2.3 Configurar VictoriaMetrics para Scrape
**Adicionar target ao VictoriaMetrics**:

**Opção 1 - Scrape Config File** (Recomendado):
Criar arquivo `prometheus-targets.yml`:
```yaml
scrape_configs:
  - job_name: 'n8n-metrics'
    scrape_interval: 3m
    static_configs:
      - targets: ['wf005.vya.digital:5678']
    metrics_path: '/metrics'

  - job_name: 'node-exporter'
    scrape_interval: 30s
    static_configs:
      - targets: ['localhost:9100']
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'node_.*'
        action: keep

  - job_name: 'cadvisor'
    scrape_interval: 30s
    static_configs:
      - targets: ['localhost:8080']
```

Atualizar docker-compose.yml:
```yaml
  victoria-metrics:
    image: victoriametrics/victoria-metrics:latest
    command:
      - '-storageDataPath=/victoria-metrics-data'
      - '-retentionPeriod=90d'
      - '-promscrape.config=/etc/victoria/scrape-config.yml'
    volumes:
      - /opt/monitoring/victoria-data:/victoria-metrics-data
      - ./prometheus-targets.yml:/etc/victoria/scrape-config.yml:ro
```

**Opção 2 - Push via Python Collector**:
Atualizar `n8n_metrics_collector.py` para coletar do Node Exporter:
```python
import requests

# Coletar métricas do Node Exporter
node_metrics = requests.get('http://localhost:9100/metrics').text

# Enviar para VictoriaMetrics
requests.post(
    'http://localhost:8428/api/v1/import/prometheus',
    data=node_metrics
)
```

**Validação da Integração**:
```bash
# Verificar se VictoriaMetrics está coletando
curl -s 'http://localhost:8428/api/v1/label/__name__/values' | grep node_

# Query de teste no VictoriaMetrics
curl -s 'http://localhost:8428/api/v1/query?query=node_cpu_seconds_total' | jq .
```

---

## 3. Instalação e Configuração do cAdvisor (Container Metrics)

### 3.1 Por Que cAdvisor?
**Vantagens sobre alternativas**:
- ✅ **Específico para containers**: Métricas detalhadas por container
- ✅ **Zero configuração**: Autodescoberta de containers
- ✅ **Leve**: ~50MB RAM, CPU mínimo
- ✅ **Integração nativa**: Formato Prometheus ready
- ✅ **UI embutida**: Interface web para debug (porta 8080)

**Comparação com Alternativas**:
| Solução | Métricas Container | Métricas Sistema | Complexidade | RAM |
|---------|-------------------|------------------|--------------|-----|
| cAdvisor | ✅✅✅ Excelente | ❌ Não | Baixa | ~50MB |
| Node Exporter | ❌ Não | ✅✅✅ Excelente | Baixa | ~20MB |
| Docker Daemon | ⚠️ Básicas | ❌ Não | Média | N/A |
| **Recomendado** | **cAdvisor + Node Exporter** | | | **~70MB** |

### 3.2 Instalação do cAdvisor
**Adicionar ao docker-compose.yml**:
```yaml
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    restart: unless-stopped
    privileged: true
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    devices:
      - /dev/kmsg
    labels:
      - "monitoring.type=infrastructure"
      - "monitoring.target=containers"
```

**Deploy e Validação**:
```bash
# Iniciar cAdvisor
docker-compose up -d cadvisor

# Verificar logs
docker logs cadvisor --tail 50

# Acessar UI (opcional)
# Abrir navegador: http://wf005.vya.digital:8080

# Testar endpoint de métricas
curl http://localhost:8080/metrics | grep container_cpu

# Verificar métricas do próprio N8N
curl -s http://localhost:8080/metrics | grep 'container_name="n8n_n8n"'
```

**Adicionar ao Scrape Config**:
```yaml
scrape_configs:
  - job_name: 'cadvisor'
    scrape_interval: 30s
    static_configs:
      - targets: ['localhost:8080']
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'container_.*'
        action: keep
```

### 3.3 Métricas Disponíveis

**Métricas de CPU por Container**:
- `container_cpu_usage_seconds_total` - Uso total de CPU
- `container_cpu_system_seconds_total` - CPU em modo kernel
- `container_cpu_user_seconds_total` - CPU em modo user
- `container_spec_cpu_quota` - Limite de CPU configurado
- `container_cpu_cfs_throttled_seconds_total` - Tempo throttled

**Métricas de Memória**:
- `container_memory_usage_bytes` - Uso atual de memória
- `container_memory_working_set_bytes` - Working set (usado pelo OOM killer)
- `container_memory_rss` - Resident Set Size
- `container_memory_cache` - Cache
- `container_spec_memory_limit_bytes` - Limite configurado
- `container_memory_failcnt` - Falhas de alocação

**Métricas de Rede**:
- `container_network_receive_bytes_total` - Bytes recebidos
- `container_network_transmit_bytes_total` - Bytes transmitidos
- `container_network_receive_packets_total` - Pacotes recebidos
- `container_network_transmit_packets_total` - Pacotes transmitidos

**Métricas de Disco**:
- `container_fs_usage_bytes` - Uso de disco
- `container_fs_limit_bytes` - Limite de disco
- `container_fs_reads_total` - Operações de leitura
- `container_fs_writes_total` - Operações de escrita

---

## 4. Criação de Dashboards no Grafana

### 4.1 Dashboard: System Overview (Servidor)
**Objetivo**: Visão geral da saúde do servidor wf005

**Painéis Recomendados**:

#### Painel 1: CPU Overview
```json
{
  "title": "CPU Usage by Core",
  "type": "graph",
  "targets": [{
    "expr": "100 - (avg by (cpu) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)"
  }]
}
```

#### Painel 2: Memory Usage
```json
{
  "title": "Memory Usage",
  "type": "graph",
  "targets": [
    {
      "expr": "node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes",
      "legendFormat": "Used"
    },
    {
      "expr": "node_memory_MemAvailable_bytes",
      "legendFormat": "Available"
    }
  ]
}
```

#### Painel 3: Disk Usage
```json
{
  "title": "Disk Space Usage",
  "type": "gauge",
  "targets": [{
    "expr": "100 - ((node_filesystem_avail_bytes{mountpoint=\"/\"} / node_filesystem_size_bytes{mountpoint=\"/\"}) * 100)"
  }]
}
```

#### Painel 4: Network Traffic
```json
{
  "title": "Network I/O",
  "type": "graph",
  "targets": [
    {
      "expr": "irate(node_network_receive_bytes_total{device!~\"veth.*|br.*|docker.*\"}[5m])",
      "legendFormat": "RX - {{device}}"
    },
    {
      "expr": "irate(node_network_transmit_bytes_total{device!~\"veth.*|br.*|docker.*\"}[5m])",
      "legendFormat": "TX - {{device}}"
    }
  ]
}
```

#### Painel 5: Load Average
```json
{
  "title": "System Load",
  "type": "stat",
  "targets": [
    {"expr": "node_load1", "legendFormat": "1m"},
    {"expr": "node_load5", "legendFormat": "5m"},
    {"expr": "node_load15", "legendFormat": "15m"}
  ]
}
```

#### Painel 6: Disk I/O
```json
{
  "title": "Disk I/O Operations",
  "type": "graph",
  "targets": [
    {
      "expr": "irate(node_disk_reads_completed_total[5m])",
      "legendFormat": "Reads - {{device}}"
    },
    {
      "expr": "irate(node_disk_writes_completed_total[5m])",
      "legendFormat": "Writes - {{device}}"
    }
  ]
}
```

**Criação do Dashboard**:
```bash
# Criar arquivo JSON
cat > docker/grafana/dashboards/system-overview.json << 'EOF'
{
  "dashboard": {
    "title": "System Overview - wf005",
    "tags": ["infrastructure", "node-exporter"],
    "timezone": "browser",
    "panels": [
      // Adicionar painéis acima
    ]
  }
}
EOF

# Recarregar provisioning
curl -X POST -u admin:W123Mudar http://localhost:3100/api/admin/provisioning/dashboards/reload
```

### 4.2 Dashboard: Docker Engine (Serviço Docker)
**Objetivo**: Monitorar o daemon Docker e recursos gerais

**Painéis Recomendados**:

#### Painel 1: Containers Status
```json
{
  "title": "Container Status",
  "type": "stat",
  "targets": [
    {
      "expr": "count(container_last_seen{name!=\"\"})",
      "legendFormat": "Total Containers"
    },
    {
      "expr": "count(container_last_seen{name!=\"\"}) - count(container_last_seen{name!=\"\"} offset 5m)",
      "legendFormat": "Recently Started"
    }
  ]
}
```

#### Painel 2: Total CPU Usage (All Containers)
```json
{
  "title": "Total Container CPU Usage",
  "type": "graph",
  "targets": [{
    "expr": "sum(irate(container_cpu_usage_seconds_total{name!=\"\"}[5m])) * 100"
  }]
}
```

#### Painel 3: Total Memory Usage
```json
{
  "title": "Total Container Memory",
  "type": "graph",
  "targets": [{
    "expr": "sum(container_memory_working_set_bytes{name!=\"\"})"
  }]
}
```

#### Painel 4: Network Traffic (All Containers)
```json
{
  "title": "Total Container Network I/O",
  "type": "graph",
  "targets": [
    {
      "expr": "sum(irate(container_network_receive_bytes_total[5m]))",
      "legendFormat": "RX"
    },
    {
      "expr": "sum(irate(container_network_transmit_bytes_total[5m]))",
      "legendFormat": "TX"
    }
  ]
}
```

### 4.3 Dashboard: Container Performance (Individual)
**Objetivo**: Análise detalhada de cada container

**Painéis Recomendados**:

#### Painel 1: CPU Usage by Container (Tabela)
```json
{
  "title": "Container CPU Usage (%)",
  "type": "table",
  "targets": [{
    "expr": "sort_desc(sum by (name) (irate(container_cpu_usage_seconds_total{name!=\"\"}[5m])) * 100)",
    "format": "table",
    "instant": true
  }],
  "transformations": [
    {"id": "organize", "options": {
      "renameByName": {"Value": "CPU %"},
      "indexByName": {"name": 0, "Value": 1}
    }},
    {"id": "sortBy", "options": {"sort": [{"field": "CPU %", "desc": true}]}}
  ]
}
```

#### Painel 2: Memory Usage by Container (Tabela)
```json
{
  "title": "Container Memory Usage",
  "type": "table",
  "targets": [{
    "expr": "sort_desc(container_memory_working_set_bytes{name!=\"\"})",
    "format": "table",
    "instant": true
  }],
  "transformations": [
    {"id": "organize", "options": {
      "renameByName": {"Value": "Memory (bytes)"},
      "indexByName": {"name": 0, "Value": 1}
    }},
    {"id": "sortBy", "options": {"sort": [{"field": "Memory (bytes)", "desc": true}]}}
  ]
}
```

#### Painel 3: N8N Container CPU (Gráfico)
```json
{
  "title": "N8N CPU Usage Over Time",
  "type": "graph",
  "targets": [{
    "expr": "irate(container_cpu_usage_seconds_total{name=~\".*n8n.*\"}[5m]) * 100"
  }]
}
```

#### Painel 4: N8N Container Memory (Gráfico)
```json
{
  "title": "N8N Memory Usage Over Time",
  "type": "graph",
  "targets": [
    {
      "expr": "container_memory_working_set_bytes{name=~\".*n8n.*\"}",
      "legendFormat": "Working Set"
    },
    {
      "expr": "container_memory_rss{name=~\".*n8n.*\"}",
      "legendFormat": "RSS"
    },
    {
      "expr": "container_spec_memory_limit_bytes{name=~\".*n8n.*\"}",
      "legendFormat": "Limit"
    }
  ]
}
```

#### Painel 5: Container Restarts
```json
{
  "title": "Container Restart Count",
  "type": "stat",
  "targets": [{
    "expr": "changes(container_last_seen{name!=\"\"}[24h])"
  }]
}
```

#### Painel 6: Container Network I/O
```json
{
  "title": "Network I/O by Container",
  "type": "graph",
  "targets": [
    {
      "expr": "topk(5, irate(container_network_receive_bytes_total{name!=\"\"}[5m]))",
      "legendFormat": "RX - {{name}}"
    },
    {
      "expr": "topk(5, irate(container_network_transmit_bytes_total{name!=\"\"}[5m]))",
      "legendFormat": "TX - {{name}}"
    }
  ]
}
```

### 4.4 Exportar Dashboards Existentes como Template
```bash
# Exportar dashboard via API
curl -u admin:W123Mudar \
  'http://localhost:3100/api/dashboards/uid/n8n-overview' | \
  jq .dashboard > templates/n8n-overview-template.json

# Criar novos dashboards baseados no template
# Substituir queries e títulos conforme necessário
```

---

## 5. Sistema de Alertas

### 5.1 Alertas de Servidor (Node Exporter)

**Alerta 1: CPU Alto**
```yaml
alert: HostHighCpuLoad
expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
for: 5m
labels:
  severity: warning
annotations:
  summary: "CPU usage above 80% on {{ $labels.instance }}"
  description: "CPU: {{ $value | humanize }}%"
```

**Alerta 2: Memória Baixa**
```yaml
alert: HostOutOfMemory
expr: node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100 < 10
for: 2m
labels:
  severity: critical
annotations:
  summary: "Host out of memory on {{ $labels.instance }}"
  description: "Available: {{ $value | humanize }}%"
```

**Alerta 3: Disco Cheio**
```yaml
alert: HostDiskSpaceFillingUp
expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100) < 15
for: 1m
labels:
  severity: critical
annotations:
  summary: "Disk space critically low on {{ $labels.instance }}"
  description: "Free: {{ $value | humanize }}%"
```

**Alerta 4: Load Average Alto**
```yaml
alert: HostHighLoad
expr: node_load15 / count(node_cpu_seconds_total{mode="idle"}) without (cpu, mode) > 1.5
for: 10m
labels:
  severity: warning
annotations:
  summary: "High load average on {{ $labels.instance }}"
  description: "Load: {{ $value | humanize }}"
```

### 5.2 Alertas de Containers (cAdvisor)

**Alerta 1: Container CPU Alto**
```yaml
alert: ContainerHighCpu
expr: sum by (name) (irate(container_cpu_usage_seconds_total{name!=""}[5m])) * 100 > 80
for: 5m
labels:
  severity: warning
annotations:
  summary: "Container {{ $labels.name }} using high CPU"
  description: "CPU: {{ $value | humanize }}%"
```

**Alerta 2: Container Memória Alta**
```yaml
alert: ContainerMemoryUsage
expr: (container_memory_working_set_bytes{name!=""} / container_spec_memory_limit_bytes{name!=""}) * 100 > 90
for: 2m
labels:
  severity: warning
annotations:
  summary: "Container {{ $labels.name }} high memory usage"
  description: "Memory: {{ $value | humanize }}%"
```

**Alerta 3: Container Reiniciando**
```yaml
alert: ContainerRestarting
expr: rate(container_last_seen{name!=""}[5m]) > 0
for: 1m
labels:
  severity: critical
annotations:
  summary: "Container {{ $labels.name }} is restarting"
```

### 5.3 Configurar Notification Channels
**Exemplo: Slack**
```yaml
# docker/grafana/provisioning/notifiers/slack.yml
apiVersion: 1
notifiers:
  - name: slack-alerts
    type: slack
    uid: slack-notifier
    org_id: 1
    is_default: true
    send_reminder: true
    settings:
      url: ${SLACK_WEBHOOK_URL}
      recipient: '#n8n-alerts'
      username: 'Grafana Alerts'
```

**Exemplo: Email**
```yaml
# docker/grafana/provisioning/notifiers/email.yml
apiVersion: 1
notifiers:
  - name: email-alerts
    type: email
    uid: email-notifier
    org_id: 1
    settings:
      addresses: 'devops@empresa.com'
      singleEmail: true
```

---

## 6. Medição de Latência de Rede e Bancos de Dados

### 6.1 Visão Geral da Solução

**Objetivo**: Monitorar latência entre datacenters e performance de acesso a bancos de dados

**Componentes**:
1. **Ping Service** (wf008 - Brasil) → Envia requisições HTTP com timestamp
2. **Collector API** (wf001 - USA) → Recebe requisições e calcula latência
3. **Database Probes** → Mede latência PostgreSQL e MySQL
4. **VictoriaMetrics** → Armazena métricas de latência
5. **Grafana Dashboard** → Visualização integrada no N8N Overview

**Métricas Coletadas**:
- ✅ Latência de rede Brasil → USA (round-trip time)
- ✅ Latência de resposta da API
- ✅ Latência de consulta PostgreSQL
- ✅ Latência de consulta MySQL
- ✅ Disponibilidade dos serviços (uptime)
- ✅ Taxa de perda de pacotes (packet loss)

### 6.2 Arquitetura da Solução

```
┌─────────────────────────────────────────────────────────────────┐
│                    wf008 (Brasil - São Paulo)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Ping Service Container (Python/FastAPI)                  │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  Cron Job (a cada 30s):                            │  │   │
│  │  │  1. Captura timestamp_start                        │  │   │
│  │  │  2. Envia POST para wf001/api/ping                 │  │   │
│  │  │  3. Payload: {timestamp, source, metrics}          │  │   │
│  │  │  4. Aguarda resposta                               │  │   │
│  │  │  5. Calcula RTT (round-trip time)                  │  │   │
│  │  │  6. Push para VictoriaMetrics local (opcional)     │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP POST (TLS)
                              │ {timestamp_start, source_location}
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     wf001 (USA - Virginia)                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  N8N Metrics Collector (Expandido)                       │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  Nova API Endpoint: /api/ping                      │  │   │
│  │  │  1. Recebe requisição                              │  │   │
│  │  │  2. Captura timestamp_received                     │  │   │
│  │  │  3. Calcula latency_inbound                        │  │   │
│  │  │  4. Executa health checks:                         │  │   │
│  │  │     - PostgreSQL query latency                     │  │   │
│  │  │     - MySQL query latency                          │  │   │
│  │  │     - N8N API health                               │  │   │
│  │  │  5. Gera métricas Prometheus                       │  │   │
│  │  │  6. Push para VictoriaMetrics                      │  │   │
│  │  │  7. Retorna resposta com timestamp_response        │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │                                                           │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  Database Probe Service (Contínuo)                 │  │   │
│  │  │  - Intervalo: 60s                                  │  │   │
│  │  │  - Test Query PostgreSQL: SELECT 1                 │  │   │
│  │  │  - Test Query MySQL: SELECT 1                      │  │   │
│  │  │  - Métricas: latency, availability                 │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  VictoriaMetrics                                         │   │
│  │  - Métricas de latência armazenadas                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Grafana Dashboard: N8N Performance Overview             │   │
│  │  + Novo Painel: Network & Database Latency              │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Métricas Detalhadas

#### 6.3.1 Métricas de Latência de Rede

**network_latency_rtt_seconds**
- **Descrição**: Round-Trip Time (RTT) Brasil → USA → Brasil
- **Labels**:
  - `source_location="sao_paulo"`
  - `target_location="virginia"`
  - `protocol="https"`
- **Cálculo**: `timestamp_response - timestamp_start`
- **Interpretação**:
  - < 150ms: ✅ Excelente
  - 150-250ms: ⚠️ Aceitável
  - > 250ms: ❌ Problemático

**network_latency_inbound_seconds**
- **Descrição**: Latência da requisição Brasil → USA (one-way)
- **Labels**: `source_location`, `target_location`
- **Cálculo**: `timestamp_received - timestamp_start`
- **Nota**: Requer sincronização de relógio (NTP)

**network_latency_outbound_seconds**
- **Descrição**: Latência da resposta USA → Brasil (one-way)
- **Labels**: `source_location`, `target_location`
- **Cálculo**: `timestamp_end - timestamp_response`

**network_availability_ratio**
- **Descrição**: Taxa de sucesso das requisições (uptime)
- **Labels**: `source_location`, `target_location`
- **Cálculo**: `successful_requests / total_requests`
- **Target**: > 99.5%

**network_packet_loss_ratio**
- **Descrição**: Taxa de perda de pacotes
- **Labels**: `source_location`, `target_location`
- **Cálculo**: `failed_requests / total_requests`
- **Target**: < 0.5%

#### 6.3.2 Métricas de Latência de Bancos de Dados

**database_query_latency_seconds**
- **Descrição**: Tempo de resposta de consulta de teste
- **Labels**:
  - `database_type="postgresql|mysql"`
  - `database_host="hostname"`
  - `query_type="simple_select|health_check"`
- **Query de Teste**: `SELECT 1`
- **Interpretação**:
  - < 5ms: ✅ Excelente
  - 5-20ms: ⚠️ Aceitável
  - > 20ms: ❌ Investigar

**database_connection_latency_seconds**
- **Descrição**: Tempo para estabelecer conexão
- **Labels**: `database_type`, `database_host`
- **Cálculo**: Tempo do handshake TCP + autenticação
- **Interpretação**:
  - < 10ms: ✅ Excelente
  - 10-50ms: ⚠️ Aceitável
  - > 50ms: ❌ Investigar

**database_availability_ratio**
- **Descrição**: Disponibilidade do banco de dados
- **Labels**: `database_type`, `database_host`
- **Cálculo**: `successful_connections / total_attempts`
- **Target**: > 99.9%

**database_connection_pool_active**
- **Descrição**: Conexões ativas no pool
- **Labels**: `database_type`, `application="n8n|collector"`
- **Uso**: Identificar gargalos de conexão

**database_connection_pool_idle**
- **Descrição**: Conexões ociosas no pool
- **Labels**: `database_type`, `application`
- **Uso**: Otimizar tamanho do pool

#### 6.3.3 Métricas de API (Collector)

**api_request_duration_seconds**
- **Descrição**: Tempo de processamento da API /api/ping
- **Labels**: `endpoint="/api/ping"`, `method="POST"`, `status="200|500"`
- **Histogram buckets**: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1]

**api_request_total**
- **Descrição**: Total de requisições recebidas
- **Labels**: `endpoint`, `method`, `status`
- **Counter**: Incrementa a cada requisição

**api_request_errors_total**
- **Descrição**: Total de erros na API
- **Labels**: `endpoint`, `error_type="timeout|connection|internal"`
- **Counter**: Incrementa em caso de erro

### 6.4 Estrutura de Dados

#### 6.4.1 Payload da Requisição (wf008 → wf001)

```json
{
  "timestamp_start": "2026-02-04T10:30:45.123456Z",
  "source": {
    "location": "sao_paulo",
    "datacenter": "wf008",
    "country": "BR",
    "ip": "203.0.113.10"
  },
  "ping_id": "uuid-v4-here",
  "sequence_number": 12345,
  "protocol_version": "1.0"
}
```

#### 6.4.2 Payload da Resposta (wf001 → wf008)

```json
{
  "timestamp_received": "2026-02-04T10:30:45.250000Z",
  "timestamp_response": "2026-02-04T10:30:45.255000Z",
  "target": {
    "location": "virginia",
    "datacenter": "wf001",
    "country": "US",
    "ip": "198.51.100.20"
  },
  "ping_id": "uuid-v4-here",
  "latency_inbound_ms": 126.544,
  "processing_time_ms": 5.123,
  "health_checks": {
    "postgresql": {
      "available": true,
      "latency_ms": 3.45,
      "host": "postgres.internal"
    },
    "mysql": {
      "available": true,
      "latency_ms": 2.89,
      "host": "mysql.internal"
    },
    "n8n_api": {
      "available": true,
      "latency_ms": 45.67
    }
  },
  "status": "success"
}
```

#### 6.4.3 Formato das Métricas Prometheus

```prometheus
# Latência de rede
network_latency_rtt_seconds{source_location="sao_paulo",target_location="virginia",protocol="https"} 0.252
network_latency_inbound_seconds{source_location="sao_paulo",target_location="virginia"} 0.127
network_availability_ratio{source_location="sao_paulo",target_location="virginia"} 0.998

# Latência de banco de dados
database_query_latency_seconds{database_type="postgresql",database_host="postgres.internal",query_type="health_check"} 0.00345
database_query_latency_seconds{database_type="mysql",database_host="mysql.internal",query_type="health_check"} 0.00289
database_availability_ratio{database_type="postgresql",database_host="postgres.internal"} 1.0

# API Collector
api_request_duration_seconds{endpoint="/api/ping",method="POST",status="200"} 0.005
api_request_total{endpoint="/api/ping",method="POST",status="200"} 12345
```

### 6.5 Componentes de Software

#### 6.5.1 Ping Service (wf008 - Brasil)

**Tecnologias**:
- Python 3.12
- httpx (async HTTP client)
- APScheduler (cron jobs)
- prometheus-client (métricas)

**Estrutura**:
```
ping-service/
├── Dockerfile
├── requirements.txt
├── config.yaml
├── src/
│   ├── ping_client.py      # Cliente HTTP
│   ├── scheduler.py        # Cron jobs
│   ├── metrics.py          # Prometheus metrics
│   └── main.py             # Entry point
└── docker-compose.yml
```

**Responsabilidades**:
1. Enviar requisições HTTP POST a cada 30s
2. Calcular RTT (round-trip time)
3. Retry logic com exponential backoff
4. Logging estruturado
5. Health check endpoint
6. Exportar métricas Prometheus (porta 9101)

**Configuração**:
```yaml
# config.yaml
targets:
  - name: "wf001-usa"
    url: "https://wf001.vya.digital:5000/api/ping"
    interval_seconds: 30
    timeout_seconds: 10
    retry_attempts: 3

source:
  location: "sao_paulo"
  datacenter: "wf008"
  country: "BR"

metrics:
  push_gateway: "http://victoria-metrics:8428/api/v1/import/prometheus"
  export_interval_seconds: 60
```

#### 6.5.2 Collector API Expansion (wf001 - USA)

**Expansões Necessárias no n8n_metrics_collector.py**:

**Novos Módulos**:
```
n8n-tuning/scripts/
├── n8n_metrics_collector.py         # Existente (expandir)
├── ping_api.py                       # NOVO - API endpoint
├── database_probe.py                 # NOVO - DB health checks
├── metrics_exporter.py               # NOVO - Export to Victoria
└── config/
    ├── api_config.yaml               # NOVO - API settings
    └── database_config.yaml          # NOVO - DB connections
```

**Responsabilidades da API (/api/ping)**:
1. Receber POST com timestamp
2. Validar payload (schema validation)
3. Calcular latência inbound
4. Executar health checks (PostgreSQL, MySQL, N8N)
5. Gerar métricas Prometheus
6. Push para VictoriaMetrics
7. Retornar resposta com timestamps e health status
8. Rate limiting (max 120 req/min)
9. Authentication (API key)
10. Logging de todas as requisições

**Responsabilidades do Database Probe**:
1. Conectar a PostgreSQL e MySQL
2. Executar queries de teste (`SELECT 1`)
3. Medir latência de conexão
4. Medir latência de query
5. Detectar falhas e timeouts
6. Monitorar pool de conexões
7. Exportar métricas a cada 60s
8. Circuit breaker pattern (evitar sobrecarga)

**Tecnologias Adicionais**:
- FastAPI (API framework)
- psycopg3 (PostgreSQL async driver)
- aiomysql (MySQL async driver)
- pydantic (data validation)
- uvicorn (ASGI server)

#### 6.5.3 Integração com Docker Compose

**Atualização do docker-compose.yml (wf001)**:
```yaml
services:
  n8n-collector:
    build:
      context: ./scripts
      dockerfile: Dockerfile.collector
    ports:
      - "5000:5000"  # API endpoint
      - "9102:9102"  # Prometheus metrics
    environment:
      - API_KEY=${COLLECTOR_API_KEY}
      - POSTGRES_HOST=${POSTGRES_HOST}
      - POSTGRES_PORT=${POSTGRES_PORT}
      - MYSQL_HOST=${MYSQL_HOST}
      - MYSQL_PORT=${MYSQL_PORT}
    volumes:
      - /opt/monitoring/logs:/logs
      - /opt/monitoring/secrets:/secrets:ro
    depends_on:
      - victoria-metrics
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

**Novo serviço para Ping Service (wf008)**:
```yaml
services:
  ping-service:
    build:
      context: ./ping-service
      dockerfile: Dockerfile
    environment:
      - TARGET_URL=https://wf001.vya.digital:5000/api/ping
      - API_KEY=${COLLECTOR_API_KEY}
      - PING_INTERVAL=30
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9101/metrics"]
      interval: 60s
      timeout: 5s
      retries: 3
```

### 6.6 Dashboard: Network & Database Latency

**Novo Painel no "N8N Performance Overview"**:

#### Painel 1: Network Latency (Brasil → USA)

**Tipo**: Graph (Time Series)

**Query 1 - RTT**:
```promql
network_latency_rtt_seconds{source_location="sao_paulo", target_location="virginia"} * 1000
```
**Legend**: Round-Trip Time (ms)

**Query 2 - Inbound**:
```promql
network_latency_inbound_seconds{source_location="sao_paulo", target_location="virginia"} * 1000
```
**Legend**: Inbound Latency (ms)

**Thresholds**:
- Verde: < 150ms
- Amarelo: 150-250ms
- Vermelho: > 250ms

#### Painel 2: Network Availability

**Tipo**: Stat (Gauge)

**Query**:
```promql
network_availability_ratio{source_location="sao_paulo", target_location="virginia"} * 100
```
**Unit**: Percent (0-100)
**Decimals**: 2
**Thresholds**:
- Verde: > 99.5%
- Amarelo: 98-99.5%
- Vermelho: < 98%

#### Painel 3: Database Query Latency

**Tipo**: Graph (Time Series)

**Query PostgreSQL**:
```promql
database_query_latency_seconds{database_type="postgresql"} * 1000
```
**Legend**: PostgreSQL Query (ms)

**Query MySQL**:
```promql
database_query_latency_seconds{database_type="mysql"} * 1000
```
**Legend**: MySQL Query (ms)

**Thresholds**:
- Verde: < 5ms
- Amarelo: 5-20ms
- Vermelho: > 20ms

#### Painel 4: Database Availability

**Tipo**: Table

**Query**:
```promql
database_availability_ratio * 100
```

**Columns**:
- Database Type
- Host
- Availability (%)
- Last Check

**Transformations**:
- Sort by Availability (desc)
- Color coding (verde > 99%, amarelo 95-99%, vermelho < 95%)

#### Painel 5: API Performance

**Tipo**: Graph (Histogram)

**Query**:
```promql
histogram_quantile(0.95, rate(api_request_duration_seconds_bucket{endpoint="/api/ping"}[5m])) * 1000
```
**Legend**: P95 Latency (ms)

**Query 2**:
```promql
histogram_quantile(0.99, rate(api_request_duration_seconds_bucket{endpoint="/api/ping"}[5m])) * 1000
```
**Legend**: P99 Latency (ms)

#### Painel 6: Combined Health Status

**Tipo**: Stat (Multi-stat)

**Queries**:
```promql
# Network Health
(network_availability_ratio > 0.995) * 100

# PostgreSQL Health
(database_availability_ratio{database_type="postgresql"} > 0.999) * 100

# MySQL Health
(database_availability_ratio{database_type="mysql"} > 0.999) * 100

# API Health
(rate(api_request_errors_total[5m]) == 0) * 100
```

**Display**:
- ✅ Verde: Todos saudáveis
- ⚠️ Amarelo: 1 componente degradado
- ❌ Vermelho: 2+ componentes com problema

### 6.7 Alertas de Latência

#### Alerta 1: Alta Latência de Rede

```yaml
alert: HighNetworkLatency
expr: network_latency_rtt_seconds{source_location="sao_paulo"} > 0.300
for: 5m
labels:
  severity: warning
  component: network
annotations:
  summary: "High network latency between Brazil and USA"
  description: "RTT: {{ $value | humanize }}s (threshold: 300ms)"
  action: "Check network connectivity and routing"
```

#### Alerta 2: Perda de Conectividade

```yaml
alert: NetworkConnectivityLoss
expr: network_availability_ratio{source_location="sao_paulo"} < 0.95
for: 2m
labels:
  severity: critical
  component: network
annotations:
  summary: "Network connectivity issues detected"
  description: "Availability: {{ $value | humanizePercentage }} (threshold: 95%)"
  action: "Investigate network outage or routing issues"
```

#### Alerta 3: Banco de Dados Lento

```yaml
alert: SlowDatabaseResponse
expr: database_query_latency_seconds > 0.050
for: 5m
labels:
  severity: warning
  component: database
annotations:
  summary: "Slow database response on {{ $labels.database_type }}"
  description: "Query latency: {{ $value | humanize }}s (threshold: 50ms)"
  action: "Check database load and optimize queries"
```

#### Alerta 4: Banco de Dados Indisponível

```yaml
alert: DatabaseUnavailable
expr: database_availability_ratio < 0.99
for: 1m
labels:
  severity: critical
  component: database
annotations:
  summary: "Database {{ $labels.database_type }} unavailable"
  description: "Availability: {{ $value | humanizePercentage }}"
  action: "Check database service status and connectivity"
```

#### Alerta 5: API Collector com Erros

```yaml
alert: CollectorAPIErrors
expr: rate(api_request_errors_total{endpoint="/api/ping"}[5m]) > 0.1
for: 2m
labels:
  severity: warning
  component: api
annotations:
  summary: "High error rate on collector API"
  description: "Error rate: {{ $value | humanize }} req/s"
  action: "Check collector API logs and health"
```

### 6.8 Considerações Técnicas

#### 6.8.1 Sincronização de Tempo (NTP)

**Problema**: Cálculo de latência one-way requer relógios sincronizados

**Solução**:
- Configurar NTP em ambos servidores (wf008 e wf001)
- Usar servidores NTP públicos confiáveis:
  - `time.google.com`
  - `time.cloudflare.com`
  - `pool.ntp.org`
- Validar drift máximo: < 10ms
- Monitorar offset do NTP como métrica adicional

**Comando de Validação**:
```bash
# Verificar status NTP
timedatectl status

# Verificar offset
chronyc tracking

# Sincronizar manualmente (se necessário)
sudo chronyc -a makestep
```

**Métrica Adicional**:
```prometheus
ntp_offset_seconds{server="time.google.com"} 0.003
```

#### 6.8.2 Segurança

**API Authentication**:
- API Key no header: `X-API-Key: secret-token-here`
- Rate limiting: 120 requisições/minuto por IP
- HTTPS obrigatório (TLS 1.3)
- CORS configurado (apenas wf008)

**Credenciais de Banco de Dados**:
- Usuário read-only dedicado
- Permissões mínimas: `SELECT`, `CONNECT`
- Conexão via TLS/SSL
- Credenciais em secrets (não versionadas)
- Rotação de credenciais: mensal

**Firewall Rules**:
```bash
# wf001 (USA) - Permitir apenas wf008
sudo ufw allow from <IP_wf008> to any port 5000 proto tcp

# wf008 (Brasil) - Permitir apenas wf001
sudo ufw allow from <IP_wf001> to any port 9101 proto tcp
```

#### 6.8.3 Performance e Escalabilidade

**Limites de Performance**:
- Ping interval: 30s (não sobrecarregar)
- Database probe interval: 60s
- Timeout de requisição: 10s
- Connection pool: 5 conexões por DB
- Retry attempts: 3 com exponential backoff

**Otimizações**:
- Usar async I/O (asyncio, aiohttp)
- Connection pooling para bancos
- Circuit breaker pattern
- Caching de resultados (5s TTL)
- Compressão HTTP (gzip)

**Escalabilidade Futura**:
- Adicionar mais localizações (Europa, Ásia)
- Múltiplos endpoints de teste
- Suporte a IPv6
- Integração com external monitoring (Pingdom, UptimeRobot)

#### 6.8.4 Fallback e Resiliência

**Circuit Breaker**:
- Após 5 falhas consecutivas, pausar por 60s
- Retry gradual: 10s, 30s, 60s
- Log de todas as falhas

**Fallback Strategy**:
- Se API não responder, continuar coletando métricas locais
- Buffer de até 100 requisições falhadas
- Replay quando conectividade restaurada

**Health Checks**:
- Ping Service: `GET /health` → 200 OK
- Collector API: `GET /health` → JSON com status de DB
- Métricas de health exportadas

#### 6.8.5 Monitoramento do Monitoramento

**Meta-Métricas**:
```prometheus
# Ping Service Health
ping_service_up{location="sao_paulo"} 1
ping_service_last_success_timestamp 1707046845

# Collector API Health
collector_api_up{location="virginia"} 1
collector_api_last_request_timestamp 1707046845

# Database Probe Health
database_probe_up{database_type="postgresql"} 1
database_probe_last_check_timestamp 1707046845
```

**Alertas de Monitoramento**:
```yaml
alert: PingServiceDown
expr: ping_service_up == 0
for: 2m
labels:
  severity: critical
annotations:
  summary: "Ping service is down"
  description: "No metrics received from ping service for 2 minutes"
```

### 6.9 Plano de Implementação

#### Fase 1: Preparação (Semana 1)
- [ ] **Dia 1-2**: Design detalhado da API e schemas
- [ ] **Dia 3**: Setup de ambiente de desenvolvimento
- [ ] **Dia 4**: Configurar NTP em ambos servidores
- [ ] **Dia 5**: Criar estrutura de diretórios e configs

#### Fase 2: Desenvolvimento (Semana 2-3)
- [ ] **Semana 2, Dia 1-3**: Desenvolver Ping Service (wf008)
  - Cliente HTTP async
  - Scheduler e retry logic
  - Prometheus metrics exporter
  - Dockerfile e docker-compose
- [ ] **Semana 2, Dia 4-5**: Testes unitários Ping Service
- [ ] **Semana 3, Dia 1-3**: Expandir Collector API (wf001)
  - Endpoint /api/ping
  - Database probe service
  - Metrics exporter
  - Authentication e rate limiting
- [ ] **Semana 3, Dia 4-5**: Testes unitários Collector API

#### Fase 3: Integração (Semana 4)
- [ ] **Dia 1**: Deploy Ping Service em wf008 (staging)
- [ ] **Dia 2**: Deploy Collector API em wf001 (staging)
- [ ] **Dia 3**: Testes de integração ponta-a-ponta
- [ ] **Dia 4**: Validar métricas no VictoriaMetrics
- [ ] **Dia 5**: Ajustes e correções

#### Fase 4: Dashboards (Semana 5)
- [ ] **Dia 1-2**: Criar painéis no Grafana
  - Network Latency (2 painéis)
  - Database Latency (2 painéis)
  - API Performance (1 painel)
  - Combined Health (1 painel)
- [ ] **Dia 3**: Integrar ao N8N Overview dashboard
- [ ] **Dia 4**: Configurar alertas (5 alertas)
- [ ] **Dia 5**: Testar notificações

#### Fase 5: Produção (Semana 6)
- [ ] **Dia 1**: Deploy em produção (wf008 e wf001)
- [ ] **Dia 2**: Monitoramento intensivo (24h)
- [ ] **Dia 3**: Ajuste de thresholds baseado em baseline
- [ ] **Dia 4**: Documentação final
- [ ] **Dia 5**: Treinamento da equipe

### 6.10 Checklist de Validação

**Infraestrutura**:
- [ ] NTP configurado e sincronizado (<10ms offset)
- [ ] Firewall rules configuradas
- [ ] Portas 5000 e 9101 acessíveis
- [ ] TLS/SSL configurado corretamente
- [ ] Certificados válidos

**Ping Service (wf008)**:
- [ ] Container rodando e saudável
- [ ] Requisições sendo enviadas a cada 30s
- [ ] Métricas exportadas na porta 9101
- [ ] Logs estruturados sendo gerados
- [ ] Health check respondendo

**Collector API (wf001)**:
- [ ] API respondendo em /api/ping
- [ ] Authentication funcionando
- [ ] Rate limiting ativo
- [ ] Database probes executando
- [ ] Métricas sendo geradas

**VictoriaMetrics**:
- [ ] Métricas de rede sendo coletadas
- [ ] Métricas de DB sendo coletadas
- [ ] Métricas de API sendo coletadas
- [ ] Retenção configurada (90 dias)
- [ ] Queries respondendo corretamente

**Grafana Dashboard**:
- [ ] 6 painéis criados e funcionais
- [ ] Queries retornando dados
- [ ] Thresholds configurados
- [ ] Cores e legendas corretas
- [ ] Links entre dashboards

**Alertas**:
- [ ] 5 alertas configurados
- [ ] Thresholds ajustados
- [ ] Notificações testadas
- [ ] Runbook documentado
- [ ] Escalação definida

**Documentação**:
- [ ] README atualizado
- [ ] Arquitetura documentada
- [ ] APIs documentadas (OpenAPI/Swagger)
- [ ] Runbook de troubleshooting
- [ ] FAQ atualizado

### 6.11 Métricas de Sucesso

**KPIs do Projeto**:
- ✅ Latência de rede < 250ms (P95)
- ✅ Availability > 99.5%
- ✅ Database query latency < 20ms (P95)
- ✅ API response time < 10ms (P95)
- ✅ Zero downtime durante deploy
- ✅ < 0.1% error rate

**Baseline Esperado** (após 30 dias):
```
Network Latency Brasil → USA:
- P50: 145ms
- P95: 220ms
- P99: 280ms

Database Query Latency:
- PostgreSQL P50: 3ms
- PostgreSQL P95: 12ms
- MySQL P50: 2.5ms
- MySQL P95: 10ms

API Collector:
- P50: 2ms
- P95: 8ms
- P99: 15ms
```

### 6.12 Desenvolvimento e Homologação Local

**Estratégia**: Desenvolver e testar tudo localmente antes de deploy em produção

#### 6.12.1 Ambiente de Desenvolvimento Local

**Pré-requisitos**:
```bash
# Ferramentas necessárias
- Docker Desktop (ou Docker Engine + Docker Compose)
- Python 3.12+
- Git
- VS Code (recomendado)
- curl / httpie (testes de API)
- psql / mysql client (testes de DB)
```

**Estrutura de Diretórios Local**:
```
~/dev/n8n-prometheus-wfdb01/
├── docker-compose.yml              # Stack completa local
├── .env                            # Variáveis de ambiente
├── .env.example                    # Template de configuração
│
├── ping-service/                   # Serviço de ping (simula wf008)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.yaml
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── ping_client.py
│   │   ├── scheduler.py
│   │   └── metrics.py
│   └── tests/
│       ├── test_ping_client.py
│       └── test_metrics.py
│
├── collector-api/                  # API collector expandido (simula wf001)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.yaml
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── ping_endpoint.py
│   │   │   └── auth.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── postgres_probe.py
│   │   │   └── mysql_probe.py
│   │   ├── metrics/
│   │   │   ├── __init__.py
│   │   │   └── exporter.py
│   │   └── n8n/
│   │       ├── __init__.py
│   │       └── collector.py
│   └── tests/
│       ├── test_api.py
│       ├── test_database_probe.py
│       └── test_metrics.py
│
├── infrastructure/                 # Stack de infraestrutura
│   ├── victoria-metrics/
│   ├── grafana/
│   │   ├── dashboards/
│   │   │   ├── n8n-overview.json
│   │   │   ├── network-latency.json
│   │   │   └── database-performance.json
│   │   └── provisioning/
│   │       ├── datasources/
│   │       │   └── victoria-metrics.yml
│   │       └── dashboards/
│   │           └── dashboards.yml
│   └── databases/
│       ├── postgres/
│       │   └── init.sql
│       └── mysql/
│           └── init.sql
│
├── scripts/                        # Scripts auxiliares
│   ├── setup_local_env.sh
│   ├── run_tests.sh
│   ├── simulate_load.py
│   └── validate_metrics.py
│
├── docs/                           # Documentação local
│   ├── DEVELOPMENT.md
│   ├── API.md
│   └── TESTING.md
│
└── logs/                           # Logs locais
    ├── ping-service/
    ├── collector-api/
    └── infrastructure/
```

#### 6.12.2 Docker Compose Local Completo

**Arquivo: docker-compose.yml**

```yaml
version: '3.8'

# Redes para simular separação geográfica
networks:
  brazil-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/24
  usa-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/24
  monitoring-net:
    driver: bridge

services:
  # ============================================
  # Infraestrutura de Bancos de Dados (USA)
  # ============================================

  postgres:
    image: postgres:15-alpine
    container_name: dev-postgres
    networks:
      - usa-net
    environment:
      POSTGRES_PASSWORD: devpass123
      POSTGRES_USER: n8n
      POSTGRES_DB: n8n
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./infrastructure/databases/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U n8n"]
      interval: 10s
      timeout: 5s
      retries: 5

  mysql:
    image: mysql:8.0
    container_name: dev-mysql
    networks:
      - usa-net
    environment:
      MYSQL_ROOT_PASSWORD: devpass123
      MYSQL_DATABASE: n8n
      MYSQL_USER: n8n
      MYSQL_PASSWORD: devpass123
    ports:
      - "3306:3306"
    volumes:
      - mysql-data:/var/lib/mysql
      - ./infrastructure/databases/mysql/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============================================
  # Mock N8N Server (USA)
  # ============================================

  n8n-mock:
    image: n8nio/n8n:latest
    container_name: dev-n8n
    networks:
      - usa-net
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=admin
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=devpass123
      - N8N_METRICS=true
    ports:
      - "5678:5678"
    volumes:
      - n8n-data:/home/node/.n8n
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:5678/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ============================================
  # VictoriaMetrics (Monitoring)
  # ============================================

  victoria-metrics:
    image: victoriametrics/victoria-metrics:latest
    container_name: dev-victoria-metrics
    networks:
      - monitoring-net
      - usa-net
      - brazil-net
    command:
      - '--storageDataPath=/victoria-metrics-data'
      - '--retentionPeriod=90d'
      - '--httpListenAddr=:8428'
    ports:
      - "8428:8428"
    volumes:
      - victoria-data:/victoria-metrics-data
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:8428/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ============================================
  # Grafana (Monitoring)
  # ============================================

  grafana:
    image: grafana/grafana:latest
    container_name: dev-grafana
    networks:
      - monitoring-net
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_INSTALL_PLUGINS=grafana-clock-panel
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./infrastructure/grafana/provisioning:/etc/grafana/provisioning
      - ./infrastructure/grafana/dashboards:/var/lib/grafana/dashboards
    depends_on:
      - victoria-metrics
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:3000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ============================================
  # Collector API (USA Network)
  # ============================================

  collector-api:
    build:
      context: ./collector-api
      dockerfile: Dockerfile
    container_name: dev-collector-api
    networks:
      - usa-net
      - monitoring-net
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=5000
      - API_KEY=${COLLECTOR_API_KEY:-dev-secret-key-12345}
      - N8N_URL=http://n8n-mock:5678
      - N8N_API_KEY=${N8N_API_KEY:-}
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_USER=n8n
      - POSTGRES_PASSWORD=devpass123
      - POSTGRES_DB=n8n
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_USER=n8n
      - MYSQL_PASSWORD=devpass123
      - MYSQL_DB=n8n
      - VICTORIA_METRICS_URL=http://victoria-metrics:8428
      - LOG_LEVEL=DEBUG
      - ENVIRONMENT=development
    ports:
      - "5000:5000"
      - "9102:9102"  # Prometheus metrics
    volumes:
      - ./collector-api:/app
      - ./logs/collector-api:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      mysql:
        condition: service_healthy
      n8n-mock:
        condition: service_healthy
      victoria-metrics:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  # ============================================
  # Ping Service (Brazil Network)
  # ============================================

  ping-service:
    build:
      context: ./ping-service
      dockerfile: Dockerfile
    container_name: dev-ping-service
    networks:
      - brazil-net
      - monitoring-net
    environment:
      - TARGET_URL=http://collector-api:5000/api/ping
      - API_KEY=${COLLECTOR_API_KEY:-dev-secret-key-12345}
      - PING_INTERVAL=30
      - SOURCE_LOCATION=local_dev_brazil
      - SOURCE_DATACENTER=local
      - SOURCE_COUNTRY=BR
      - VICTORIA_METRICS_URL=http://victoria-metrics:8428
      - LOG_LEVEL=DEBUG
      - ENVIRONMENT=development
    ports:
      - "9101:9101"  # Prometheus metrics
    volumes:
      - ./ping-service:/app
      - ./logs/ping-service:/app/logs
    depends_on:
      collector-api:
        condition: service_healthy
      victoria-metrics:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9101/metrics"]
      interval: 60s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  # ============================================
  # Node Exporter (Opcional - para testes)
  # ============================================

  node-exporter:
    image: prom/node-exporter:latest
    container_name: dev-node-exporter
    networks:
      - monitoring-net
    command:
      - '--path.rootfs=/host'
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    restart: unless-stopped

  # ============================================
  # cAdvisor (Opcional - para testes)
  # ============================================

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: dev-cadvisor
    networks:
      - monitoring-net
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    privileged: true
    devices:
      - /dev/kmsg
    restart: unless-stopped

volumes:
  postgres-data:
  mysql-data:
  n8n-data:
  victoria-data:
  grafana-data:
```

**Arquivo: .env.example**
```bash
# Copiar para .env e ajustar valores

# API Keys
COLLECTOR_API_KEY=dev-secret-key-12345
N8N_API_KEY=

# Database (já configurado no compose, mas pode sobrescrever)
POSTGRES_PASSWORD=devpass123
MYSQL_ROOT_PASSWORD=devpass123

# Monitoring
GRAFANA_ADMIN_PASSWORD=admin

# Development
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

#### 6.12.3 Setup Inicial do Ambiente Local

**Script: scripts/setup_local_env.sh**

```bash
#!/bin/bash

set -e

echo "🚀 Configurando ambiente de desenvolvimento local..."

# Verificar pré-requisitos
command -v docker >/dev/null 2>&1 || { echo "❌ Docker não instalado"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose não instalado"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 não instalado"; exit 1; }

echo "✅ Pré-requisitos OK"

# Criar estrutura de diretórios
echo "📁 Criando estrutura de diretórios..."
mkdir -p ping-service/src/tests
mkdir -p collector-api/src/{api,database,metrics,n8n}/tests
mkdir -p infrastructure/{grafana/{dashboards,provisioning/{datasources,dashboards}},victoria-metrics,databases/{postgres,mysql}}
mkdir -p scripts
mkdir -p logs/{ping-service,collector-api,infrastructure}
mkdir -p docs

# Copiar .env.example para .env
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env..."
    cp .env.example .env
    echo "⚠️  Edite o arquivo .env com suas configurações"
fi

# Criar requirements.txt para ping-service
echo "📦 Criando requirements.txt para ping-service..."
cat > ping-service/requirements.txt << 'EOF'
httpx==0.27.0
APScheduler==3.10.4
prometheus-client==0.20.0
python-dotenv==1.0.1
pydantic==2.6.1
pydantic-settings==2.2.0
PyYAML==6.0.1
structlog==24.1.0
uvloop==0.19.0
EOF

# Criar requirements.txt para collector-api
echo "📦 Criando requirements.txt para collector-api..."
cat > collector-api/requirements.txt << 'EOF'
fastapi==0.109.2
uvicorn[standard]==0.27.1
httpx==0.27.0
psycopg[binary]==3.1.18
aiomysql==0.2.0
prometheus-client==0.20.0
python-dotenv==1.0.1
pydantic==2.6.1
pydantic-settings==2.2.0
PyYAML==6.0.1
structlog==24.1.0
python-multipart==0.0.9
slowapi==0.1.9
cryptography==42.0.2
EOF

# Criar Dockerfile básico para ping-service
echo "🐳 Criando Dockerfile para ping-service..."
cat > ping-service/Dockerfile << 'EOF'
FROM python:3.12-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte
COPY . .

# Expor porta de métricas
EXPOSE 9101

# Health check
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:9101/metrics || exit 1

# Comando de inicialização
CMD ["python", "-u", "src/main.py"]
EOF

# Criar Dockerfile básico para collector-api
echo "🐳 Criando Dockerfile para collector-api..."
cat > collector-api/Dockerfile << 'EOF'
FROM python:3.12-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte
COPY . .

# Expor portas (API e Metrics)
EXPOSE 5000 9102

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Comando de inicialização
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]
EOF

# Criar init.sql básico para PostgreSQL
echo "🗄️  Criando init.sql para PostgreSQL..."
cat > infrastructure/databases/postgres/init.sql << 'EOF'
-- Criar tabela de teste para health checks
CREATE TABLE IF NOT EXISTS health_check (
    id SERIAL PRIMARY KEY,
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir registro de teste
INSERT INTO health_check (check_time) VALUES (CURRENT_TIMESTAMP);

-- Criar usuário read-only para probes
CREATE USER IF NOT EXISTS probe_user WITH PASSWORD 'probe_pass_123';
GRANT CONNECT ON DATABASE n8n TO probe_user;
GRANT SELECT ON health_check TO probe_user;
EOF

# Criar init.sql básico para MySQL
echo "🗄️  Criando init.sql para MySQL..."
cat > infrastructure/databases/mysql/init.sql << 'EOF'
-- Criar tabela de teste para health checks
CREATE TABLE IF NOT EXISTS health_check (
    id INT AUTO_INCREMENT PRIMARY KEY,
    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir registro de teste
INSERT INTO health_check (check_time) VALUES (CURRENT_TIMESTAMP());

-- Criar usuário read-only para probes
CREATE USER IF NOT EXISTS 'probe_user'@'%' IDENTIFIED BY 'probe_pass_123';
GRANT SELECT ON n8n.health_check TO 'probe_user'@'%';
FLUSH PRIVILEGES;
EOF

# Criar arquivo de configuração do Grafana datasource
echo "📊 Criando configuração de datasource do Grafana..."
mkdir -p infrastructure/grafana/provisioning/datasources
cat > infrastructure/grafana/provisioning/datasources/victoria-metrics.yml << 'EOF'
apiVersion: 1

datasources:
  - name: VictoriaMetrics
    type: prometheus
    access: proxy
    url: http://victoria-metrics:8428
    isDefault: true
    editable: false
    jsonData:
      httpMethod: POST
      timeInterval: 30s
EOF

# Criar arquivo de configuração de dashboards do Grafana
echo "📊 Criando configuração de dashboards do Grafana..."
mkdir -p infrastructure/grafana/provisioning/dashboards
cat > infrastructure/grafana/provisioning/dashboards/dashboards.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'Default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    allowUiUpdates: true
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
EOF

echo ""
echo "✅ Setup completo!"
echo ""
echo "📋 Próximos passos:"
echo "1. Edite o arquivo .env com suas configurações"
echo "2. Execute: docker-compose up -d"
echo "3. Aguarde todos os serviços iniciarem (2-3 minutos)"
echo "4. Acesse o Grafana: http://localhost:3000 (admin/admin)"
echo "5. Acesse o N8N: http://localhost:5678 (admin/admin)"
echo "6. Verifique métricas: http://localhost:8428"
echo ""
echo "🔍 Comandos úteis:"
echo "  - Ver logs: docker-compose logs -f [service-name]"
echo "  - Restart: docker-compose restart [service-name]"
echo "  - Stop tudo: docker-compose down"
echo "  - Stop e limpar volumes: docker-compose down -v"
echo ""
```

**Tornar executável**:
```bash
chmod +x scripts/setup_local_env.sh
```

#### 6.12.4 Workflow de Desenvolvimento Local

**Passo 1: Setup Inicial**
```bash
# Clonar/criar estrutura
cd ~/dev
mkdir n8n-prometheus-wfdb01
cd n8n-prometheus-wfdb01

# Executar setup
bash scripts/setup_local_env.sh

# Ajustar .env se necessário
vim .env
```

**Passo 2: Iniciar Stack**
```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs em tempo real
docker-compose logs -f

# Verificar status
docker-compose ps
```

**Passo 3: Verificar Serviços**
```bash
# Health checks
curl http://localhost:5000/health          # Collector API
curl http://localhost:9101/metrics         # Ping Service metrics
curl http://localhost:8428/health          # VictoriaMetrics
curl http://localhost:3000/api/health      # Grafana

# Testar ping manualmente
curl -X POST http://localhost:5000/api/ping \
  -H "X-API-Key: dev-secret-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp_start": "'$(date -u +"%Y-%m-%dT%H:%M:%S.%6NZ")'",
    "source": {
      "location": "local_test",
      "datacenter": "local",
      "country": "BR"
    },
    "ping_id": "test-'$(uuidgen)'"
  }'
```

**Passo 4: Desenvolvimento Iterativo**
```bash
# Editar código (exemplo: collector-api)
vim collector-api/src/api/ping_endpoint.py

# Restart apenas o serviço alterado (auto-reload se configurado)
docker-compose restart collector-api

# Ver logs do serviço
docker-compose logs -f collector-api

# Executar testes
docker-compose exec collector-api pytest tests/ -v
```

**Passo 5: Validar Métricas**
```bash
# Verificar métricas no VictoriaMetrics
curl -s 'http://localhost:8428/api/v1/query?query=network_latency_rtt_seconds' | jq .

# Verificar métricas de database
curl -s 'http://localhost:8428/api/v1/query?query=database_query_latency_seconds' | jq .

# Listar todas as métricas disponíveis
curl -s 'http://localhost:8428/api/v1/label/__name__/values' | jq .
```

#### 6.12.5 Testes e Validação Local

**Script: scripts/run_tests.sh**

```bash
#!/bin/bash

set -e

echo "🧪 Executando testes..."

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Contador de testes
PASSED=0
FAILED=0

# Função para testar endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected=$3

    echo -n "Testing $name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")

    if [ "$response" -eq "$expected" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $response)"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $response, expected $expected)"
        ((FAILED++))
    fi
}

# Função para testar métrica
test_metric() {
    local name=$1
    local query=$2

    echo -n "Testing metric $name... "
    result=$(curl -s "http://localhost:8428/api/v1/query?query=$query" | jq -r '.status')

    if [ "$result" == "success" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED++))
    fi
}

echo "==================================="
echo "1. Testando Health Checks"
echo "==================================="
test_endpoint "Grafana Health" "http://localhost:3000/api/health" 200
test_endpoint "VictoriaMetrics Health" "http://localhost:8428/health" 200
test_endpoint "Collector API Health" "http://localhost:5000/health" 200
test_endpoint "N8N Health" "http://localhost:5678/healthz" 200

echo ""
echo "==================================="
echo "2. Testando Métricas Prometheus"
echo "==================================="
test_endpoint "Ping Service Metrics" "http://localhost:9101/metrics" 200
test_endpoint "Collector API Metrics" "http://localhost:9102/metrics" 200
test_endpoint "Node Exporter Metrics" "http://localhost:9100/metrics" 200

echo ""
echo "==================================="
echo "3. Testando VictoriaMetrics Queries"
echo "==================================="
test_metric "Network RTT" "network_latency_rtt_seconds"
test_metric "Database Latency" "database_query_latency_seconds"
test_metric "API Duration" "api_request_duration_seconds"

echo ""
echo "==================================="
echo "4. Testando API Collector"
echo "==================================="

# Teste de ping com timestamp
echo -n "Testing /api/ping endpoint... "
ping_response=$(curl -s -X POST http://localhost:5000/api/ping \
  -H "X-API-Key: dev-secret-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp_start": "'$(date -u +"%Y-%m-%dT%H:%M:%S.%6NZ")'",
    "source": {
      "location": "test",
      "datacenter": "local",
      "country": "BR"
    },
    "ping_id": "test-'$(date +%s)'"
  }')

if echo "$ping_response" | jq -e '.status == "success"' > /dev/null; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
    echo "  Response: $(echo $ping_response | jq -c '.')"
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
    echo "  Response: $ping_response"
fi

echo ""
echo "==================================="
echo "5. Testando Database Connectivity"
echo "==================================="

# PostgreSQL
echo -n "Testing PostgreSQL... "
if docker-compose exec -T postgres psql -U n8n -d n8n -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

# MySQL
echo -n "Testing MySQL... "
if docker-compose exec -T mysql mysql -u n8n -pdevpass123 n8n -e "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((FAILED++))
fi

echo ""
echo "==================================="
echo "RESULTADO DOS TESTES"
echo "==================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Total: $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Todos os testes passaram!${NC}"
    exit 0
else
    echo -e "${RED}✗ Alguns testes falharam${NC}"
    exit 1
fi
```

**Tornar executável e executar**:
```bash
chmod +x scripts/run_tests.sh
./scripts/run_tests.sh
```

#### 6.12.6 Simulação de Carga

**Script: scripts/simulate_load.py**

```python
#!/usr/bin/env python3
"""
Simula carga no sistema para testar performance e métricas
"""
import asyncio
import httpx
import time
from datetime import datetime
import uuid

API_URL = "http://localhost:5000/api/ping"
API_KEY = "dev-secret-key-12345"
REQUESTS_PER_SECOND = 1  # Ajustar conforme necessário
DURATION_SECONDS = 300  # 5 minutos

async def send_ping():
    async with httpx.AsyncClient(timeout=10.0) as client:
        payload = {
            "timestamp_start": datetime.utcnow().isoformat() + "Z",
            "source": {
                "location": "load_test",
                "datacenter": "local",
                "country": "BR"
            },
            "ping_id": str(uuid.uuid4())
        }

        try:
            response = await client.post(
                API_URL,
                json=payload,
                headers={"X-API-Key": API_KEY}
            )
            return response.status_code, response.json()
        except Exception as e:
            return 0, {"error": str(e)}

async def main():
    print(f"🚀 Iniciando teste de carga...")
    print(f"   URL: {API_URL}")
    print(f"   Rate: {REQUESTS_PER_SECOND} req/s")
    print(f"   Duration: {DURATION_SECONDS}s")
    print()

    start_time = time.time()
    requests_sent = 0
    requests_success = 0
    requests_failed = 0

    while time.time() - start_time < DURATION_SECONDS:
        tasks = []
        for _ in range(REQUESTS_PER_SECOND):
            tasks.append(send_ping())

        results = await asyncio.gather(*tasks)

        for status, response in results:
            requests_sent += 1
            if status == 200:
                requests_success += 1
            else:
                requests_failed += 1
                print(f"❌ Error: {status} - {response}")

        # Imprimir progresso a cada 10 requisições
        if requests_sent % 10 == 0:
            elapsed = time.time() - start_time
            print(f"📊 {requests_sent} requests | "
                  f"✓ {requests_success} | "
                  f"✗ {requests_failed} | "
                  f"⏱️  {elapsed:.1f}s")

        await asyncio.sleep(1)

    # Resultado final
    elapsed = time.time() - start_time
    print()
    print("=" * 50)
    print(f"✅ Teste concluído!")
    print(f"   Total: {requests_sent}")
    print(f"   Success: {requests_success} ({requests_success/requests_sent*100:.1f}%)")
    print(f"   Failed: {requests_failed} ({requests_failed/requests_sent*100:.1f}%)")
    print(f"   Duration: {elapsed:.1f}s")
    print(f"   Avg rate: {requests_sent/elapsed:.2f} req/s")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
```

**Executar**:
```bash
chmod +x scripts/simulate_load.py
python3 scripts/simulate_load.py
```

#### 6.12.7 Checklist de Homologação Local

**Antes de Deploy em Produção, validar**:

- [ ] **Funcionalidades Básicas**:
  - [ ] Ping Service envia requisições a cada 30s
  - [ ] Collector API responde com latência < 50ms
  - [ ] Database probes executam queries com sucesso
  - [ ] Métricas são exportadas para VictoriaMetrics
  - [ ] Grafana exibe dados corretamente

- [ ] **Performance**:
  - [ ] API suporta 120 req/min (rate limit)
  - [ ] Latência P95 < 100ms (local)
  - [ ] Zero memory leaks após 1h de execução
  - [ ] CPU usage < 10% em idle
  - [ ] Logs não crescem indefinidamente

- [ ] **Resiliência**:
  - [ ] Retry logic funciona (simular falha de rede)
  - [ ] Circuit breaker ativa após 5 falhas
  - [ ] Recovery após queda de serviço
  - [ ] Graceful shutdown preserva dados
  - [ ] Health checks detectam falhas

- [ ] **Segurança**:
  - [ ] API Key authentication funciona
  - [ ] Rate limiting bloqueia excesso
  - [ ] Senhas não aparecem em logs
  - [ ] Conexões de DB usam credenciais corretas
  - [ ] HTTPS configurado (se aplicável)

- [ ] **Métricas e Alertas**:
  - [ ] Todas as 13 métricas são coletadas
  - [ ] Queries PromQL retornam dados
  - [ ] Dashboards carregam sem erros
  - [ ] Alertas disparam corretamente
  - [ ] Notificações são recebidas

- [ ] **Documentação**:
  - [ ] README.md atualizado
  - [ ] API documentada (Swagger/OpenAPI)
  - [ ] Variáveis de ambiente documentadas
  - [ ] Troubleshooting guide criado
  - [ ] Runbook de deploy criado

- [ ] **Testes**:
  - [ ] Testes unitários passam (> 80% coverage)
  - [ ] Testes de integração passam
  - [ ] Teste de carga bem-sucedido (5min)
  - [ ] Testes de falha bem-sucedidos
  - [ ] All tests green ✅

#### 6.12.8 Migração para Produção

**Processo de Deploy**:

1. **Preparação** (Semana 1):
   ```bash
   # Tag de release
   git tag v1.0.0-homolog
   git push origin v1.0.0-homolog

   # Build de imagens para produção
   docker build -t vya/ping-service:v1.0.0 ./ping-service
   docker build -t vya/collector-api:v1.0.0 ./collector-api

   # Push para registry (Docker Hub ou privado)
   docker push vya/ping-service:v1.0.0
   docker push vya/collector-api:v1.0.0
   ```

2. **Deploy Staging (wf001 - Staging)** (Semana 2):
   ```bash
   # SSH para wf001
   ssh user@wf001.vya.digital

   # Criar estrutura
   sudo mkdir -p /opt/monitoring-staging
   cd /opt/monitoring-staging

   # Copiar docker-compose.yml e configs
   scp docker-compose.yml user@wf001:/opt/monitoring-staging/

   # Ajustar .env para staging
   vim .env

   # Deploy
   docker-compose up -d

   # Monitorar logs
   docker-compose logs -f
   ```

3. **Testes em Staging** (Semana 2-3):
   - Executar todos os testes de homologação
   - Monitorar por 48h
   - Validar métricas e alertas
   - Ajustar configurações se necessário

4. **Deploy Produção (wf001 + wf008)** (Semana 4):
   ```bash
   # wf001 (USA)
   ssh user@wf001.vya.digital
   sudo mkdir -p /opt/monitoring-prod
   cd /opt/monitoring-prod
   # ... repetir processo

   # wf008 (Brasil)
   ssh user@wf008.vya.digital
   sudo mkdir -p /opt/monitoring-prod
   cd /opt/monitoring-prod
   # ... deploy ping-service
   ```

5. **Validação Pós-Deploy** (Semana 4-5):
   - Executar checklist de validação
   - Monitorar intensivamente por 72h
   - Coletar feedback da equipe
   - Ajustar thresholds de alertas
   - Documentar issues e resoluções

6. **Rollback Plan** (se necessário):
   ```bash
   # Parar novos serviços
   docker-compose stop collector-api ping-service

   # Reverter para versão anterior
   docker-compose down
   git checkout v0.9.0
   docker-compose up -d

   # Validar sistema antigo funcionando
   ./scripts/run_tests.sh
   ```

#### 6.12.9 Monitoramento do Desenvolvimento

**Métricas de Progresso**:
```markdown
## Sprint 1 (Semanas 1-2): Desenvolvimento Local
- [ ] Setup ambiente completo
- [ ] Ping Service implementado
- [ ] Collector API implementado
- [ ] Database Probes implementados
- [ ] Testes unitários (>80% coverage)
- [ ] Documentação API (Swagger)

## Sprint 2 (Semanas 3-4): Integração e Testes
- [ ] Integração completa local
- [ ] Dashboards Grafana criados
- [ ] Alertas configurados
- [ ] Testes de carga bem-sucedidos
- [ ] Checklist de homologação 100%

## Sprint 3 (Semanas 5-6): Deploy Staging
- [ ] Deploy em ambiente staging
- [ ] Validação 48h
- [ ] Ajustes e correções
- [ ] Aprovação para produção

## Sprint 4 (Semanas 7-8): Deploy Produção
- [ ] Deploy wf001 (USA)
- [ ] Deploy wf008 (Brasil)
- [ ] Validação 72h
- [ ] Documentação final
- [ ] Treinamento equipe
```

**Daily Standup Checklist**:
- [ ] O que foi feito ontem?
- [ ] O que será feito hoje?
- [ ] Há algum bloqueador?
- [ ] Testes estão passando?
- [ ] Documentação está atualizada?

---

## 7. Ordem de Execução Detalhada (4 Semanas)

### 📅 Semana 1: Preparação e Backup

**Objetivos**:
- ✅ Backup completo dos dados atuais
- ✅ Preparar estrutura de diretórios
- ✅ Containerizar scripts de coleta

**Checklist Diário**:

**Segunda-feira** (Dia 1):
- [ ] Criar snapshot do VictoriaMetrics
- [ ] Documentar volume de dados coletados
- [ ] Validar integridade com SHA256
- [ ] Criar estrutura `/opt/monitoring/` no servidor destino

**Terça-feira** (Dia 2):
- [ ] Criar Dockerfile para collector Python
- [ ] Testar build do container localmente
- [ ] Criar health_check.sh script
- [ ] Atualizar docker-compose.yml

**Quarta-feira** (Dia 3):
- [ ] Deploy do container collector
- [ ] Validar coleta via container
- [ ] Comparar métricas (script vs container)
- [ ] Monitorar logs por 24h

**Quinta-feira** (Dia 4):
- [ ] Configurar volumes persistentes
- [ ] Testar backup e restore
- [ ] Documentar processo de migração
- [ ] Criar runbook de rollback

**Sexta-feira** (Dia 5):
- [ ] Revisar toda preparação
- [ ] Validar checklist completo
- [ ] Agendar instalação para Semana 2
- [ ] Comunicar equipe sobre mudanças

---

### 📅 Semana 2: Instalação de Node Exporter e cAdvisor

**Objetivos**:
- ✅ Instalar Node Exporter no wf005
- ✅ Instalar cAdvisor
- ✅ Configurar scraping no VictoriaMetrics
- ✅ Validar coleta de métricas

**Checklist Diário**:

**Segunda-feira** (Dia 1):
- [ ] **09:00** - Verificar pré-requisitos
  - [ ] Docker rodando normalmente
  - [ ] Espaço em disco disponível (>5GB)
  - [ ] Portas 9100 e 8080 livres
  - [ ] Backup recente confirmado

**Segunda-feira** (Dia 1) - Instalação Node Exporter:
- [ ] **10:00** - Adicionar serviço ao docker-compose.yml
- [ ] **10:15** - Deploy: `docker-compose up -d node-exporter`
- [ ] **10:20** - Validar logs: `docker logs node-exporter`
- [ ] **10:25** - Testar endpoint: `curl localhost:9100/metrics`
- [ ] **10:30** - Verificar recursos: `docker stats node-exporter`
- [ ] **11:00** - Monitorar por 1h (verificar estabilidade)
- [ ] **12:00** - Checkpoint: Tudo OK? Continuar ou rollback

**Terça-feira** (Dia 2) - Instalação cAdvisor:
- [ ] **10:00** - Adicionar cAdvisor ao docker-compose.yml
- [ ] **10:15** - Deploy: `docker-compose up -d cadvisor`
- [ ] **10:20** - Validar logs: `docker logs cadvisor`
- [ ] **10:25** - Testar endpoint: `curl localhost:8080/metrics`
- [ ] **10:30** - Acessar UI: `http://wf005:8080`
- [ ] **10:45** - Verificar métricas do N8N
- [ ] **11:00** - Monitorar por 2h

**Quarta-feira** (Dia 3) - Configurar Scraping:
- [ ] **09:00** - Criar prometheus-targets.yml
- [ ] **09:30** - Atualizar VictoriaMetrics config
- [ ] **09:45** - Restart VictoriaMetrics
- [ ] **10:00** - Validar targets: `curl localhost:8428/api/v1/targets`
- [ ] **10:15** - Query teste: node_cpu_seconds_total
- [ ] **10:30** - Query teste: container_cpu_usage_seconds_total
- [ ] **11:00** - Verificar volume de dados (crescimento)

**Quinta-feira** (Dia 4) - Validação Intensiva:
- [ ] Executar queries de todas as métricas importantes
- [ ] Verificar gaps nos dados (continuidade)
- [ ] Testar período de retenção
- [ ] Documentar qualquer issue encontrado
- [ ] Ajustar scrape_interval se necessário

**Sexta-feira** (Dia 5) - Estabilização:
- [ ] Revisar logs de toda a semana
- [ ] Confirmar 5 dias de coleta estável
- [ ] Documentar lições aprendidas
- [ ] Preparar para criação de dashboards

---

### 📅 Semana 3: Criação de Dashboards

**Objetivos**:
- ✅ Criar Dashboard "System Overview"
- ✅ Criar Dashboard "Docker Engine"
- ✅ Criar Dashboard "Container Performance"
- ✅ Integrar com dashboards N8N existentes

**Checklist Diário**:

**Segunda-feira** (Dia 1) - Dashboard System Overview:
- [ ] **09:00** - Criar arquivo system-overview.json
- [ ] **10:00** - Painel 1: CPU Usage by Core
- [ ] **10:30** - Painel 2: Memory Usage
- [ ] **11:00** - Painel 3: Disk Space Usage
- [ ] **11:30** - Painel 4: Network Traffic
- [ ] **14:00** - Painel 5: Load Average
- [ ] **14:30** - Painel 6: Disk I/O
- [ ] **15:00** - Testar todas as queries
- [ ] **15:30** - Ajustar visualizações e cores
- [ ] **16:00** - Deploy via provisioning
- [ ] **16:15** - Validar no Grafana

**Terça-feira** (Dia 2) - Dashboard Docker Engine:
- [ ] **09:00** - Criar arquivo docker-engine.json
- [ ] **10:00** - Painel 1: Container Status
- [ ] **10:30** - Painel 2: Total CPU Usage
- [ ] **11:00** - Painel 3: Total Memory Usage
- [ ] **11:30** - Painel 4: Network Traffic
- [ ] **14:00** - Testar agregações (sum)
- [ ] **15:00** - Deploy e validar

**Quarta-feira** (Dia 3) - Dashboard Container Performance:
- [ ] **09:00** - Criar arquivo container-performance.json
- [ ] **09:30** - Painel 1: CPU by Container (Tabela)
- [ ] **10:00** - Painel 2: Memory by Container (Tabela)
- [ ] **10:30** - Painel 3: N8N CPU (Gráfico)
- [ ] **11:00** - Painel 4: N8N Memory (Gráfico)
- [ ] **11:30** - Painel 5: Container Restarts
- [ ] **14:00** - Painel 6: Network I/O by Container
- [ ] **15:00** - Testar filtros e sorting
- [ ] **16:00** - Deploy e validar

**Quinta-feira** (Dia 4) - Integração e Refinamento:
- [ ] Criar links entre dashboards
- [ ] Adicionar variáveis de template (container, timerange)
- [ ] Padronizar cores e temas
- [ ] Testar em diferentes resoluções
- [ ] Adicionar anotações e descrições

**Sexta-feira** (Dia 5) - Review e Ajustes:
- [ ] Apresentar dashboards para equipe
- [ ] Coletar feedback
- [ ] Implementar ajustes sugeridos
- [ ] Documentar uso dos dashboards
- [ ] Criar screenshots para documentação

---

### 📅 Semana 4: Alertas e Documentação Final

**Objetivos**:
- ✅ Configurar todos os alertas
- ✅ Testar notification channels
- ✅ Documentação completa
- ✅ Treinamento da equipe

**Checklist Diário**:

**Segunda-feira** (Dia 1) - Alertas de Servidor:
- [ ] **09:00** - Configurar alerta: HostHighCpuLoad
- [ ] **09:30** - Configurar alerta: HostOutOfMemory
- [ ] **10:00** - Configurar alerta: HostDiskSpaceFillingUp
- [ ] **10:30** - Configurar alerta: HostHighLoad
- [ ] **11:00** - Testar cada alerta (simular condição)
- [ ] **14:00** - Ajustar thresholds baseado em baseline

**Terça-feira** (Dia 2) - Alertas de Containers:
- [ ] **09:00** - Configurar alerta: ContainerHighCpu
- [ ] **09:30** - Configurar alerta: ContainerMemoryUsage
- [ ] **10:00** - Configurar alerta: ContainerRestarting
- [ ] **11:00** - Testar alertas
- [ ] **14:00** - Configurar notification channels (Slack/Email)
- [ ] **15:00** - Validar recebimento de notificações

**Quarta-feira** (Dia 3) - Documentação:
- [ ] **09:00** - Atualizar README.md do projeto
- [ ] **10:00** - Criar runbook de troubleshooting
- [ ] **11:00** - Documentar processo de backup/restore
- [ ] **14:00** - Criar guia de uso dos dashboards
- [ ] **15:00** - Documentar interpretação de alertas
- [ ] **16:00** - Criar FAQ (perguntas frequentes)

**Quinta-feira** (Dia 4) - Treinamento:
- [ ] **10:00** - Sessão de treinamento com equipe (2h)
  - [ ] Apresentar dashboards
  - [ ] Explicar métricas principais
  - [ ] Demonstrar como investigar alertas
  - [ ] Q&A
- [ ] **14:00** - Exercício prático: Investigar problema simulado
- [ ] **16:00** - Revisar dúvidas e ajustes

**Sexta-feira** (Dia 5) - Finalização:
- [ ] **09:00** - Review completo de toda implementação
- [ ] **10:00** - Validar checklist de todas as 4 semanas
- [ ] **11:00** - Testar cenários de falha e recovery
- [ ] **14:00** - Criar relatório final de implementação
- [ ] **15:00** - Apresentação executiva para stakeholders
- [ ] **16:00** - Celebrar conclusão! 🎉

---

## 7. Validação e Testes

### 7.1 Checklist de Validação Final

**Infraestrutura**:
- [ ] Node Exporter rodando e coletando métricas
- [ ] cAdvisor rodando e coletando métricas
- [ ] VictoriaMetrics scraping todos os targets
- [ ] Grafana exibindo dados de todas as fontes
- [ ] Volumes persistentes configurados corretamente
- [ ] Backups automáticos funcionando

**Dashboards**:
- [ ] System Overview funcional (6 painéis)
- [ ] Docker Engine funcional (4 painéis)
- [ ] Container Performance funcional (6 painéis)
- [ ] N8N Performance Overview (existente, atualizado)
- [ ] N8N Performance Detailed (existente, atualizado)
- [ ] N8N Node Performance (existente, atualizado)
- [ ] Links entre dashboards funcionando
- [ ] Variáveis de template operacionais

**Alertas**:
- [ ] 4 alertas de servidor configurados
- [ ] 3 alertas de container configurados
- [ ] Notification channels testados
- [ ] Thresholds ajustados baseado em baseline
- [ ] Silencing rules configurados (manutenção)

**Documentação**:
- [ ] README.md atualizado
- [ ] Runbook de troubleshooting criado
- [ ] Guia de dashboards criado
- [ ] FAQ documentado
- [ ] Processo de backup documentado
- [ ] Lições aprendidas documentadas

**Treinamento**:
- [ ] Equipe treinada no uso dos dashboards
- [ ] Equipe sabe interpretar alertas
- [ ] Equipe sabe como investigar problemas
- [ ] Contatos de escalação definidos

### 7.2 Testes de Carga e Stress

**Teste 1: Simular Alta CPU**:
```bash
# Executar stress test
docker run --rm --name stress-cpu \
  -it progrium/stress \
  --cpu 2 --timeout 60s

# Validar:
# - Dashboard mostra aumento de CPU
# - Alerta é disparado após 5min
# - Notificação é recebida
```

**Teste 2: Simular Alta Memória**:
```bash
# Consumir memória
docker run --rm --name stress-mem \
  -it progrium/stress \
  --vm 1 --vm-bytes 1G --timeout 120s

# Validar alertas e dashboards
```

**Teste 3: Simular Container Restart**:
```bash
# Restart forçado
docker restart n8n_n8n

# Validar:
# - Alerta de restart disparado
# - Dashboard mostra interrupção
# - Recovery detectado
```

---

## 8. Manutenção e Evolução

### 8.1 Manutenção Regular

**Diária**:
- [ ] Verificar alertas disparados (5 min)
- [ ] Review rápido dos dashboards (10 min)

**Semanal**:
- [ ] Análise de tendências (30 min)
- [ ] Review de alertas falsos positivos (20 min)
- [ ] Verificar espaço em disco VictoriaMetrics (5 min)
- [ ] Atualizar documentação se necessário (15 min)

**Mensal**:
- [ ] Backup completo e teste de restore (1h)
- [ ] Review de thresholds de alertas (30 min)
- [ ] Atualização de containers (Node Exporter, cAdvisor) (1h)
- [ ] Limpeza de dados antigos (30 min)
- [ ] Relatório mensal de performance (2h)

### 8.2 Roadmap Futuro

**Próximos 3 Meses**:
- [ ] Expandir monitoramento para wf001, wf002, wf006
- [ ] Implementar dashboards comparativos entre servidores
- [ ] Adicionar métricas de aplicação (custom metrics)
- [ ] Implementar distributed tracing (Jaeger/Tempo)
- [ ] Criar dashboard de custos (recursos vs billing)

**Próximos 6 Meses**:
- [ ] Migrar para Prometheus + Thanos (long-term storage)
- [ ] Implementar anomaly detection (Machine Learning)
- [ ] Criar dashboards preditivos (capacity planning)
- [ ] Integrar com CI/CD para deployment metrics
- [ ] Implementar SLO/SLI tracking

---

## 9. Referências e Recursos

### 9.1 Documentação Oficial

**Node Exporter**:
- GitHub: https://github.com/prometheus/node_exporter
- Collectors: https://github.com/prometheus/node_exporter#enabled-by-default
- Best Practices: https://prometheus.io/docs/practices/naming/

**cAdvisor**:
- GitHub: https://github.com/google/cadvisor
- Metrics: https://github.com/google/cadvisor/blob/master/docs/storage/prometheus.md
- Runtime Options: https://github.com/google/cadvisor/blob/master/docs/runtime_options.md

**Grafana**:
- Provisioning: https://grafana.com/docs/grafana/latest/administration/provisioning/
- Alerting: https://grafana.com/docs/grafana/latest/alerting/
- Dashboard API: https://grafana.com/docs/grafana/latest/http_api/dashboard/

**VictoriaMetrics**:
- Docs: https://docs.victoriametrics.com/
- PromQL: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Best Practices: https://docs.victoriametrics.com/guides/k8s-monitoring-via-vm-cluster.html

### 9.2 Dashboards Pré-Prontos

**Node Exporter Full**:
- Grafana ID: 1860
- URL: https://grafana.com/grafana/dashboards/1860

**Docker Container & Host Metrics**:
- Grafana ID: 193
- URL: https://grafana.com/grafana/dashboards/193

**cAdvisor Exporter**:
- Grafana ID: 14282
- URL: https://grafana.com/grafana/dashboards/14282

### 9.3 Comunidade e Suporte

- Grafana Community: https://community.grafana.com/
- Prometheus Users: https://groups.google.com/g/prometheus-users
- VictoriaMetrics Slack: https://slack.victoriametrics.com/

---

**Documento Criado**: 04/02/2026
**Última Revisão**: 04/02/2026
**Próxima Revisão**: Após conclusão da Semana 4
**Responsável**: DevOps Team
