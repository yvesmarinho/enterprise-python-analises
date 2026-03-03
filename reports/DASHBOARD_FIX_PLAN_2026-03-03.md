# 📋 PLANO DE CORREÇÃO - Dashboards Grafana
**Data**: 03/03/2026
**Prioridade**: 🔴 CRÍTICA
**Tempo Estimado**: 2-3 horas
**Responsável**: DevOps Team

---

## 🎯 OBJETIVO

Corrigir todos os dashboards N8N não funcionais configurando datasources corretos em todos os painéis.

---

## 📊 RESUMO DO PLANO

- ✅ **Fase 1**: Preparação e Backup (15 min)
- ⏳ **Fase 2**: Corrigir Datasource Provisioning (10 min)
- ⏳ **Fase 3**: Corrigir Dashboards N8N (60 min)
- ⏳ **Fase 4**: Organizar Arquivos Duplicados (20 min)
- ⏳ **Fase 5**: Deploy e Validação (30 min)
- ⏳ **Fase 6**: Documentação Final (15 min)

**Total**: ~2h 30min

---

## 🔥 FASE 1: PREPARAÇÃO E BACKUP (15 min)

### 1.1 Criar Backup dos Dashboards Atuais
- [ ] Criar pasta de backup datada
```bash
mkdir -p n8n-prometheus-wfdb01/grafana/dashboards-backup-2026-03-03
cp -r n8n-prometheus-wfdb01/grafana/dashboards/*.json \
  n8n-prometheus-wfdb01/grafana/dashboards-backup-2026-03-03/
```

- [ ] Criar backup dos dashboards em grafana_data
```bash
mkdir -p n8n-prometheus-wfdb01/grafana_data/dashboards-backup-2026-03-03
cp -r n8n-prometheus-wfdb01/grafana_data/dashboards/*.json \
  n8n-prometheus-wfdb01/grafana_data/dashboards-backup-2026-03-03/
```

- [ ] Verificar backups criados
```bash
ls -lh n8n-prometheus-wfdb01/grafana/dashboards-backup-2026-03-03/
ls -lh n8n-prometheus-wfdb01/grafana_data/dashboards-backup-2026-03-03/
```

### 1.2 Criar Pasta de Trabalho
- [ ] Criar estrutura para dashboards corrigidos
```bash
mkdir -p reports/dashboard-fixes/2026-03-03/{before,after}
```

---

## 🔑 FASE 2: CORRIGIR DATASOURCE PROVISIONING (10 min)

### 2.1 Adicionar UID Explícito ao Datasource

**Arquivo**: `n8n-prometheus-wfdb01/infrastructure/grafana/provisioning/datasources/victoria-metrics.yml`

**Mudança**:
```yaml
# ANTES:
datasources:
  - name: VictoriaMetrics
    type: prometheus
    access: proxy
    url: http://victoria-metrics:8428
    isDefault: true
    editable: false

# DEPOIS:
datasources:
  - name: VictoriaMetrics
    type: prometheus
    access: proxy
    url: http://victoria-metrics:8428
    uid: prometheus           # ✅ ADICIONAR
    isDefault: true
    editable: false
```

**Tarefas**:
- [ ] Editar arquivo datasource YAML
- [ ] Adicionar linha `uid: prometheus`
- [ ] Validar sintaxe YAML
- [ ] Commit da mudança

### 2.2 Criar Datasource Alternativo (Opcional)
- [ ] Considerar criar datasource `victoriametrics` como alias
- [ ] Avaliar necessidade de múltiplos datasources

---

## 🔧 FASE 3: CORRIGIR DASHBOARDS N8N (60 min)

### 3.1 Criar Script de Correção Automatizada

**Arquivo**: `scripts/fix_n8n_dashboards.py`

- [ ] Criar script Python para:
  - Ler todos os dashboards N8N
  - Identificar painéis sem datasource
  - Adicionar datasource `{"type": "prometheus", "uid": "prometheus"}`
  - Salvar dashboards corrigidos
  - Gerar relatório de mudanças

**Script Base**:
```python
import json
from pathlib import Path

def fix_dashboard(dashboard_path):
    with open(dashboard_path, 'r') as f:
        data = json.load(f)

    datasource = {
        "type": "prometheus",
        "uid": "prometheus"
    }

    fixed_count = 0
    for panel in data.get('panels', []):
        if panel.get('type') == 'row':
            continue
        if 'datasource' not in panel or not panel['datasource']:
            panel['datasource'] = datasource
            fixed_count += 1

    # Salvar dashboard corrigido
    with open(dashboard_path, 'w') as f:
        json.dump(data, f, indent=2)

    return fixed_count
```

### 3.2 Corrigir Dashboard: N8N Performance Overview

**Arquivo**: `n8n-prometheus-wfdb01/grafana/dashboards/n8n-performance-overview.json`

- [ ] Executar script de correção
- [ ] Verificar 6 painéis corrigidos:
  - [ ] Total Executions
  - [ ] Success Rate
  - [ ] Total Workflows
  - [ ] Active Workflows
  - [ ] Execution Duration
  - [ ] Error Rate

- [ ] Validar JSON sintaxe
- [ ] Testar import no Grafana (opcional)

### 3.3 Corrigir Dashboard: N8N Performance Detailed

**Arquivo**: `n8n-prometheus-wfdb01/grafana/dashboards/n8n-performance-detailed.json`

- [ ] Executar script de correção
- [ ] Verificar 12 painéis corrigidos:
  - [ ] Total Workflows
  - [ ] Active Workflows
  - [ ] Success Rate
  - [ ] Avg Execution Duration
  - [ ] Node Executions
  - [ ] Workflow Executions Timeline
  - [ ] API Requests
  - [ ] API Response Time
  - [ ] API Error Rate
  - [ ] Top Failing Workflows
  - [ ] Slowest Workflows
  - [ ] Error Distribution

- [ ] Validar JSON sintaxe

### 3.4 Corrigir Dashboard: N8N Node Performance

**Arquivo**: `n8n-prometheus-wfdb01/grafana/dashboards/n8n-node-performance.json`

- [ ] Executar script de correção
- [ ] Verificar 3 painéis corrigidos:
  - [ ] Top 20 Slowest Nodes (Average Time)
  - [ ] Average Time by Node Type (milliseconds)
  - [ ] All Nodes Performance

- [ ] Validar JSON sintaxe

### 3.5 Corrigir UID Incorreto

**Arquivo**: `n8n-tuning/docker/grafana/dashboards/n8n-node-performance.json`

- [ ] Buscar referências a UID `P4169E866C3094E38`
- [ ] Substituir por `prometheus`
```bash
sed -i 's/"P4169E866C3094E38"/"prometheus"/g' \
  n8n-tuning/docker/grafana/dashboards/n8n-node-performance.json
```

### 3.6 Verificação Geral
- [ ] Executar script de análise novamente
- [ ] Confirmar 0 painéis sem datasource
- [ ] Confirmar todos UIDs = `prometheus`

---

## 📁 FASE 4: ORGANIZAR ARQUIVOS DUPLICADOS (20 min)

### 4.1 Definir Localização Canônica

**Decisão**: Usar `n8n-prometheus-wfdb01/grafana/dashboards/` como fonte única

### 4.2 Organizar por Pastas

- [ ] Criar estrutura de pastas
```bash
cd n8n-prometheus-wfdb01/grafana/dashboards
mkdir -p N8N MySQL PostgreSQL Docker
```

- [ ] Mover dashboards para pastas corretas
```bash
# N8N
mv n8n-*.json N8N/

# MySQL
mv *MySQL*.json MySQL/

# PostgreSQL
mv *PostgreSQL*.json PostgreSQL/

# Docker
mv *Docker*.json Docker/
```

### 4.3 Remover Duplicatas

- [ ] Comparar arquivos entre localizações
```bash
diff n8n-prometheus-wfdb01/grafana/dashboards/N8N/n8n-performance-overview.json \
     n8n-prometheus-wfdb01/grafana_data/dashboards/n8n-performance-overview.json
```

- [ ] Deletar duplicatas antigas em `grafana_data/dashboards/`
- [ ] Deletar duplicatas antigas em `n8n-tuning/docker/grafana/dashboards/`

### 4.4 Criar Symlinks (Opcional)
- [ ] Avaliar necessidade de symlinks para compatibilidade

---

## 🚀 FASE 5: DEPLOY E VALIDAÇÃO (30 min)

### 5.1 Deploy Local (Desenvolvimento)

- [ ] Parar Grafana local (se rodando)
```bash
docker-compose -f n8n-prometheus-wfdb01/docker-compose.yml down grafana
```

- [ ] Atualizar volumes para apontar aos dashboards corrigidos
- [ ] Subir Grafana
```bash
docker-compose -f n8n-prometheus-wfdb01/docker-compose.yml up -d grafana
```

- [ ] Aguardar inicialização (30 segundos)

### 5.2 Validação Local

- [ ] Acessar Grafana: http://localhost:3000
- [ ] Verificar datasource VictoriaMetrics com UID `prometheus`
- [ ] Abrir cada dashboard N8N:
  - [ ] N8N Performance Overview
  - [ ] N8N Performance Detailed
  - [ ] N8N Node Performance

- [ ] Verificar painéis:
  - [ ] Sem mensagens de erro "Datasource not found"
  - [ ] Queries carregando (pode não ter dados ainda)
  - [ ] Ícones de datasource corretos

### 5.3 Deploy Produção (wf001.vya.digital)

- [ ] Conectar ao servidor: `ssh-wf001`
- [ ] Navegar para diretório do projeto
- [ ] Fazer backup dos dashboards atuais
```bash
cd /opt/docker_user/enterprise-observability
cp -r grafana/dashboards grafana/dashboards-backup-$(date +%Y%m%d)
```

- [ ] Copiar dashboards corrigidos
```bash
# Do computador local:
scp -r n8n-prometheus-wfdb01/grafana/dashboards/* \
  wf001:/opt/docker_user/enterprise-observability/grafana/dashboards/
```

- [ ] Copiar datasource atualizado
```bash
scp n8n-prometheus-wfdb01/infrastructure/grafana/provisioning/datasources/victoria-metrics.yml \
  wf001:/opt/docker_user/enterprise-observability/grafana/provisioning/datasources/
```

- [ ] Restart Grafana
```bash
docker restart enterprise-grafana
```

- [ ] Aguardar inicialização (30 segundos)

### 5.4 Validação Produção

- [ ] Acessar Grafana: https://grafana.vya.digital
- [ ] Login com credenciais
- [ ] Verificar datasource:
  - Nome: VictoriaMetrics
  - UID: prometheus
  - Status: ✅ Working

- [ ] Verificar estrutura de pastas:
  - [ ] Pasta N8N/ visível
  - [ ] Pasta MySQL/ visível
  - [ ] Pasta PostgreSQL/ visível
  - [ ] Pasta Docker/ visível

- [ ] Abrir dashboards N8N:
  - [ ] Verificar painéis sem erros
  - [ ] Verificar dados populando (se métricas existirem)
  - [ ] Screenshot de cada dashboard

- [ ] Verificar dashboards existentes (MySQL, PostgreSQL, Docker):
  - [ ] Ainda funcionais
  - [ ] Sem regressões

---

## 📝 FASE 6: DOCUMENTAÇÃO FINAL (15 min)

### 6.1 Atualizar Documentação do Projeto

- [ ] Atualizar `n8n-prometheus-wfdb01/grafana/README.md`
  - Adicionar seção sobre estrutura de pastas
  - Documentar UID padrão: `prometheus`
  - Adicionar troubleshooting

- [ ] Atualizar `.docs/INDEX.md`
  - Status: Dashboards corrigidos (100% funcionais)
  - Data de correção: 03/03/2026

- [ ] Atualizar `.docs/TODO.md`
  - Marcar tarefas como concluídas
  - Remover item "Corrigir dashboards Grafana"

### 6.2 Criar Relatório Final

**Arquivo**: `reports/DASHBOARD_FIX_FINAL_REPORT_2026-03-03.md`

Incluir:
- [ ] Resumo executivo
- [ ] Problemas encontrados
- [ ] Soluções aplicadas
- [ ] Resultados de validação
- [ ] Screenshots (antes/depois)
- [ ] Métricas:
  - Painéis corrigidos: 21
  - Dashboards corrigidos: 3
  - Taxa de sucesso: 100%
  - Tempo total: X horas

### 6.3 Atualizar Session Activities

**Arquivo**: `.docs/sessions/2026-03-03/TODAY_ACTIVITIES_2026-03-03.md`

- [ ] Adicionar seção "Correção de Dashboards"
- [ ] Listar todas as tarefas realizadas
- [ ] Documentar problemas encontrados e resolvidos

### 6.4 Commit e Push

- [ ] Git add todos os arquivos modificados
- [ ] Commit com mensagem descritiva:
  ```
  fix(grafana): corrigir dashboards N8N e datasource UID

  - Adicionar UID explícito ao datasource VictoriaMetrics
  - Corrigir 21 painéis N8N sem datasource configurado
  - Organizar dashboards em pastas (N8N/, MySQL/, PostgreSQL/, Docker/)
  - Remover dashboards duplicados
  - Atualizar documentação

  Fixes: Dashboards N8N não exibiam dados
  ```

- [ ] Push para repositório
- [ ] Criar tag de release (opcional): `v1.1.0-grafana-fix`

---

## ⚠️ ROLLBACK PLAN (Caso algo dê errado)

### Rollback Local
```bash
# Restaurar dashboards originais
cp -r n8n-prometheus-wfdb01/grafana/dashboards-backup-2026-03-03/* \
     n8n-prometheus-wfdb01/grafana/dashboards/

# Restart Grafana
docker-compose restart grafana
```

### Rollback Produção
```bash
# No servidor wf001
cd /opt/docker_user/enterprise-observability
rm -rf grafana/dashboards/*
cp -r grafana/dashboards-backup-$(date +%Y%m%d)/* grafana/dashboards/
docker restart enterprise-grafana
```

---

## 📊 CHECKLIST FINAL

### Pré-Deploy
- [ ] Backups criados
- [ ] Script de correção testado
- [ ] Dashboards corrigidos validados localmente
- [ ] Documentação atualizada

### Deploy
- [ ] Datasource UID atualizado
- [ ] Dashboards copiados para produção
- [ ] Grafana reiniciado
- [ ] Validação em produção realizada

### Pós-Deploy
- [ ] Todos os dashboards funcionando
- [ ] Métricas N8N visíveis (se disponíveis)
- [ ] Sem regressões em dashboards existentes
- [ ] Relatório final criado
- [ ] Commit e push realizados

---

## 🎯 CRITÉRIOS DE SUCESSO

### Objetivos Alcançados
- ✅ 0 painéis sem datasource
- ✅ 100% dashboards N8N funcionais
- ✅ Datasource com UID explícito
- ✅ Estrutura de pastas organizada
- ✅ Duplicatas removidas
- ✅ Documentação atualizada

### Métricas
- **Painéis corrigidos**: 21
- **Dashboards corrigidos**: 3
- **Taxa de sucesso**: 100%
- **Downtime**: 0 (dashboards já estavam quebrados)

---

## 📞 SUPORTE

Em caso de problemas:
1. Verificar logs do Grafana: `docker logs enterprise-grafana`
2. Verificar datasource status no UI do Grafana
3. Validar sintaxe JSON dos dashboards
4. Executar rollback se necessário
5. Consultar documentação: `n8n-prometheus-wfdb01/grafana/README.md`

---

**Plano criado**: 03/03/2026
**Versão**: 1.0
**Próxima revisão**: Após deploy em produção
