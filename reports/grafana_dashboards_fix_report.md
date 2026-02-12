# Relatório de Correção - Dashboards Grafana
**Data:** 09/02/2026
**Sessão:** 2026-02-09
**Analista:** enterprise-python-analysis

---

## 🔍 Diagnóstico: Problema dos Dashboards

### ❌ Problema Identificado
Os dashboards do Grafana **não exibem dados** porque estão configurados com datasource UIDs **incorretos** que não correspondem ao datasource real provisionado no Grafana.

### 🎯 Causa Raiz

#### 1. **Configuração Real do Datasource**
Arquivo: `n8n-prometheus-wfdb01/infrastructure/grafana/provisioning/datasources/victoria-metrics.yml`

```yaml
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
```

**Características:**
- ✅ Nome: `VictoriaMetrics`
- ✅ Tipo: `prometheus`
- ✅ Default: Sim
- ❌ UID: **NÃO DEFINIDO** (Grafana gera automaticamente)

#### 2. **UIDs Encontrados nos Dashboards**

| UID | Dashboards | Status |
|-----|------------|--------|
| `"prometheus"` | 3 dashboards | ❌ Não existe |
| `"Prometheus"` | 1 dashboard | ❌ Não existe |
| `"P4169E866C3094E38"` | 1 dashboard | ❌ Não existe |
| **Sem UID** | 2 dashboards | ❌ Sem datasource |

---

## 📊 Análise Detalhada dos Dashboards

### ✅ Dashboards Operacionais (3)
1. **WFDB02.vya.digital - PostgreSQL Database**
   - UID do DS: `"prometheus"` (minúsculo)
   - 32 painéis com queries

2. **wf008 - Docker Monitoring**
   - UID do DS: `"prometheus"` (minúsculo)
   - 8 painéis com queries

3. **wfdb02 - MySQL Dashboard** (versão 1756827751674)
   - UID do DS: `"prometheus"` (minúsculo)
   - 13 painéis com queries

### ⚠️ Dashboards com Problemas (4)

1. **wfdb02 - MySQL Dashboard** (versão 1770665439838)
   - ❌ UID do DS: `"Prometheus"` (**maiúsculo** - diferente!)
   - 94 painéis com queries
   - **Problema:** Case-sensitive mismatch

2. **N8N Node Performance Analysis**
   - ❌ UID do DS: `"P4169E866C3094E38"` (UID aleatório)
   - 4 painéis com queries
   - **Problema:** UID de outro ambiente

3. **N8N Performance Analysis**
   - ❌ **SEM DATASOURCE CONFIGURADO**
   - 12 painéis com queries
   - **Problema:** Datasource não definido

4. **N8N Performance Overview**
   - ❌ **SEM DATASOURCE CONFIGURADO**
   - 6 painéis com queries
   - **Problema:** Datasource não definido

---

## 🔧 Soluções Propostas

### Solução 1: Definir UID Explícito no Datasource (RECOMENDADO)

#### Vantagens:
✅ Controle total sobre o UID
✅ Portabilidade entre ambientes
✅ Evita problemas com UIDs gerados automaticamente
✅ Facilita manutenção

#### Implementação:

1. **Atualizar o arquivo de datasource:**

```yaml
apiVersion: 1

datasources:
  - name: VictoriaMetrics
    type: prometheus
    uid: prometheus  # UID EXPLÍCITO
    access: proxy
    url: http://victoria-metrics:8428
    isDefault: true
    editable: false
    jsonData:
      httpMethod: POST
      timeInterval: 30s
```

2. **Reiniciar o Grafana:**
```bash
cd n8n-prometheus-wfdb01
docker-compose restart grafana
```

3. **Corrigir os dashboards:**
- Padronizar todos os UIDs para `"prometheus"` (minúsculo)
- Usar o script `fix_dashboard_datasources.py`

---

### Solução 2: Descobrir UID Atual e Atualizar Dashboards

#### Vantagens:
✅ Não requer reinicialização do Grafana
✅ Mantém configuração atual

#### Desvantagens:
❌ UID pode mudar se recriar datasource
❌ Menos controle

#### Implementação:

1. **Descobrir o UID atual via API:**
```bash
curl -u admin:admin http://grafana.vya.digital/api/datasources | jq '.[] | select(.name=="VictoriaMetrics") | .uid'
```

2. **Atualizar todos os dashboards com o UID descoberto**

---

## 🚀 Plano de Ação Recomendado

### Fase 1: Preparação (5 min)
- [ ] 1.1. Backup dos dashboards atuais
- [ ] 1.2. Validar acesso ao Grafana
- [ ] 1.3. Verificar UID atual do datasource

### Fase 2: Correção do Datasource (10 min)
- [ ] 2.1. Atualizar `victoria-metrics.yml` com UID explícito
- [ ] 2.2. Reiniciar Grafana container
- [ ] 2.3. Validar datasource no Grafana UI
- [ ] 2.4. Confirmar UID via API

### Fase 3: Correção dos Dashboards (15 min)
- [ ] 3.1. Executar script de correção automática
- [ ] 3.2. Validar dashboards corrigidos
- [ ] 3.3. Testar visualização de dados
- [ ] 3.4. Importar dashboards atualizados no Grafana

### Fase 4: Validação (10 min)
- [ ] 4.1. Abrir cada dashboard
- [ ] 4.2. Verificar dados sendo exibidos
- [ ] 4.3. Testar diferentes time ranges
- [ ] 4.4. Documentar problemas remanescentes

---

## 📝 Comandos Úteis

### Verificar UID do Datasource
```bash
# Via API Grafana
curl -s -u admin:admin http://grafana.vya.digital/api/datasources | jq '.[] | {name, uid, type}'

# Via Docker exec
docker exec dev-grafana cat /etc/grafana/provisioning/datasources/victoria-metrics.yml
```

### Reiniciar Grafana
```bash
cd n8n-prometheus-wfdb01
docker-compose restart grafana

# Verificar logs
docker logs dev-grafana -f --tail=50
```

### Backup de Dashboards
```bash
# Criar backup
cd n8n-prometheus-wfdb01/grafana_data/dashboards
tar -czf dashboards-backup-$(date +%Y%m%d-%H%M%S).tar.gz *.json

# Listar backups
ls -lh dashboards-backup-*.tar.gz
```

### Validar JSON dos Dashboards
```bash
# Verificar sintaxe JSON
for file in *.json; do
    echo "Validando: $file"
    jq empty "$file" && echo "✅ OK" || echo "❌ ERRO"
done
```

---

## 🎯 Resultado Esperado

Após aplicar as correções:

✅ **Datasource configurado com UID fixo:** `prometheus`
✅ **Todos os dashboards apontando para o mesmo UID**
✅ **Grafana exibindo métricas do VictoriaMetrics**
✅ **Gráficos populados com dados históricos**
✅ **Sistema monitorável e operacional**

---

## 📚 Referências

- [Grafana Provisioning Datasources](https://grafana.com/docs/grafana/latest/administration/provisioning/#datasources)
- [VictoriaMetrics as Prometheus Datasource](https://docs.victoriametrics.com/guides/grafana/)
- [Grafana HTTP API - Datasources](https://grafana.com/docs/grafana/latest/developers/http_api/data_source/)

---

## 📌 Próximos Passos

1. **Curto Prazo:**
   - Aplicar correções nos dashboards
   - Validar exibição de dados
   - Documentar UID padrão

2. **Médio Prazo:**
   - Criar template de dashboard com datasource correto
   - Padronizar nomenclatura de dashboards
   - Implementar CI/CD para validação de dashboards

3. **Longo Prazo:**
   - Automatizar provisionamento de dashboards
   - Implementar versionamento de dashboards
   - Criar biblioteca de dashboards reutilizáveis

---

**Documento gerado em:** 09/02/2026 16:50
**Localização:** `/reports/grafana_dashboards_fix_report.md`
