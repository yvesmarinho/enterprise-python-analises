# 🔄 SESSION RECOVERY - 03/02/2026

**Data da Sessão**: 03 de Fevereiro de 2026  
**Horário de Início**: ~14:00  
**Status**: ✅ Sessão Encerrada  
**Duração**: ~2h15min

---

## 📋 Contexto da Sessão Anterior

**Última Sessão**: 02/02/2026  
**Objetivo**: Configurar monitoramento N8N com Grafana + VictoriaMetrics

**Entregáveis da Sessão Anterior**:
- ✅ Stack Grafana 12.3.2 + VictoriaMetrics configurada
- ✅ Script Python de coleta de métricas (n8n_metrics_exporter.py)
- ✅ Dashboards criados: Performance Overview, Performance Detailed, Node Performance
- ⚠️ **Problema identificado**: Gráficos com dados duplicados e fora de ordem

---

## 🎯 Objetivos desta Sessão

1. **Corrigir problemas nos dashboards do Grafana**
   - Gráfico "Bottleneck Score vs Execution Count" difícil de entender
   - Tabelas com workflows duplicados
   - Ordenação incorreta em "All Nodes Performance"

2. **Planejar próximos passos do projeto**
   - Definir roadmap de migração da stack
   - Documentar instalação de Node Exporter
   - Preparar métricas de sistema e containers

---

## 🔍 Estado Inicial do Sistema

### Ambiente de Monitoramento
- **Grafana**: http://localhost:3100 (admin / W123Mudar)
- **VictoriaMetrics**: http://localhost:8428
- **N8N Server**: wf005.vya.digital:5678

### Dashboards Ativos
1. **N8N Performance Overview** ✅ Funcionando
2. **N8N Performance Detailed** ⚠️ Com problemas
   - Panel 11: "Bottleneck Score Ranking" - Linha gráfico difícil de ler
   - Panel 12: "Score Components" - Workflows duplicados
3. **N8N Node Performance** ⚠️ Com problemas
   - Panel 3: "All Nodes Performance" - Sem ordenação

### Problemas Conhecidos
- ❌ Gráfico de linha não adequado para ranking
- ❌ Merge de múltiplas queries Prometheus criando duplicatas
- ❌ Campo `__name__` causando rows separadas na merge
- ❌ allowUiUpdates=true permitindo UI sobrescrever arquivos JSON

---

## 📊 Métricas Coletadas (Baseline)

### Top Workflows por Bottleneck Score
```
1. sdr_agent_planejados-v2: 12.18
2. hub-whatsapp-api-validate-reseller: 4.81
3. hub-whatsapp-api-validate-client: 4.34
4. hub-whatsapp-api-gateway-evolution-api: 3.77
5. 121Labs PABX call-analytics: 0.29
```

### Nodes Mais Lentos
```
1. Select rows (setCacheReseller): 2684ms
2. Select rows (validate-client): 1764ms
3. Select rows (gateway): 1185ms
4. setCacheClient: 1143ms
```

---

## 🚀 Plano de Ação

### Prioridade Alta
- [x] Converter gráfico Bottleneck Score para tabela
- [x] Resolver problema de duplicatas no merge
- [x] Adicionar ordenação em All Nodes Performance
- [x] Configurar provisioning com allowUiUpdates=false

### Prioridade Média
- [x] Documentar próximos passos em NEXT_STEPS.md
- [ ] Testar alertas do Grafana
- [ ] Validar coleta contínua de métricas

### Prioridade Baixa
- [ ] Otimizar queries lentas no N8N
- [ ] Implementar cache Redis
- [ ] Criar dashboard de tendências

---

## 📁 Arquivos Relevantes

### Configuração
- `/n8n-tuning/docker/docker-compose.yml` - Stack de monitoramento
- `/n8n-tuning/docker/grafana/provisioning/dashboards/dashboards.yml` - Provisioning config
- `/n8n-tuning/.secrets/n8n_credentials.json` - Credenciais API

### Dashboards
- `/n8n-tuning/docker/grafana/dashboards/n8n-performance-detailed.json`
- `/n8n-tuning/docker/grafana/dashboards/n8n-node-performance.json`

### Scripts
- `/n8n-tuning/scripts/n8n_metrics_collector.py` - Coleta de métricas
- `/n8n-tuning/scripts/workflow_analyzer.py` - Análise de workflows

### Documentação
- `/n8n-tuning/docs/INDEX.md` - Índice principal
- `/n8n-tuning/docs/TODO.md` - Lista de tarefas
- `/n8n-tuning/docs/NEXT_STEPS.md` - Roadmap

---

## 🔧 Comandos Úteis

### Grafana
```bash
# Recarregar dashboards
curl -X POST -H "Content-Type: application/json" \
  -u admin:W123Mudar \
  http://localhost:3100/api/admin/provisioning/dashboards/reload

# Verificar hash de arquivo
sha256sum docker/grafana/dashboards/n8n-performance-detailed.json

# Copiar dashboard atualizado
sudo cp /tmp/dashboard.json docker/grafana/dashboards/
sudo chown 472:root docker/grafana/dashboards/dashboard.json
```

### Docker
```bash
# Verificar permissões no container
docker exec -it n8n-tuning-grafana-1 ls -lh /var/lib/grafana/dashboards/

# Logs do Grafana
docker logs n8n-tuning-grafana-1 -f --tail=100
```

### Python
```bash
# Executar coleta manual
cd /home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-tuning
python scripts/n8n_metrics_collector.py
```

---

## 📝 Notas Importantes

### Limitação do Grafana Descoberta
- **Problema**: Table panels com múltiplas instant queries do Prometheus não fazem merge corretamente quando field names diferem
- **Causa**: Query A retorna "Value", Query B retorna "n8n_workflow_executions_total", Query C retorna "n8n_workflow_execution_duration_seconds"
- **Solução**: Usar single query por panel ou split em panels separados
- **Transformations**: organize (rename) acontece APÓS merge, não resolve o problema

### Configuração de Provisioning
```yaml
allowUiUpdates: false  # Impede UI de sobrescrever JSON files
disableDeletion: true  # Impede deleção via UI
updateIntervalSeconds: 5  # Polling de arquivos
```

---

## ✅ Recovery Checklist

Ao iniciar próxima sessão, verificar:

- [ ] Grafana está rodando (localhost:3100)
- [ ] VictoriaMetrics está coletando dados
- [ ] Dashboards carregados corretamente
- [ ] Nenhum erro nos logs do Grafana
- [ ] Python collector executando no cron (a cada 3 min)
- [ ] Métricas disponíveis no endpoint /metrics do N8N
- [ ] Todos os painéis exibindo dados sem duplicatas
- [ ] Ordenação correta em tabelas

---

**Preparado por**: GitHub Copilot  
**Próxima Sessão**: A ser agendada  
**Status**: Pronto para continuação
