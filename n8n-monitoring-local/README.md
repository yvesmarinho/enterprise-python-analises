# N8N Monitoring - Ambiente de Desenvolvimento Local

Sistema de monitoramento de latência de rede e performance de banco de dados para N8N.

## 🎯 Objetivo

Desenvolver e testar localmente um sistema completo de monitoramento que mede:
- **Latência de rede** entre Brasil (wf008) e USA (wf001)
- **Latência de banco de dados** (PostgreSQL e MySQL)
- **Performance de API** do Collector
- **Métricas de disponibilidade** e resiliência

## 📦 Componentes

### Serviços Principais
- **Ping Service**: Envia requisições periódicas do Brasil para USA
- **Collector API**: Recebe pings, mede latência e monitora bancos de dados externos
- **VictoriaMetrics**: Armazena todas as métricas (retenção 90 dias)
- **Grafana**: Visualização de dashboards e alertas

### Infraestrutura Externa (Produção)
- **PostgreSQL**: wfdb02.vya.digital:5432 (monitor_db)
- **MySQL**: wfdb02.vya.digital:3306 (monitor_db)
- **N8N**: workflow.vya.digital

### Infraestrutura Local
- **Node Exporter**: Métricas do host
- **cAdvisor**: Métricas de containers Docker

## 🚀 Quick Start

### Pré-requisitos

```bash
# Verificar Docker
docker --version
docker-compose --version

# Verificar Python (opcional, para desenvolvimento)
python3 --version  # Deve ser 3.12+
```

### 1. Clone e Configure

```bash
# Navegue até o diretório
cd n8n-monitoring-local

# Crie o diretório de secrets
mkdir -p .secrets

# Copie o arquivo de exemplo
cp .env.example .secrets/.env

# Edite as credenciais (OBRIGATÓRIO)
nano .secrets/.env
```

**⚠️ IMPORTANTE**: O arquivo `.secrets/.env` contém credenciais de produção:
- API Key do Collector
- Credenciais N8N (workflow.vya.digital)
- Credenciais PostgreSQL (wfdb02.vya.digital)
- Credenciais MySQL (wfdb02.vya.digital)

**Não commite este arquivo no Git!** Já está no `.gitignore`.

### 2. Inicie os Serviços

```bash
# Iniciar toda a stack
docker-compose up -d

# Ver logs em tempo real
docker-compose logs -f

# Verificar status
docker-compose ps
```

### 3. Aguarde Inicialização

Os serviços levam ~2-3 minutos para inicializar completamente. Monitore os logs:

```bash
# Aguardar todos os health checks passarem
docker-compose logs -f | grep "healthy"
```

### 4. Acesse os Serviços

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / admin |
| VictoriaMetrics | http://localhost:8428 | - |
| Collector API | http://localhost:5000 | API Key: (ver .secrets/.env) |
| Ping Metrics | http://localhost:9101/metrics | - |
| Collector Metrics | http://localhost:9102/metrics | - |
| Node Exporter | http://localhost:9100/metrics | - |
| cAdvisor | http://localhost:8080 | - |

**Serviços Externos (Produção)**:
| Serviço | URL | Acesso |
|---------|-----|--------|
| N8N | https://workflow.vya.digital | Credenciais no .secrets/.env |
| PostgreSQL | wfdb02.vya.digital:5432 | monitor_user (ver .secrets/.env) |
| MySQL | wfdb02.vya.digital:3306 | monitor_user (ver .secrets/.env) |

## 🧪 Testar o Sistema

### Teste Manual de Ping

```bash
# Obtenha a API Key do arquivo .secrets/.env
API_KEY=$(grep COLLECTOR_API_KEY .secrets/.env | cut -d'=' -f2)

# Enviar um ping manual
curl -X POST http://localhost:5000/api/ping \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp_start": "'$(date -u +"%Y-%m-%dT%H:%M:%S.%6NZ")'",
    "source": {
      "location": "manual_test",
      "datacenter": "local",
      "country": "BR"
    },
    "ping_id": "test-123"
  }'
```

### Verificar Health Checks

```bash
# Collector API
curl http://localhost:5000/health | jq .

# Grafana
curl http://localhost:3000/api/health

# VictoriaMetrics
curl http://localhost:8428/health
```

### Verificar Métricas

```bash
# Métricas do Ping Service
curl http://localhost:9101/metrics | grep network_latency

# Métricas do Collector API
curl http://localhost:9102/metrics | grep database_query_latency

# Query no VictoriaMetrics
curl -s 'http://localhost:8428/api/v1/query?query=network_latency_rtt_seconds' | jq .
```

### Testar Bancos de Dados

```bash
# Testar conectividade PostgreSQL (externo)
docker-compose exec collector-api bash -c "apt-get update && apt-get install -y postgresql-client && psql -h wfdb02.vya.digital -U monitor_user -d monitor_db -c 'SELECT 1'"

# Testar conectividade MySQL (externo)
docker-compose exec collector-api bash -c "mysql -h wfdb02.vya.digital -u monitor_user -p -D monitor_db -e 'SELECT 1'"

# Ver logs de database probes
docker-compose logs -f collector-api | grep -E "postgres|mysql"
```

## 📊 Dashboards Grafana

Após login no Grafana (http://localhost:3000):

1. **N8N Performance Overview**
   - Latência de rede Brasil → USA
   - Métricas de API
   - Status de serviços

2. **Database Performance**
   - Latência de queries (PostgreSQL e MySQL)
   - Disponibilidade de bancos
   - Erros de conexão

3. **Infrastructure Monitoring**
   - CPU, RAM, Network do host
   - Métricas de containers Docker
   - Disponibilidade geral

## 🛠️ Desenvolvimento

### Estrutura do Projeto

```
n8n-monitoring-local/
├── ping-service/           # Serviço de ping (Brasil)
│   ├── src/
│   │   ├── main.py        # Entry point
│   │   ├── ping_client.py # Cliente HTTP
│   │   ├── scheduler.py   # Scheduler de pings
│   │   ├── metrics.py     # Métricas Prometheus
│   │   └── config.py      # Configurações
│   ├── tests/             # Testes unitários
│   ├── Dockerfile
│   └── requirements.txt
│
├── collector-api/          # API Collector (USA)
│   ├── src/
│   │   ├── main.py        # FastAPI app
│   │   ├── api/           # Endpoints
│   │   ├── database/      # Probes de DB
│   │   ├── metrics/       # Métricas
│   │   └── models.py      # Modelos Pydantic
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── infrastructure/         # Configs de infraestrutura
│   ├── grafana/
│   │   ├── dashboards/
│   │   └── provisioning/
│   └── databases/
│       ├── postgres/init.sql
│       └── mysql/init.sql
│
├── scripts/               # Scripts utilitários
├── docker-compose.yml
└── .env.example
```

### Desenvolvimento Iterativo

```bash
# Editar código
vim collector-api/src/api/__init__.py

# Restart apenas o serviço (auto-reload ativo)
docker-compose restart collector-api

# Ver logs
docker-compose logs -f collector-api

# Rebuild após mudanças em requirements
docker-compose build collector-api
docker-compose up -d collector-api
```

### Executar Testes

```bash
# Testes do Ping Service
docker-compose exec ping-service pytest tests/ -v

# Testes do Collector API
docker-compose exec collector-api pytest tests/ -v
```

## 🔧 Troubleshooting

### Serviços não iniciam

```bash
# Ver logs de todos os serviços
docker-compose logs

# Rebuild completo
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Métricas não aparecem no Grafana

```bash
# Verificar se VictoriaMetrics está recebendo dados
curl -s 'http://localhost:8428/api/v1/label/__name__/values' | jq .

# Verificar datasource do Grafana
curl -s http://localhost:3000/api/datasources | jq .
```

### Erro de conexão com banco de dados

```bash
# Verificar se bancos estão rodando
docker-compose ps postgres mysql

# Ver logs do banco
docker-compose logs postgres
docker-compose logs mysql

# Testar conexão manualmente
docker-compose exec collector-api psql -h postgres -U n8n -d n8n
```

### Porta já em uso

```bash
# Verificar portas em uso
sudo netstat -tlnp | grep -E '3000|5000|5678|8428'

# Parar serviços conflitantes ou alterar portas no docker-compose.yml
```

## 🧹 Limpeza

```bash
# Parar todos os serviços
docker-compose down

# Parar e remover volumes (CUIDADO: apaga dados)
docker-compose down -v

# Limpar imagens não utilizadas
docker system prune -a
```

## 📈 Métricas Disponíveis

### Network Latency
- `network_latency_rtt_seconds` - Round-trip time
- `ping_requests_total` - Total de requisições
- `ping_errors_total` - Total de erros

### Database
- `database_query_latency_seconds` - Latência de queries
- `database_available` - Disponibilidade (1 = up, 0 = down)
- `database_connection_errors_total` - Erros de conexão

### API
- `api_requests_total` - Requests por endpoint
- `api_request_duration_seconds` - Duração de requests
- `collector_api_up` - Status do serviço

## 📝 Próximos Passos

1. ✅ Ambiente local funcionando
2. ⏳ Criar dashboards completos no Grafana
3. ⏳ Configurar alertas
4. ⏳ Testes de carga
5. ⏳ Deploy em staging (wf001)
6. ⏳ Deploy em produção (wf001 + wf008)

## 🆘 Suporte

- **Logs**: `docker-compose logs -f [service-name]`
- **Status**: `docker-compose ps`
- **Restart**: `docker-compose restart [service-name]`
- **Rebuild**: `docker-compose build [service-name]`

## 📚 Documentação Adicional

- [API Documentation](http://localhost:5000/docs) - Swagger UI
- [Grafana Docs](https://grafana.com/docs/)
- [VictoriaMetrics Docs](https://docs.victoriametrics.com/)
- [Prometheus Metrics](https://prometheus.io/docs/concepts/metric_types/)

---

**Versão**: 1.0.0  
**Última atualização**: 04/02/2026
