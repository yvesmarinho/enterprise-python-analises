# 🚀 GUIA COMPLETO DE DEPLOY - N8N Performance Monitoring

**Data**: 05/02/2026  
**Objetivo**: Deploy do sistema de monitoramento N8N para servidor de produção  
**Ambiente**: Grafana + VictoriaMetrics + Python Collectors

---

## 📋 Visão Geral

Este guia documenta o processo completo para fazer o deploy do sistema de monitoramento N8N do ambiente de desenvolvimento para o servidor de produção, mantendo todas as configurações do Grafana e garantindo a acuracidade dos dados.

---

## 🎯 Checklist Rápido

- [ ] Copiar arquivos do projeto para o servidor
- [ ] Configurar credenciais (.secrets)
- [ ] Subir containers Docker (Grafana + VictoriaMetrics)
- [ ] Instalar dependências Python
- [ ] Configurar cron jobs
- [ ] Validar coleta de métricas
- [ ] Verificar dashboards no Grafana
- [ ] Monitorar por 1 hora

---

## 📦 1. ARQUIVOS A COPIAR

### 1.1. Estrutura Completa

Copiar a pasta `n8n-tuning/` completa para o servidor:

```bash
# No seu ambiente LOCAL (desenvolvimento)
cd /home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/

# Criar arquivo tar.gz com tudo que precisa
tar -czf n8n-tuning-deploy.tar.gz \
  n8n-tuning/docker/ \
  n8n-tuning/scripts/ \
  n8n-tuning/pyproject.toml \
  n8n-tuning/.python-version \
  n8n-tuning/README.md \
  n8n-tuning/docs/
```

### 1.2. Arquivos Essenciais

| Arquivo/Pasta | Descrição | Obrigatório |
|---------------|-----------|-------------|
| `docker/docker-compose.yml` | Configuração dos containers | ✅ Sim |
| `docker/grafana/provisioning/` | Provisioning do Grafana | ✅ Sim |
| `docker/grafana/dashboards/` | Dashboards (3 arquivos JSON) | ✅ Sim |
| `scripts/*.py` | Scripts Python de coleta | ✅ Sim |
| `scripts/*.sh` | Scripts Shell para cron | ✅ Sim |
| `pyproject.toml` | Dependências Python | ✅ Sim |
| `.python-version` | Versão do Python | ✅ Sim |
| `.secrets/` | Credenciais (criar no servidor) | ✅ Sim |

---

## 🖥️ 2. PREPARAÇÃO DO SERVIDOR

### 2.1. Requisitos

```bash
# Verificar requisitos no servidor
docker --version        # Docker 20.10+
docker-compose --version # Docker Compose 2.0+
python3 --version       # Python 3.10+
```

### 2.2. Copiar Arquivos para o Servidor

```bash
# Do seu computador LOCAL
scp n8n-tuning-deploy.tar.gz user@servidor:/opt/

# No SERVIDOR
ssh user@servidor
cd /opt/
tar -xzf n8n-tuning-deploy.tar.gz
cd n8n-tuning/
```

### 2.3. Criar Estrutura de Pastas

```bash
# No SERVIDOR
mkdir -p .secrets
mkdir -p data/{metrics,logs,workflows,database}
mkdir -p logs
```

---

## 🔐 3. CONFIGURAR CREDENCIAIS

### 3.1. Criar Arquivo de Credenciais

```bash
# No SERVIDOR
nano .secrets/credentials.json
```

### 3.2. Template de Credenciais

Cole o seguinte conteúdo (ajuste com suas credenciais reais):

```json
{
  "n8n": {
    "url": "http://wf005.vya.digital:5678",
    "api_key": "SUA_API_KEY_AQUI"
  },
  "postgresql": {
    "host": "wf005.vya.digital",
    "port": 5432,
    "database": "n8n",
    "user": "n8n",
    "password": "SUA_SENHA_POSTGRES_AQUI"
  },
  "victoria_metrics": {
    "url": "http://localhost:8428"
  }
}
```

### 3.3. Proteger Arquivo

```bash
chmod 600 .secrets/credentials.json
```

### 3.4. Adicionar ao .gitignore

```bash
# Verificar se .gitignore está correto
cat > .secrets/.gitignore <<EOF
*.json
*.key
*.pem
EOF
```

---

## 🐳 4. DEPLOY DOS CONTAINERS DOCKER

### 4.1. Configurar Docker Compose

O arquivo `docker/docker-compose.yml` já está configurado com:

- **VictoriaMetrics**: Porta 8428, retenção 90 dias
- **Grafana**: Porta 3100, senha admin: `W123Mudar`
- **Volumes persistentes**: grafana-data, victoria-metrics-data
- **Health checks**: Ambos os serviços

### 4.2. Ajustar Portas (se necessário)

Se as portas 8428 ou 3100 estiverem em uso, edite:

```bash
nano docker/docker-compose.yml

# Mudar:
#   - "3100:3000"  # Para outra porta
#   - "8428:8428"  # Para outra porta
```

### 4.3. Subir os Containers

```bash
# No SERVIDOR
cd /opt/n8n-tuning/docker/

# Subir containers
docker-compose up -d

# Verificar logs
docker-compose logs -f
```

### 4.4. Validar Containers

```bash
# Verificar containers rodando
docker ps | grep n8n

# Deve mostrar:
# - n8n-victoria-metrics
# - n8n-grafana

# Testar health checks
curl http://localhost:8428/health    # VictoriaMetrics
curl http://localhost:3100/api/health # Grafana
```

---

## 🐍 5. INSTALAR DEPENDÊNCIAS PYTHON

### 5.1. Criar Ambiente Virtual

```bash
# No SERVIDOR
cd /opt/n8n-tuning/

# Criar venv
python3 -m venv .venv

# Ativar venv
source .venv/bin/activate

# Verificar pip
pip --version
```

### 5.2. Instalar Dependências

```bash
# Instalar uv (gerenciador de pacotes)
pip install uv

# Instalar dependências do projeto
uv pip install -e .

# OU manualmente:
pip install requests psycopg2-binary

# Verificar instalação
python -c "import requests, psycopg2; print('✅ OK')"
```

---

## ⏰ 6. CONFIGURAR CRON JOBS

### 6.1. Ajustar Caminhos nos Scripts

```bash
# Editar script de cron
nano scripts/cron_executions.sh

# Ajustar as variáveis:
PROJECT_DIR="/opt/n8n-tuning"
PYTHON_VENV="/opt/n8n-tuning/.venv/bin/python"
```

### 6.2. Testar Scripts Manualmente

```bash
# No SERVIDOR (com venv ativado)
cd /opt/n8n-tuning/

# Testar exporter principal
python scripts/n8n_metrics_exporter.py

# Deve mostrar:
# ✅ N8N URL: http://wf005.vya.digital:5678
# 📊 Coletando workflows...
# ✅ X workflows coletados
# 📊 Coletando execuções...
# ✅ X execuções coletadas
# 📤 Exportando métricas para VictoriaMetrics...
# ✅ X métricas exportadas com sucesso

# Testar exporter de nodes
python scripts/n8n_node_metrics_exporter.py

# Deve mostrar:
# 🔌 Conectando ao PostgreSQL...
# ✅ Conectado ao banco de dados
# 📊 Coletando execuções das últimas 24h...
# ✅ X execuções encontradas
# 📤 Exportando métricas para VictoriaMetrics...
# ✅ X métricas de nodes exportadas
```

### 6.3. Dar Permissão de Execução

```bash
chmod +x scripts/cron_executions.sh
chmod +x scripts/cron_node_metrics.sh
```

### 6.4. Instalar Cron Job

```bash
# Editar crontab
crontab -e

# Adicionar (coleta a cada 3 minutos):
*/3 * * * * /opt/n8n-tuning/scripts/cron_executions.sh >> /opt/n8n-tuning/logs/cron.log 2>&1

# Salvar e sair
```

### 6.5. Verificar Cron Instalado

```bash
# Listar cron jobs
crontab -l

# Aguardar 3 minutos e verificar logs
tail -f /opt/n8n-tuning/logs/cron.log
```

---

## ✅ 7. VALIDAÇÃO DA INSTALAÇÃO

### 7.1. Verificar VictoriaMetrics

```bash
# Verificar se VictoriaMetrics está recebendo dados
curl -s 'http://localhost:8428/api/v1/labels' | jq '.'

# Deve retornar lista de labels/métricas
```

### 7.2. Acessar Grafana

```bash
# No navegador:
http://SERVIDOR_IP:3100

# Login:
#   Usuário: admin
#   Senha: W123Mudar
```

### 7.3. Verificar Datasource

1. No Grafana, ir em **Configuration** → **Data Sources**
2. Verificar **VictoriaMetrics** está:
   - ✅ Status: Working
   - ✅ URL: http://victoria-metrics:8428

### 7.4. Verificar Dashboards

Os 3 dashboards devem estar disponíveis em **Dashboards** → **N8N Performance**:

1. **N8N Performance Overview** ✅
   - Gráficos de workflows ativos/inativos
   - Execuções por status
   - Taxa de sucesso

2. **N8N Performance Detailed** ✅
   - Tabela de Bottleneck Score Ranking (Top 15)
   - Gráficos de score components
   - Tempo médio de execução

3. **N8N Node Performance** ✅
   - Tabela de All Nodes Performance
   - Nodes mais lentos
   - Distribuição de tempo por node

### 7.5. Verificar Dados nos Dashboards

**IMPORTANTE**: Aguarde 3-5 minutos após o primeiro cron para ver dados.

```bash
# Forçar execução imediata (para não esperar cron)
cd /opt/n8n-tuning/
./scripts/cron_executions.sh

# Aguardar 30 segundos e verificar VictoriaMetrics
curl -s 'http://localhost:8428/api/v1/query?query=n8n_workflow_count' | jq '.'
```

---

## 🔍 8. TROUBLESHOOTING

### 8.1. Containers Não Sobem

```bash
# Ver logs
docker-compose logs victoria-metrics
docker-compose logs grafana

# Verificar conflito de portas
netstat -tlnp | grep -E '8428|3100'

# Recriar containers
docker-compose down -v
docker-compose up -d
```

### 8.2. Grafana Sem Dashboards

```bash
# Verificar permissões
ls -la docker/grafana/dashboards/
ls -la docker/grafana/provisioning/

# Verificar logs do Grafana
docker logs n8n-grafana | grep -i dashboard

# Forçar reload de dashboards
docker restart n8n-grafana
```

### 8.3. VictoriaMetrics Sem Dados

```bash
# Verificar se scripts estão rodando
ps aux | grep n8n_metrics_exporter

# Testar conexão com N8N
curl -H "X-N8N-API-KEY: SUA_KEY" http://wf005.vya.digital:5678/api/v1/workflows

# Verificar logs do script
tail -f /opt/n8n-tuning/logs/cron.log

# Executar manualmente com verbose
cd /opt/n8n-tuning/
source .venv/bin/activate
python -u scripts/n8n_metrics_exporter.py
```

### 8.4. Credenciais Inválidas

```bash
# Verificar formato do JSON
cat .secrets/credentials.json | jq '.'

# Testar conexão PostgreSQL
psql -h wf005.vya.digital -U n8n -d n8n -c "SELECT COUNT(*) FROM execution_entity;"

# Testar API do N8N
curl -H "X-N8N-API-KEY: $(jq -r '.n8n.api_key' .secrets/credentials.json)" \
  $(jq -r '.n8n.url' .secrets/credentials.json)/api/v1/workflows | jq '.data | length'
```

### 8.5. Dashboards com Dados Incorretos

**Problema**: Dashboards mostram dados mas valores parecem incorretos

**Soluções**:

```bash
# 1. Verificar timezone
docker exec n8n-victoria-metrics date
docker exec n8n-grafana date

# 2. Verificar queries no VictoriaMetrics
curl -s 'http://localhost:8428/api/v1/query?query=n8n_workflow_execution_count' | jq '.'

# 3. Limpar cache do VictoriaMetrics (cuidado!)
docker-compose down
docker volume rm docker_victoria-metrics-data
docker-compose up -d

# 4. Reprocessar últimas 24h
cd /opt/n8n-tuning/
source .venv/bin/activate
python scripts/n8n_metrics_exporter.py
python scripts/n8n_node_metrics_exporter.py
```

---

## 📊 9. VALIDAÇÃO DE ACURACIDADE

### 9.1. Comparar com N8N UI

```bash
# 1. Contar workflows no N8N
#    UI: http://wf005.vya.digital:5678/workflows
#    Anotar número total de workflows

# 2. Verificar no VictoriaMetrics
curl -s 'http://localhost:8428/api/v1/query?query=count(n8n_workflow_info)' | \
  jq -r '.data.result[0].value[1]'

# Os valores devem ser IGUAIS
```

### 9.2. Validar Execuções

```bash
# 1. Contar execuções no N8N UI (últimas 24h)
#    UI: http://wf005.vya.digital:5678/executions

# 2. Query no VictoriaMetrics (últimas 24h)
curl -s 'http://localhost:8428/api/v1/query?query=sum(increase(n8n_workflow_execution_count[24h]))' | \
  jq -r '.data.result[0].value[1]'

# Diferença aceitável: até 5% (devido ao timing de coleta)
```

### 9.3. Validar Nodes

```bash
# 1. Executar um workflow no N8N e anotar tempo de execução

# 2. Aguardar 3 minutos (próximo cron)

# 3. Verificar no Grafana:
#    Dashboard: N8N Node Performance
#    Buscar pelo nome do workflow
#    Comparar tempo de execução

# Diferença aceitável: até 100ms
```

### 9.4. Script de Validação Automática

```bash
# Criar script de validação
cat > /opt/n8n-tuning/scripts/validate_accuracy.sh <<'EOF'
#!/bin/bash
echo "🔍 Validando acuracidade dos dados..."

# Carregar credenciais
N8N_URL=$(jq -r '.n8n.url' .secrets/credentials.json)
N8N_KEY=$(jq -r '.n8n.api_key' .secrets/credentials.json)

# Contar workflows na API
API_WORKFLOWS=$(curl -s -H "X-N8N-API-KEY: $N8N_KEY" "$N8N_URL/api/v1/workflows" | jq '.data | length')

# Contar workflows no VictoriaMetrics
VM_WORKFLOWS=$(curl -s 'http://localhost:8428/api/v1/query?query=count(n8n_workflow_info)' | jq -r '.data.result[0].value[1]')

echo "N8N API: $API_WORKFLOWS workflows"
echo "VictoriaMetrics: $VM_WORKFLOWS workflows"

if [ "$API_WORKFLOWS" == "$VM_WORKFLOWS" ]; then
    echo "✅ Dados consistentes!"
else
    echo "⚠️ Divergência detectada!"
fi
EOF

chmod +x /opt/n8n-tuning/scripts/validate_accuracy.sh

# Executar validação
./scripts/validate_accuracy.sh
```

---

## 🔧 10. MANUTENÇÃO

### 10.1. Monitoramento Contínuo

```bash
# Verificar uso de disco
df -h | grep -E 'victoria|grafana'

# Verificar logs de erro
docker-compose logs --tail=100 | grep -i error

# Verificar execução do cron
grep -i error /opt/n8n-tuning/logs/cron.log
```

### 10.2. Backup

```bash
# Backup dos dados (semanal recomendado)
cd /opt/n8n-tuning/docker/

# Parar containers
docker-compose stop

# Backup dos volumes
docker run --rm \
  -v docker_victoria-metrics-data:/source:ro \
  -v /backup:/backup \
  alpine tar czf /backup/victoria-metrics-$(date +%Y%m%d).tar.gz -C /source .

docker run --rm \
  -v docker_grafana-data:/source:ro \
  -v /backup:/backup \
  alpine tar czf /backup/grafana-$(date +%Y%m%d).tar.gz -C /source .

# Reiniciar containers
docker-compose start
```

### 10.3. Limpeza de Logs

```bash
# Limpar logs antigos (> 30 dias)
find /opt/n8n-tuning/logs/ -name "*.log" -mtime +30 -delete

# Rotação de logs do cron
cat > /etc/logrotate.d/n8n-tuning <<EOF
/opt/n8n-tuning/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

---

## 📋 11. CHECKLIST FINAL

### Após Deploy

- [ ] VictoriaMetrics health check OK
- [ ] Grafana acessível e logado
- [ ] Datasource VictoriaMetrics conectado
- [ ] 3 dashboards carregados
- [ ] Cron job instalado e executando
- [ ] Scripts Python executando sem erros
- [ ] Dados aparecendo nos dashboards (aguardar 5 min)
- [ ] Validação de acuracidade OK
- [ ] Backup automático configurado

### Monitoramento (Primeiras 24h)

- [ ] Verificar logs de erro a cada 4h
- [ ] Comparar métricas com N8N UI
- [ ] Validar tempos de execução
- [ ] Verificar uso de disco
- [ ] Testar alertas (se configurados)

### Documentação

- [ ] Documentar IP/porta do servidor
- [ ] Documentar credenciais de acesso (cofre seguro)
- [ ] Atualizar INDEX.md com status do deploy
- [ ] Criar entrada no TODO.md com próximos passos

---

## 🆘 12. SUPORTE

### Logs Importantes

```bash
# Logs do Docker
docker-compose logs -f victoria-metrics
docker-compose logs -f grafana

# Logs do Python
tail -f /opt/n8n-tuning/logs/cron.log

# Logs do sistema
journalctl -u docker -f
```

### Comandos Úteis

```bash
# Reiniciar tudo
cd /opt/n8n-tuning/docker/
docker-compose restart

# Ver uso de recursos
docker stats n8n-victoria-metrics n8n-grafana

# Verificar conectividade
curl -v http://wf005.vya.digital:5678/healthz
telnet wf005.vya.digital 5432
```

---

## 📝 13. PRÓXIMOS PASSOS

Após validar que tudo está funcionando:

1. **Configurar Alertas** (ver docs/NEXT_STEPS.md)
2. **Ajustar Retenção** de dados se necessário
3. **Criar Dashboards** adicionais personalizados
4. **Documentar Baseline** de performance
5. **Integrar com Sistema** de tickets/alertas existente

---

**✅ Deploy Completo!**

Se todos os checks acima estiverem OK, o sistema está pronto para uso em produção.

Para dúvidas ou problemas, consulte a seção de Troubleshooting ou os logs detalhados.

---

**Última Atualização**: 05/02/2026
