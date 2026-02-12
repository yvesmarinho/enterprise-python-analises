# Guia de Deploy - Dashboards Grafana (Servidor Remoto)
**Data:** 09/02/2026
**Servidor:** wfdb01 (remoto via SSHFS)
**Objetivo:** Provisionar dashboards via arquivos no Grafana

---

## 📊 Problema Resolvido

### ❌ Situação Anterior
- Dashboards importados manualmente no Grafana
- UIDs de datasource incorretos (`"Prometheus"`, `"P4169E866C3094E38"`)
- Gráficos não exibiam dados
- Sem versionamento de dashboards

### ✅ Situação Atual
- **Dashboards provisionados via arquivos**
- **UIDs corrigidos para `"prometheus"`** (minúsculo)
- **Automação de deployment**
- **Versionamento via Git**

---

## 🏗️ Estrutura Criada

```
wfdb01-docker-folder/
├── docker-compose.yaml                          # ✅ ATUALIZADO
├── config/
│   └── datasources.yaml                         # UID: prometheus
└── grafana/
    ├── provisioning/
    │   └── dashboards/
    │       └── dashboards.yaml                  # ✅ NOVO
    └── dashboards/                              # ✅ NOVO
        ├── wfdb02 - MySQL Dashboard-1770665439838.json          (268KB)
        ├── WFDB02.vya.digital - PostgreSQL Database-...json     (78KB)
        ├── wfdb02 - MySQL Dashboard-1756827751674.json          (44KB)
        ├── wf008 - Docker Monitoring-1756735858594.json         (21KB)
        ├── n8n-performance-detailed.json                        (19KB)
        ├── n8n-node-performance.json                            (6.1KB)
        └── n8n-performance-overview.json                        (4.0KB)
```

---

## 🔧 Alterações no docker-compose.yaml

### Serviço Grafana - Volumes Adicionados

```yaml
volumes:
  # Datasources (já existia)
  - ./config/datasources.yaml:/etc/grafana/provisioning/datasources/datasources.yml

  # NOVO: Provisioning de dashboards
  - ./grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards:ro

  # NOVO: Arquivos JSON dos dashboards
  - ./grafana/dashboards:/var/lib/grafana/dashboards:ro

  # Volumes existentes
  - grafana:/var/lib/grafana
  - backup:/backup
```

**Modificações:**
- ✅ Adicionados 2 novos volumes (read-only)
- ✅ Dashboards carregados automaticamente no startup
- ✅ Atualizações refletidas sem restart (30s interval)

---

## 🚀 Deploy no Servidor Remoto

### Pré-requisitos
- [x] Acesso SSH ao servidor wfdb01
- [x] Docker e Docker Compose instalados
- [x] Grafana container parado ou disponível para restart

### Passo 1: Sincronizar Arquivos

```bash
# Via RSYNC (RECOMENDADO)
rsync -avz --progress \
  wfdb01-docker-folder/grafana/ \
  user@wfdb01:/opt/docker_user/enterprise-observability/grafana/

rsync -avz --progress \
  wfdb01-docker-folder/docker-compose.yaml \
  user@wfdb01:/opt/docker_user/enterprise-observability/

# OU via SCP (alternativa)
scp -r wfdb01-docker-folder/grafana/ \
  user@wfdb01:/opt/docker_user/enterprise-observability/

scp wfdb01-docker-folder/docker-compose.yaml \
  user@wfdb01:/opt/docker_user/enterprise-observability/
```

### Passo 2: Verificar Permissões

```bash
ssh user@wfdb01

# Navegar para diretório
cd /opt/docker_user/enterprise-observability

# Verificar estrutura
ls -la grafana/provisioning/dashboards/
ls -la grafana/dashboards/

# Ajustar permissões (se necessário)
chown -R 472:472 grafana/
chmod -R 755 grafana/provisioning/
chmod -R 644 grafana/dashboards/*.json
```

### Passo 3: Validar Configuração

```bash
# Verificar docker-compose.yaml
grep -A 5 "grafana:" docker-compose.yaml

# Validar sintaxe
docker-compose config | grep -A 10 "grafana"

# Verificar volumes
docker-compose config | grep "grafana/dashboards"
```

### Passo 4: Reiniciar Grafana

```bash
# Opção 1: Restart apenas do Grafana
docker-compose restart grafana

# Opção 2: Recriar container (recomendado)
docker-compose up -d --force-recreate grafana

# Verificar logs
docker logs -f enterprise-grafana --tail=50
```

---

## 🔍 Validação Pós-Deploy

### 1. Verificar Datasource UID

```bash
# Via API
curl -s -u admin:SENHA http://grafana.vya.digital/api/datasources | \
  jq '.[] | select(.type=="prometheus") | {name, uid}'

# Resultado esperado:
# {
#   "name": "Prometheus",
#   "uid": "prometheus"
# }
```

### 2. Verificar Dashboards Provisionados

```bash
# Listar dashboards
curl -s -u admin:SENHA http://grafana.vya.digital/api/search | \
  jq '.[] | {title, uid, folderId}'

# Resultado esperado: 7 dashboards
```

### 3. Verificar Logs do Grafana

```bash
docker logs enterprise-grafana 2>&1 | grep -i "dashboard"

# Procurar por:
# ✅ "Dashboard provisioning completed"
# ✅ "Inserted dashboard"
# ❌ "Dashboard provisioning failed"
```

### 4. Verificar UI

1. Acessar: https://grafana.vya.digital
2. Login: admin / [verificar secrets]
3. Navegação: **Dashboards** → **Browse**
4. Verificar:
   - ✅ 7 dashboards listados
   - ✅ Gráficos exibindo dados
   - ✅ Sem erros de datasource
   - ✅ Time range funcionando

---

## 📋 Dashboards Disponíveis

| Dashboard | Painéis | Tamanho | Status |
|-----------|---------|---------|--------|
| **wfdb02 - MySQL Dashboard** (completo) | 94 | 268KB | ✅ Pronto |
| **PostgreSQL Database** | 32 | 78KB | ✅ Pronto |
| **MySQL Dashboard** (simplificado) | 13 | 44KB | ✅ Pronto |
| **Docker Monitoring** | 8 | 21KB | ✅ Pronto |
| **N8N Performance Detailed** | 12 | 19KB | ⚠️ Sem datasource* |
| **N8N Node Performance** | 4 | 6.1KB | ✅ Corrigido |
| **N8N Performance Overview** | 6 | 4.0KB | ⚠️ Sem datasource* |

*Nota: Dashboards N8N precisarão de métricas específicas do N8N para funcionar completamente.

---

## 🔧 Troubleshooting

### Problema: Dashboards não aparecem

**Verificar:**
```bash
# 1. Volumes montados corretamente
docker inspect enterprise-grafana | grep -A 5 "Mounts"

# 2. Arquivos existem no container
docker exec enterprise-grafana ls -la /etc/grafana/provisioning/dashboards/
docker exec enterprise-grafana ls -la /var/lib/grafana/dashboards/

# 3. Permissões corretas
docker exec enterprise-grafana ls -ln /var/lib/grafana/dashboards/
```

**Solução:**
```bash
# Recriar container
docker-compose up -d --force-recreate grafana

# Verificar provisioning
docker exec enterprise-grafana cat /etc/grafana/provisioning/dashboards/dashboards.yaml
```

### Problema: Gráficos vazios

**Verificar datasource UID:**
```bash
# Verificar UID no dashboard
docker exec enterprise-grafana cat /var/lib/grafana/dashboards/wfdb02*.json | \
  grep -o '"uid"[[:space:]]*:[[:space:]]*"[^"]*"' | sort | uniq

# Verificar UID do datasource
curl -s -u admin:SENHA http://grafana.vya.digital/api/datasources | \
  jq '.[] | select(.type=="prometheus") | .uid'
```

**Solução:**
- Confirmar que todos usam `"prometheus"` (minúsculo)
- Se necessário, re-executar script de correção localmente

### Problema: Dashboard read-only

**Comportamento esperado:**
- Dashboards provisionados são **editáveis na UI** (`allowUiUpdates: true`)
- Mudanças não persistem após restart (arquivos são source of truth)

**Workflow recomendado:**
1. Editar dashboard na UI
2. Exportar JSON
3. Salvar no repositório Git
4. Commit e push
5. Sync para servidor

---

## 🔄 Workflow de Atualização

### Adicionar Novo Dashboard

```bash
# 1. Exportar do Grafana
curl -u admin:SENHA \
  "http://grafana.vya.digital/api/dashboards/uid/DASHBOARD_UID" | \
  jq '.dashboard' > new-dashboard.json

# 2. Adicionar ao repositório
cp new-dashboard.json wfdb01-docker-folder/grafana/dashboards/

# 3. Commit
git add wfdb01-docker-folder/grafana/dashboards/new-dashboard.json
git commit -m "feat: adicionar dashboard X"

# 4. Sync para servidor
rsync -avz wfdb01-docker-folder/grafana/dashboards/ \
  user@wfdb01:/opt/docker_user/enterprise-observability/grafana/dashboards/

# 5. Aguardar 30s (auto-refresh) ou reiniciar
ssh user@wfdb01 "cd /opt/docker_user/enterprise-observability && docker-compose restart grafana"
```

### Modificar Dashboard Existente

```bash
# 1. Editar na UI do Grafana
# 2. Exportar JSON atualizado
# 3. Sobrescrever arquivo local
# 4. Commit e sync
```

---

## 📊 Métricas e Monitoramento

### Verificar Health do Provisioning

```bash
# Prometheus metrics do Grafana
curl -s http://grafana.vya.digital:3000/metrics | \
  grep provisioning

# Expected metrics:
# grafana_provisioning_dashboard_files_total
# grafana_provisioning_datasource_total
```

### Logs de Provisioning

```bash
# Filtrar apenas provisioning
docker logs enterprise-grafana 2>&1 | grep provision

# Procurar por erros
docker logs enterprise-grafana 2>&1 | grep -i "error\|failed" | grep dashboard
```

---

## ✅ Checklist de Deploy

- [ ] **Preparação**
  - [ ] Backup do Grafana atual (`/var/lib/grafana`)
  - [ ] Documentar dashboards existentes
  - [ ] Validar datasources no servidor

- [ ] **Sync Arquivos**
  - [ ] Copiar `grafana/provisioning/dashboards/`
  - [ ] Copiar `grafana/dashboards/`
  - [ ] Atualizar `docker-compose.yaml`
  - [ ] Verificar permissões (472:472)

- [ ] **Deploy**
  - [ ] Validar docker-compose config
  - [ ] Reiniciar Grafana container
  - [ ] Aguardar 60s para startup completo
  - [ ] Verificar logs (sem erros)

- [ ] **Validação**
  - [ ] Datasource UID = "prometheus"
  - [ ] 7 dashboards listados na UI
  - [ ] Gráficos exibindo dados
  - [ ] Queries funcionando
  - [ ] Time ranges operacionais

- [ ] **Documentação**
  - [ ] Atualizar README do projeto
  - [ ] Registrar em changelog
  - [ ] Notificar equipe

---

## 📚 Referências

- [Grafana Provisioning Dashboards](https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards)
- [Grafana Dashboard JSON Model](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/view-dashboard-json-model/)
- [Docker Compose Volumes](https://docs.docker.com/compose/compose-file/compose-file-v3/#volumes)

---

## 📝 Notas Importantes

1. **SSHFS mount:**
   - Pasta `wfdb01-docker-folder` pode ser um mount SSHFS
   - Verificar conectividade antes do deploy: `mount | grep sshfs`

2. **Permissões:**
   - Grafana container usa UID 472
   - Garantir que arquivos sejam legíveis por esse UID

3. **Read-only volumes:**
   - Dashboards montados como `:ro` (read-only)
   - Protege arquivos de modificações acidentais
   - Source of truth é o repositório Git

4. **Auto-refresh:**
   - Provisioner verifica mudanças a cada 30s
   - Não necessário restart para novos dashboards
   - Deletar arquivo = remove dashboard do Grafana

---

**Próximos Passos:**
1. Executar deploy no servidor remoto
2. Validar dashboards funcionando
3. Configurar backup automatizado
4. Documentar processo para equipe

---

**Documento gerado em:** 09/02/2026 17:20
**Localização:** `/wfdb01-docker-folder/grafana/DEPLOYMENT_GUIDE.md`
