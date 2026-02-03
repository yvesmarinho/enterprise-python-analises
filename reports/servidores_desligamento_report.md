# 📋 Relatório de Servidores - Candidatos a Desligamento
**Data de Análise:** 16/01/2026 11:16:45
---
## 🖥️ wf005.vya.digital
**Timestamp:** 2026-01-16T10:53:55.198455

### 📊 Resumo de Recursos
- **Total de Containers:** 13
- **CPU Total:** 6.32%
- **Memória Total:** 4.81 GB (4922.44 MB)
- **Memória Média por Container:** 378.65 MB

### 📦 Containers
| # | Nome | Imagem | CPU % | Memória | Portas | Volumes | Migar | Migrado |
|---|------|--------|-------|---------|--------|----------|------|------|
| 1 | `dashboard` | metabase | 3.93 | 2.68 GB | 3002→3000 | 1 | sim ||
| 2 | `redis` | redis | 0.74 | 578 MB | 6379→6379 | 1 (350MB) | não ||
| 3 | `evolution_api_wea001` | evolution-api | 0.00 | 311 MB | 8088→8080 | 2 (0MB) | não ||
| 4 | `portainer` | sha256 | 0.04 | 236 MB | 9000→9000 | 2 (1909MB) | não ||
| 5 | `pgadmin` | pgadmin4 | 0.10 | 226 MB | 8082→80 | 3 (1237MB) | sim |erro|
| 6 | `evolution_api_wea002` | evolution-api | 0.03 | 171 MB | 8089→8080 | 2 (0MB) | não ||
| 7 | `dashy` | dashy | 0.37 | 161 MB | 8083→8080 | 2 (37MB) | sim | sim | sim |
| 8 | `rabbitmq` | rabbitmq | 1.04 | 155 MB | 15673→15672, 5673→5672 | 4 (1MB) | não ||
| 9 | `traefik` | sha256 | 0.00 | 138 MB | 443→443, 80→80, 9090→9090 | 8 (426MB) | não |
| 10 | `code_store` | bytestash | 0.06 | 69 MB | 5000→5000 | 1 (2MB) | não | sim |
| 11 | `api013.vya.digital` | node-survey | 0.00 | 59 MB | - | 2 | sim | sim |
| 12 | `dbmgnt002.vya.digital` | adminer | 0.01 | 40 MB | - | 1 | sim | sim |  |
| 13 | `api012.vyadigital` | enterprise-node-billet | 0.00 | 35 MB | 3033→3033 | 1 | sim | sim|

### 🔍 Observações
- **Alto uso de Memória (>500MB):** 2 container(s)
  - `dashboard`: 2.68 GB
  - `redis`: 0.56 GB
- **Redes utilizadas:** app-network

- **Volumes com dados significativos (>100MB):**
  - `portainer`: /opt/docker_user/portainer/portainer_data (1909.31 MB)
  - `pgadmin`: /var/lib/docker/volumes/3c78cfebfc7daa0317eda069ca07a0d0753d6fbf99332ed6e08554c28394a7d4/_data (1236.75 MB)
  - `traefik`: /opt/docker_user/traefik/log (425.69 MB)
  - `redis`: /opt/docker_user/redis/data/redis (350.34 MB)

---

## 🖥️ wf006.vya.digital
**Timestamp:** 2026-01-16T10:57:28.755270

### 📊 Resumo de Recursos
- **Total de Containers:** 8
- **CPU Total:** 54.66%
- **Memória Total:** 12.78 GB (13085.39 MB)
- **Memória Média por Container:** 1635.67 MB

### 📦 Containers
| # | Nome | Imagem | CPU % | Memória | Portas | Volumes |
|---|------|--------|-------|---------|--------|----------|
| 1 | `synChat` | chatwoot | 25.46 | 9.45 GB | 3008→3000 | 10 (20840MB) |
| 2 | `chat-vya-digital` | chatwoot | 0.52 | 1.68 GB | - | 2 |
| 3 | `traefik` | traefik | 0.00 | 550 MB | 443→443, 80→80, 9090→9090 | 8 (796MB) |
| 4 | `synChatSidekiq` | chatwoot | 18.38 | 459 MB | - | 2 |
| 5 | `chat-vya-digital-sidekiq` | chatwoot | 0.05 | 414 MB | - | 2 |
| 6 | `portainer` | sha256 | 0.32 | 126 MB | 9000→9000 | 2 (1MB) |
| 7 | `perfexcrm` | perfexcrm | 0.01 | 109 MB | 8001→80 | 2 (144MB) |
| 8 | `redis` | redis | 9.92 | 31 MB | 6379→6379 | 1 (5MB) |

### 🔍 Observações
- **Alto uso de CPU (>5%):** 3 container(s)
  - `synChat`: 25.46%
  - `synChatSidekiq`: 18.38%
  - `redis`: 9.92%
- **Alto uso de Memória (>500MB):** 3 container(s)
  - `synChat`: 9.45 GB
  - `chat-vya-digital`: 1.68 GB
  - `traefik`: 0.54 GB
- **Redes utilizadas:** app-network

- **Volumes com dados significativos (>100MB):**
  - `synChat`: /var/log (20840.17 MB)
  - `traefik`: /opt/docker_user/traefik/log (795.72 MB)
  - `perfexcrm`: /opt/docker_user/perfexcrm/var_www/html (144.23 MB)

---

## 📌 Próximas Ações

### ✅ Checklist de Migração

- [ ] Backup de todos os volumes com dados
- [ ] Documentar configurações de rede
- [ ] Verificar dependências entre containers
- [ ] Testar conectividade de portas nos servidores destino
- [ ] Planejar janela de manutenção
- [ ] Atualizar DNS/Proxy reverso
- [ ] Validar funcionamento após migração

