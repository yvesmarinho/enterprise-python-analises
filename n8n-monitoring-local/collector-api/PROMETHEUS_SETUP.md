# Configuração do Prometheus Pushgateway

Este documento explica como configurar o Collector API para enviar métricas para a **Enterprise Observability Stack** hospedada em **wfdb01.vya.digital**.

## 📋 Visão Geral

O Collector API foi atualizado para suportar dois modos de exportação de métricas:

1. **Modo Pull (padrão Prometheus)**: Prometheus faz scraping do endpoint `/metrics` do Collector API
2. **Modo Push (Pushgateway)**: Collector API envia métricas periodicamente para o Pushgateway

### 🏢 Enterprise Observability Stack

A stack centralizada hospedada em **wfdb01.vya.digital** inclui:

- **Prometheus**: https://prometheus.vya.digital
- **Pushgateway**: https://prometheus.vya.digital/pushgateway
- **Grafana**: https://grafana.vya.digital
- **Alertmanager**: https://alertmanager.vya.digital
- **Loki**: https://loki.vya.digital
- **VictoriaMetrics**: Armazenamento de longo prazo (12 meses)

Todos os serviços são acessíveis via HTTPS com certificados Let's Encrypt gerenciados pelo Traefik.

## 🎯 Por que usar Pushgateway?

- **Ideal para jobs de curta duração**: Métricas não se perdem se o serviço for reiniciado
- **Serviços atrás de firewall**: Não precisa expor portas para scraping
- **Controle de frequência**: Você define quando enviar as métricas
- **Múltiplas instâncias**: Cada instância pode enviar suas métricas independentemente

## ⚙️ Configuração

### 1. Configurar Variáveis de Ambiente

Crie um arquivo `.secrets/.env` baseado no `.env.example`:

```bash
mkdir -p .secrets
cp .env.example .secrets/.env
```

Edite `.secrets/.env` e configure:

```bash
# Prometheus Pushgateway
PROMETHEUS_PUSHGATEWAY_URL=https://prometheus.vya.digital/pushgateway
PROMETHEUS_PUSHGATEWAY_ENABLED=true
PROMETHEUS_PUSHGATEWAY_INTERVAL=60
PROMETHEUS_JOB_NAME=collector_api
```

**Parâmetros:**
- `PROMETHEUS_PUSHGATEWAY_URL`: URL do Pushgateway via Traefik (HTTPS seguro)
- `PROMETHEUS_PUSHGATEWAY_ENABLED`: `true` para habilitar, `false` para desabilitar
- `PROMETHEUS_PUSHGATEWAY_INTERVAL`: Intervalo em segundos entre cada envio (padrão: 60)
- `PROMETHEUS_JOB_NAME`: Nome do job no Prometheus (usado para identificação)

### 2. Verificar Conectividade

Teste se o Pushgateway está acessível:

```bash
curl http://wfdb01.vya.digital:9091/
```

Ou teste com o IP direto:

```bash
curl http://86.48.31.149:9091/
```

Você deve ver uma página HTML do Pushgateway.

## 🚀 Como Funciona

### Inicialização

Quando o Collector API inicia:

1. Verifica se `PROMETHEUS_PUSHGATEWAY_ENABLED=true`
2. Cria uma instância do `PrometheusPusher`
3. Inicia uma task assíncrona para enviar métricas periodicamente

### Envio de Métricas

A cada `PROMETHEUS_PUSHGATEWAY_INTERVAL` segundos:

1. Coleta todas as métricas do registro Prometheus
2. Serializa no formato Prometheus
3. Envia via HTTP POST para: `http://wfdb01.vya.digital:9091/metrics/job/{JOB_NAME}/instance/{INSTANCE}`

### Identificação

Cada instância do Collector API é identificada por:
- **Job**: Nome configurado em `PROMETHEUS_JOB_NAME`
- **Instance**: `{API_HOST}:{API_PORT}` (ex: `0.0.0.0:5000`)

## 📊 Métricas Disponíveis

O Collector API exporta as seguintes métricas:

### Métricas de API
- `api_requests_total`: Total de requisições recebidas
- `api_request_duration_seconds`: Duração das requisições

### Métricas de Latência de Rede
- `network_latency_rtt_seconds`: Round-trip time calculado no servidor

### Métricas de Database
- `database_query_latency_seconds`: Latência de queries
- `database_connection_errors_total`: Erros de conexão
- `database_available`: Disponibilidade do banco (1=disponível, 0=indisponível)

### Métricas de Serviço
- `collector_api_up`: Serviço ativo (1) ou inativo (0)

## 🔍 Verificando Métricas

### 1. Verificar no Pushgateway

Acesse o Pushgateway via navegador:
```
http://wfdb01.vya.digital:9091/
```

Ou via curl:
```bash
curl http://wfdb01.vya.digital:9091/metrics
```

Procure por métricas com o job configurado:
```
# Exemplo
database_available{db_type="postgresql",instance="0.0.0.0:5000",job="collector_api"} 1
```

### 2. Verificar no Prometheus

Se o Prometheus está configurado para fazer scraping do Pushgateway, acesse:
```
http://wfdb01.vya.digital:9090/
```

Execute queries como:
```promql
# Ver todas as métricas do collector_api
{job="collector_api"}

# Latência de queries PostgreSQL
database_query_latency_seconds{job="collector_api", db_type="postgresql"}

# Disponibilidade de databases
database_available{job="collector_api"}
```

## 🐳 Deploy com Docker

### Dockerfile

O Dockerfile já está configurado. Apenas construa e execute:

```bash
# Construir imagem
docker build -t collector-api:latest .

# Executar container
docker run -d \
  --name collector-api \
  -p 5000:5000 \
  -p 9102:9102 \
  -v $(pwd)/.secrets:/app/.secrets:ro \
  collector-api:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  collector-api:
    build: .
    container_name: collector-api
    ports:
      - "5000:5000"
      - "9102:9102"
    volumes:
      - ./.secrets:/app/.secrets:ro
    environment:
      - PROMETHEUS_PUSHGATEWAY_URL=http://wfdb01.vya.digital:9091
      - PROMETHEUS_PUSHGATEWAY_ENABLED=true
    restart: unless-stopped
```

## 🔧 Troubleshooting

### Problema: Métricas não aparecem no Pushgateway

**Verificar:**
1. Logs do container/aplicação:
   ```bash
   docker logs collector-api | grep prometheus
   ```

2. Conectividade com o Pushgateway:
   ```bash
   docker exec collector-api curl http://wfdb01.vya.digital:9091/
   ```

3. Configuração:
   ```bash
   docker exec collector-api env | grep PROMETHEUS
   ```

### Problema: Erro de conexão

**Possíveis causas:**
- Firewall bloqueando porta 9091
- Pushgateway não está rodando
- URL incorreta

**Solução:**
```bash
# No servidor wfdb01.vya.digital
sudo systemctl status prometheus-pushgateway
sudo ufw status
```

### Problema: Métricas duplicadas

Cada instância do Collector API cria um identificador único baseado no `API_HOST:API_PORT`. Se você tiver múltiplas instâncias, cada uma terá sua própria entrada no Pushgateway.

Para limpar métricas antigas:
```bash
# Deletar métricas de uma instância específica
curl -X DELETE http://wfdb01.vya.digital:9091/metrics/job/collector_api/instance/0.0.0.0:5000
```

## 📈 Monitoramento e Alertas

### Dashboards Grafana

Configure datasource no Grafana apontando para o Prometheus:
```
http://wfdb01.vya.digital:9090
```

### Queries úteis

```promql
# Taxa de requisições por minuto
rate(api_requests_total{job="collector_api"}[1m])

# Latência média de database
avg(database_query_latency_seconds{job="collector_api"})

# Disponibilidade de databases
min(database_available{job="collector_api"}) by (db_type)
```

### Alertas

Exemplo de regra de alerta:

```yaml
groups:
  - name: collector_api
    interval: 30s
    rules:
      - alert: DatabaseUnavailable
        expr: database_available{job="collector_api"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database {{ $labels.db_type }} is unavailable"
          description: "Database {{ $labels.db_type }} has been unavailable for more than 2 minutes"
      
      - alert: HighDatabaseLatency
        expr: database_query_latency_seconds{job="collector_api"} > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database latency detected"
          description: "Database {{ $labels.db_type }} latency is above 1 second"
```

## 🔐 Segurança

### Autenticação

Por padrão, o Pushgateway não tem autenticação. Para produção, considere:

1. **Reverse proxy com autenticação** (Nginx, Traefik)
2. **Firewall rules** (permitir apenas IPs conhecidos)
3. **VPN ou rede privada**

### Exemplo Nginx com autenticação básica:

```nginx
location /pushgateway/ {
    auth_basic "Prometheus Pushgateway";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    proxy_pass http://localhost:9091/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## 📚 Referências

- [Prometheus Pushgateway](https://github.com/prometheus/pushgateway)
- [Prometheus Client Python](https://github.com/prometheus/client_python)
- [Best Practices for Pushgateway](https://prometheus.io/docs/practices/pushing/)

## 🆘 Suporte

Para problemas ou dúvidas:
1. Verificar logs do Collector API
2. Verificar logs do Pushgateway no servidor wfdb01.vya.digital
3. Consultar a documentação oficial do Prometheus
