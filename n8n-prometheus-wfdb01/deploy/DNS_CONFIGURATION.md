# DNS Configuration for Monitoring Services
# Data: 2026-02-04

## 📍 Serviços com DNS Público

### wf001 (USA - Virginia)

**Stack de Monitoramento**:
```
wf008 (Brasil) → Ping Service
        ↓
    HTTPS POST
        ↓
api-monitoring.vya.digital (Collector API)
        ↓
    VictoriaMetrics (armazenamento)
        ↓
monitoring.vya.digital (Grafana dashboards)
```

#### 1. Grafana - Dashboards e Visualização
**DNS**: `monitoring.vya.digital`  
**IP**: IP_do_wf001  
**Porta Interna**: 3000  
**Porta Externa**: 443 (HTTPS via Traefik)  
**Acesso**: Público (com autenticação Grafana)

```dns
# Registro DNS tipo A
monitoring.vya.digital.  IN  A  <IP_wf001>
```

#### 2. Collector API - Endpoint para Pings
**DNS**: `api-monitoring.vya.digital`  
**IP**: IP_do_wf001  
**Porta Interna**: 5000  
**Porta Externa**: 443 (HTTPS via Traefik)  
**Acesso**: Restrito (API Key obrigatória)

```dns
# Registro DNS tipo A
api-monitoring.vya.digital.  IN  A  <IP_wf001>
```

---

### 🔒 VictoriaMetrics (Sem Acesso Público)

**Acesso**: Apenas interno via rede Docker  
**Porta**: 8428 (bind localhost apenas)  
**Motivo**: Não possui autenticação nativa - expor publicamente seria risco de segurança

Serviços que acessam internamente:
- Grafana → `http://victoria-metrics:8428`
- Collector API → `http://victoria-metrics:8428`

---

### wf008 (Brasil - São Paulo)

#### Sem DNS Público Necessário
Os serviços no wf008 (Ping Service, Node Exporter, cAdvisor) não precisam de DNS público:
- Ping Service **envia** dados para wf001 (não recebe conexões externas)
- Métricas são coletadas remotamente se necessário (futuro)

---

## 🔧 Configuração DNS - Resumo

### Registros DNS a Criar

```dns
# Grafana (público com autenticação)
monitoring.vya.digital.           IN  A  <IP_wf001>

# Collector API (com API Key)
api-monitoring.vya.digital.       IN  A  <IP_wf001>
```

---

## 🚀 Implementação com Traefik

### Docker Compose já configurado

Os serviços **Grafana** e **Collector API** no arquivo [wf001-usa/docker-compose.yml](wf001-usa/docker-compose.yml) já possuem as labels do Traefik configuradas:

**Grafana**:
```yaml
labels:
  - 'traefik.enable=true'
  - 'traefik.http.routers.grafana.rule=Host(`monitoring.vya.digital`)'
  - 'traefik.http.routers.grafana.tls=true'
  - 'traefik.http.routers.grafana.entrypoints=websecure'
  - 'traefik.http.routers.grafana.tls.certresolver=lets-encrypt'
  - 'traefik.http.services.grafana.loadbalancer.server.port=3000'
  - 'traefik.http.middlewares.grafana.headers.SSLRedirect=true'
  - 'traefik.http.middlewares.grafana.headers.STSSeconds=315360000'
  - 'traefik.http.middlewares.grafana.headers.browserXSSFilter=true'
  - 'traefik.http.middlewares.grafana.headers.contentTypeNosniff=true'
  - 'traefik.http.middlewares.grafana.headers.forceSTSHeader=true'
  - 'traefik.http.middlewares.grafana.headers.SSLHost=vya.digital'
  - 'traefik.http.middlewares.grafana.headers.STSIncludeSubdomains=true'
  - 'traefik.http.middlewares.grafana.headers.STSPreload=true'
  - 'traefik.http.routers.grafana.middlewares=grafana@docker'
  - 'traefik.docker.network=app-network'
```

**Collector API**:
```yaml
labels:
  - 'traefik.enable=true'
  - 'traefik.http.routers.collector-api.rule=Host(`api-monitoring.vya.digital`)'
  - 'traefik.http.routers.collector-api.tls=true'
  - 'traefik.http.routers.collector-api.entrypoints=websecure'
  - 'traefik.http.routers.collector-api.tls.certresolver=lets-encrypt'
  - 'traefik.http.services.collector-api.loadbalancer.server.port=5000'
  - 'traefik.http.middlewares.collector-api.headers.SSLRedirect=true'
  - 'traefik.http.middlewares.collector-api.headers.STSSeconds=315360000'
  - 'traefik.http.middlewares.collector-api.headers.browserXSSFilter=true'
  - 'traefik.http.middlewares.collector-api.headers.contentTypeNosniff=true'
  - 'traefik.http.middlewares.collector-api.headers.forceSTSHeader=true'
  - 'traefik.http.middlewares.collector-api.headers.SSLHost=vya.digital'
  - 'traefik.http.middlewares.collector-api.headers.STSIncludeSubdomains=true'
  - 'traefik.http.middlewares.collector-api.headers.STSPreload=true'
  - 'traefik.http.routers.collector-api.middlewares=collector-api@docker'
  - 'traefik.docker.network=app-network'
```

### Requisitos

1. **Traefik rodando no wf001** com:
   - Rede `app-network` criada
   - Certificate resolver `lets-encrypt` configurado
   - Entrypoint `websecure` na porta 443

2. **DNS configurados** apontando para IP do wf001

3. **Rede app-network**:
```bash
docker network create app-network
```

---

## 📝 Passos para Implementação

### 1. Registrar DNS
```bash
# No painel do provedor DNS (Cloudflare, Route53, etc.)
# Adicionar registros A apontando para o IP do wf001
monitoring.vya.digital      → <IP_wf001>
api-monitoring.vya.digital  → <IP_wf001>
```

### 2. Criar Rede Docker
```bash
ssh root@wf001.vya.digital
docker network create app-network
```

### 3. Deploy dos Serviços
```bash
cd /opt/monitoring-prod
docker compose up -d
```

O Traefik irá automaticamente:
- ✅ Detectar os serviços via labels
- ✅ Configurar rotas HTTPS
- ✅ Obter certificados Let's Encrypt
- ✅ Aplicar headers de segurança
- ✅ Redirecionar HTTP → HTTPS

---

## 🧪 Testes de Validação

### Grafana
```bash
# Testar DNS
nslookup monitoring.vya.digital

# Testar HTTPS
curl -I https://monitoring.vya.digital

# Verificar redirect HTTP→HTTPS
curl -I http://monitoring.vya.digital
```

### Collector API
```bash
# Do servidor wf008
curl -X POST https://api-monitoring.vya.digital/api/ping \
  -H "X-API-Key: ${COLLECTOR_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "ping_id": "test-001",
    "timestamp_start": "2026-02-04T13:00:00Z",
    "source": {
      "location": "wf008_brazil",
      "datacenter": "wf008",
      "country": "BR"
    }
  }'

# Deve retornar 200 OK com processamento RTT
```

---

## 🔒 Segurança

### Headers de Segurança (já configurados via Traefik)
- ✅ SSL Redirect (HTTP → HTTPS)
- ✅ HSTS (Strict-Transport-Security)
- ✅ Browser XSS Filter
- ✅ Content Type Nosniff
- ✅ Force STS Header
- ✅ STS Include Subdomains
- ✅ STS Preload

### Autenticação
- **Grafana**: Login com usuário/senha (configurado via env)
- **Collector API**: Header `X-API-Key` obrigatório

### Firewall (Opcional - adicional ao Traefik)
```bash
# wf001 - Permitir apenas HTTPS público
ufw allow 443/tcp

# Bloquear acesso direto às portas internas
ufw deny 3000/tcp
ufw deny 5000/tcp
```

---

## 📊 URLs Finais

Após configuração completa:

- **Grafana**: https://monitoring.vya.digital
- **Collector API**: https://api-monitoring.vya.digital
- **VictoriaMetrics**: Acesso apenas interno (sem DNS público)

**Credenciais Grafana**:
- User: Configurado em `GRAFANA_ADMIN_USER`
- Password: Configurado em `GRAFANA_ADMIN_PASSWORD`

---

## 🔄 Atualização dos Serviços

### wf008 (Ping Service)
O arquivo [wf008-brasil/docker-compose.yml](wf008-brasil/docker-compose.yml) já está atualizado:
```yaml
environment:
  - TARGET_URL=https://api-monitoring.vya.digital/api/ping
```

### wf001 (Grafana)
O arquivo [wf001-usa/docker-compose.yml](wf001-usa/docker-compose.yml) já está configurado:
```yaml
environment:
  - GF_SERVER_ROOT_URL=https://monitoring.vya.digital
```
