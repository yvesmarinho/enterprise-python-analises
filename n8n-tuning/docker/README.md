# 🐳 N8N Monitoring Stack

**Victoria Metrics + Grafana para Análise de Performance do N8N**

---

## 🚀 Quick Start

### 1. Iniciar os containers

```bash
cd docker
docker-compose up -d
```

### 2. Verificar status

```bash
docker-compose ps
```

Você deve ver:
- `n8n-victoria-metrics` - Running on port 8428
- `n8n-grafana` - Running on port 3100

### 3. Acessar serviços

**Grafana:**
- URL: http://localhost:3100
- User: `admin`
- Password: `admin`

**Victoria Metrics:**
- URL: http://localhost:8428
- Metrics endpoint: http://localhost:8428/metrics

---

## 📊 Dashboards Disponíveis

Após login no Grafana, você encontrará:

1. **N8N Performance Overview** - Dashboard principal
   - Total de execuções
   - Taxa de sucesso
   - Execuções por minuto
   - Duração média
   - Top 10 workflows mais lentos

---

## 🔧 Configuração

### Victoria Metrics

**Retenção de dados:** 90 dias (configurável)
```yaml
command:
  - '-retentionPeriod=90d'  # Altere conforme necessário
```

**Porta:** 8428 (padrão)

### Grafana

**Porta:** 3100 (para evitar conflito com outras instâncias)
```yaml
ports:
  - "3100:3000"  # Host:Container
```

**Credenciais padrão:**
- User: admin
- Password: admin (altere após primeiro login!)

---

## 📈 Enviar Métricas

### Opção 1: Via Script Python

```python
from scripts.n8n_metrics_exporter import N8NMetricsExporter

exporter = N8NMetricsExporter(
    n8n_url="https://workflow.vya.digital/",
    n8n_api_key="sua-api-key",
    vm_url="http://localhost:8428"
)

# Coletar e enviar métricas
exporter.collect_and_push()
```

### Opção 2: Prometheus Format (Push Gateway)

```bash
curl -X POST http://localhost:8428/api/v1/import/prometheus \
  -d 'n8n_executions_total{workflow="my-workflow"} 42'
```

### Opção 3: Remote Write (quando tiver Prometheus)

```yaml
# prometheus.yml
remote_write:
  - url: http://localhost:8428/api/v1/write
```

---

## 🔍 Queries PromQL Úteis

### Taxa de Execuções
```promql
rate(n8n_executions_total[5m]) * 60
```

### Taxa de Sucesso
```promql
sum(n8n_executions_success) / sum(n8n_executions_total) * 100
```

### Latência P95
```promql
histogram_quantile(0.95, n8n_execution_duration_seconds_bucket)
```

### Top 10 Workflows Mais Lentos
```promql
topk(10, avg by (workflow_name) (n8n_execution_duration_seconds))
```

### Workflows com Maior Taxa de Erro
```promql
topk(10, 
  sum by (workflow_name) (n8n_executions_failed) / 
  sum by (workflow_name) (n8n_executions_total)
)
```

---

## 🛠️ Comandos Úteis

### Parar os containers
```bash
docker-compose down
```

### Parar e remover volumes (limpar dados)
```bash
docker-compose down -v
```

### Ver logs
```bash
docker-compose logs -f victoria-metrics
docker-compose logs -f grafana
```

### Restart
```bash
docker-compose restart
```

### Atualizar imagens
```bash
docker-compose pull
docker-compose up -d
```

---

## 📁 Estrutura de Arquivos

```
docker/
├── docker-compose.yml              # Configuração principal
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── victoria-metrics.yml  # Datasource auto-config
│   │   └── dashboards/
│   │       └── dashboards.yml        # Dashboard provisioning
│   └── dashboards/
│       └── n8n-performance-overview.json  # Dashboard principal
└── README.md                       # Este arquivo
```

---

## 🔐 Segurança

### Produção

**Altere a senha do Grafana:**
```bash
docker exec -it n8n-grafana grafana-cli admin reset-admin-password <nova-senha>
```

**Configure autenticação no Victoria Metrics:**
```yaml
command:
  - '-httpAuth.username=admin'
  - '-httpAuth.password=secure-password'
```

---

## 🚨 Troubleshooting

### Victoria Metrics não inicia
```bash
# Verificar logs
docker-compose logs victoria-metrics

# Verificar permissões do volume
docker volume inspect docker_victoria-metrics-data
```

### Grafana não conecta no Victoria Metrics
```bash
# Verificar se estão na mesma rede
docker network inspect docker_n8n-monitoring

# Testar conectividade
docker exec -it n8n-grafana curl http://victoria-metrics:8428/health
```

### Porta 3100 ou 8428 já em uso
```bash
# Alterar portas no docker-compose.yml
ports:
  - "3101:3000"  # Para Grafana
  - "8429:8428"  # Para Victoria Metrics
```

---

## 📊 Migração Futura para Prometheus

Quando o Prometheus estiver disponível:

1. **Opção 1: Remote Write** (Victoria Metrics continua como storage)
```yaml
# prometheus.yml
remote_write:
  - url: http://victoria-metrics:8428/api/v1/write
```

2. **Opção 2: Victoria Metrics como fonte**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'victoria-metrics'
    static_configs:
      - targets: ['victoria-metrics:8428']
```

3. **Opção 3: Migrar dados**
```bash
# Export de Victoria Metrics
curl -G http://localhost:8428/api/v1/export \
  --data-urlencode 'match[]={__name__=~"n8n_.*"}'

# Import para Prometheus (usando remote write)
```

**Benefício:** PromQL queries não mudam! 🎯

---

## 💡 Próximos Passos

1. ✅ Iniciar stack: `docker-compose up -d`
2. ✅ Acessar Grafana: http://localhost:3100
3. ⏳ Configurar script de coleta (n8n_metrics_exporter.py)
4. ⏳ Criar alertas no Grafana
5. ⏳ Adicionar mais dashboards

---

**Documentação completa:** ../docs/METRICS_GUIDE.md
