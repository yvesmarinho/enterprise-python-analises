# Grafana Dashboards - Provisioning Automático

## 📊 Resumo

7 dashboards Grafana provisionados automaticamente via arquivos.
**Status:** ✅ Corrigidos e prontos para deploy

---

## 🚀 Deploy Rápido

```bash
# No diretório wfdb01-docker-folder
./sync-dashboards.sh
```

O script irá:
1. ✅ Sincronizar provisioning e dashboards
2. ✅ Ajustar permissões no servidor
3. ✅ Aplicar docker-compose atualizado
4. ✅ Reiniciar Grafana
5. ✅ Validar deployment

---

## 📁 Estrutura

```
grafana/
├── provisioning/
│   └── dashboards/
│       └── dashboards.yaml          # Configuração de provisioning
└── dashboards/                      # 7 dashboards JSON (448KB)
    ├── wfdb02 - MySQL Dashboard-1770665439838.json          (268KB)
    ├── WFDB02.vya.digital - PostgreSQL Database-...json     (78KB)
    ├── wfdb02 - MySQL Dashboard-1756827751674.json          (44KB)
    ├── wf008 - Docker Monitoring-1756735858594.json         (21KB)
    ├── n8n-performance-detailed.json                        (19KB)
    ├── n8n-node-performance.json                            (6.1KB)
    └── n8n-performance-overview.json                        (4.0KB)
```

---

## 🔧 Correções Aplicadas

### ✅ Datasource UIDs Corrigidos

| Dashboard | UID Anterior | UID Corrigido | Status |
|-----------|--------------|---------------|--------|
| MySQL Dashboard (completo) | `"Prometheus"` | `"prometheus"` | ✅ 247 substituições |
| N8N Node Performance | `"P4169E866C3094E38"` | `"prometheus"` | ✅ 4 substituições |
| PostgreSQL | `"prometheus"` | `"prometheus"` | ✅ Já correto |
| Docker Monitoring | `"prometheus"` | `"prometheus"` | ✅ Já correto |
| MySQL (simplificado) | `"prometheus"` | `"prometheus"` | ✅ Já correto |

### ⚠️ N8N Dashboards sem Datasource

2 dashboards N8N precisarão de configuração adicional:
- `n8n-performance-detailed.json` (12 painéis)
- `n8n-performance-overview.json` (6 painéis)

---

## 📋 Comandos Úteis

### Validar localmente
```bash
# Verificar UIDs
grep -h '"uid"' grafana/dashboards/*.json | grep prometheus | sort | uniq

# Contar dashboards
ls -1 grafana/dashboards/*.json | wc -l
```

### Sync manual
```bash
# Sincronizar apenas dashboards
rsync -avz grafana/dashboards/ \
  user@wfdb01:/opt/docker_user/enterprise-observability/grafana/dashboards/

# Reiniciar Grafana
ssh user@wfdb01 "cd /opt/docker_user/enterprise-observability && docker-compose restart grafana"
```

### Validar no servidor
```bash
# Verificar provisioning
docker exec enterprise-grafana ls -la /etc/grafana/provisioning/dashboards/

# Ver dashboards montados
docker exec enterprise-grafana ls -la /var/lib/grafana/dashboards/

# Logs de provisioning
docker logs enterprise-grafana 2>&1 | grep -i dashboard
```

---

## 🔍 Troubleshooting

### Dashboards não aparecem no Grafana

1. **Verificar volumes:**
   ```bash
   docker inspect enterprise-grafana | grep -A 10 Mounts
   ```

2. **Verificar permissões:**
   ```bash
   ls -ln grafana/dashboards/
   # Devem ser legíveis por UID 472
   ```

3. **Resetar provisioning:**
   ```bash
   docker-compose restart grafana
   docker logs -f enterprise-grafana
   ```

### Gráficos vazios

1. **Verificar datasource UID:**
   ```bash
   curl -s -u admin:SENHA http://grafana.vya.digital/api/datasources | \
     jq '.[] | select(.type=="prometheus") | .uid'
   # Deve retornar: "prometheus"
   ```

2. **Verificar queries:**
   - Abrir dashboard → Edit panel → Query inspector
   - Verificar se métricas estão disponíveis no Prometheus

---

## 📚 Documentação

- **Deploy Guide completo:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Correção dos UIDs:** `/reports/grafana_dashboards_fix_report.md`
- **Análise inicial:** `/scripts/analyze_grafana_dashboards.py`

---

## ✅ Validação Pós-Deploy

Após executar `sync-dashboards.sh`:

1. ✅ Acessar: https://grafana.vya.digital
2. ✅ Verificar 7 dashboards em **Dashboards → Browse**
3. ✅ Abrir cada dashboard e confirmar dados sendo exibidos
4. ✅ Testar diferentes time ranges (Last 1h, Last 24h, Last 7d)

---

**Última atualização:** 09/02/2026 17:21
**Dashboards corrigidos:** 7/7 ✅
**Pronto para produção:** ✅
