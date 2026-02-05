# ✅ CHECKLIST DE DEPLOY - N8N Monitoring

**Data**: 05/02/2026  
**Versão**: 1.0

---

## 🎯 PRÉ-REQUISITOS

### No Servidor
- [ ] Docker 20.10+ instalado
- [ ] Docker Compose 2.0+ instalado
- [ ] Python 3.10+ instalado
- [ ] Portas 8428 e 3100 disponíveis
- [ ] Acesso SSH configurado
- [ ] jq instalado (`apt install jq`)
- [ ] curl instalado

### Credenciais Necessárias
- [ ] N8N API Key obtida
- [ ] PostgreSQL host/porta/user/senha
- [ ] Acesso ao servidor N8N (wf005.vya.digital:5678)

---

## 📦 FASE 1: PREPARAÇÃO (10 min)

### 1.1. No Ambiente Local
```bash
cd /home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-tuning/

# Criar pacote de deploy
./scripts/create_deploy_package.sh
```

- [ ] Pacote `.tar.gz` criado com sucesso
- [ ] Tamanho do pacote verificado (~2-5 MB)

### 1.2. Copiar para Servidor
```bash
# Copiar pacote
scp n8n-monitoring-deploy-*.tar.gz user@servidor:/opt/

# OU usar rsync (mais rápido)
rsync -avz --progress n8n-monitoring-deploy-*.tar.gz user@servidor:/opt/
```

- [ ] Arquivo copiado com sucesso
- [ ] Checksum validado (opcional)

---

## 🖥️ FASE 2: INSTALAÇÃO NO SERVIDOR (15 min)

### 2.1. Extrair Arquivos
```bash
ssh user@servidor
cd /opt/
tar -xzf n8n-monitoring-deploy-*.tar.gz
cd n8n-tuning/
```

- [ ] Arquivos extraídos
- [ ] Estrutura de pastas OK
- [ ] Permissões corretas

### 2.2. Criar Estrutura de Pastas
```bash
mkdir -p .secrets data/{metrics,logs,workflows} logs
```

- [ ] Pastas criadas

### 2.3. Configurar Credenciais
```bash
# Copiar template
cp .secrets/credentials.template.json .secrets/credentials.json

# Editar com suas credenciais
nano .secrets/credentials.json
```

**Preencher**:
- [ ] `n8n.url` - URL do N8N
- [ ] `n8n.api_key` - API Key do N8N
- [ ] `postgresql.host` - Host do PostgreSQL
- [ ] `postgresql.port` - Porta (5432)
- [ ] `postgresql.database` - Nome do DB (n8n)
- [ ] `postgresql.user` - Usuário
- [ ] `postgresql.password` - Senha

```bash
# Proteger arquivo
chmod 600 .secrets/credentials.json
```

- [ ] Credenciais configuradas
- [ ] Permissões do arquivo OK (600)

---

## 🐳 FASE 3: DOCKER (10 min)

### 3.1. Subir Containers
```bash
cd docker/
docker-compose up -d
```

- [ ] VictoriaMetrics iniciado
- [ ] Grafana iniciado
- [ ] Sem erros nos logs

### 3.2. Verificar Saúde
```bash
# Aguardar 30 segundos para inicialização
sleep 30

# Verificar containers
docker ps | grep n8n

# Health checks
curl http://localhost:8428/health
curl http://localhost:3100/api/health
```

- [ ] Ambos containers rodando
- [ ] Health checks retornam OK
- [ ] Portas acessíveis

### 3.3. Acessar Grafana
```bash
# No navegador
http://SERVIDOR_IP:3100

# Login: admin / W123Mudar
```

- [ ] Grafana acessível
- [ ] Login funcionando
- [ ] Interface carregada

---

## 🐍 FASE 4: PYTHON (10 min)

### 4.1. Criar Ambiente Virtual
```bash
cd /opt/n8n-tuning/

python3 -m venv .venv
source .venv/bin/activate
```

- [ ] Venv criado
- [ ] Venv ativado

### 4.2. Instalar Dependências
```bash
pip install --upgrade pip
pip install requests psycopg2-binary

# OU usar pyproject.toml
pip install -e .
```

- [ ] requests instalado
- [ ] psycopg2-binary instalado
- [ ] Sem erros

### 4.3. Testar Scripts
```bash
# Testar exporter principal
python scripts/n8n_metrics_exporter.py
```

**Verificar output**:
- [ ] Conectou ao N8N
- [ ] Coletou workflows
- [ ] Coletou execuções
- [ ] Exportou para VictoriaMetrics
- [ ] Sem erros

```bash
# Testar exporter de nodes
python scripts/n8n_node_metrics_exporter.py
```

- [ ] Conectou ao PostgreSQL
- [ ] Coletou dados de execução
- [ ] Exportou métricas
- [ ] Sem erros

---

## ⏰ FASE 5: CRON (5 min)

### 5.1. Ajustar Caminhos
```bash
nano scripts/cron_executions.sh

# Ajustar:
PROJECT_DIR="/opt/n8n-tuning"
PYTHON_VENV="/opt/n8n-tuning/.venv/bin/python"
```

- [ ] Caminhos corretos
- [ ] Arquivo salvo

### 5.2. Dar Permissões
```bash
chmod +x scripts/cron_executions.sh
```

- [ ] Permissão de execução OK

### 5.3. Instalar Cron
```bash
crontab -e

# Adicionar linha:
*/3 * * * * /opt/n8n-tuning/scripts/cron_executions.sh >> /opt/n8n-tuning/logs/cron.log 2>&1
```

- [ ] Cron job adicionado
- [ ] Cron job salvo

### 5.4. Verificar Instalação
```bash
crontab -l | grep cron_executions.sh
```

- [ ] Cron job listado

---

## ✅ FASE 6: VALIDAÇÃO (10 min)

### 6.1. Executar Script de Validação
```bash
cd /opt/n8n-tuning/
./scripts/validate_deploy.sh
```

**Verificar resultado**:
- [ ] Arquivos OK
- [ ] Containers OK
- [ ] Credenciais OK
- [ ] Cron OK (warning aceitável)
- [ ] Dados OK (aguardar 5 min se warning)

### 6.2. Aguardar Primeira Coleta
```bash
# Aguardar 3-5 minutos para cron executar
sleep 180

# Verificar logs
tail -20 logs/cron.log
```

- [ ] Cron executou
- [ ] Sem erros nos logs
- [ ] Métricas coletadas

### 6.3. Verificar VictoriaMetrics
```bash
# Verificar se tem dados
curl -s 'http://localhost:8428/api/v1/labels' | jq '.data | length'

# Deve retornar número > 0
```

- [ ] VictoriaMetrics tem métricas

### 6.4. Verificar Grafana

**No navegador: http://SERVIDOR_IP:3100**

1. Ir em **Configuration** → **Data Sources**
   - [ ] VictoriaMetrics presente
   - [ ] Status: Working (verde)

2. Ir em **Dashboards** → **N8N Performance**
   - [ ] 3 dashboards listados
   - [ ] N8N Performance Overview abre
   - [ ] N8N Performance Detailed abre
   - [ ] N8N Node Performance abre

3. Abrir **N8N Performance Detailed**
   - [ ] Tabela "Bottleneck Score Ranking" com dados
   - [ ] Gráficos com dados
   - [ ] Sem erros

---

## 🔍 FASE 7: VALIDAÇÃO DE ACURACIDADE (10 min)

### 7.1. Comparar Workflows
```bash
cd /opt/n8n-tuning/

# Executar validação
./scripts/validate_deploy.sh

# Verificar linha:
# "Workflows na API N8N: X"
# "Workflows no VictoriaMetrics: X"
# Devem ser IGUAIS
```

- [ ] Números de workflows iguais

### 7.2. Validar no Grafana

1. Abrir N8N UI: http://wf005.vya.digital:5678/workflows
2. Contar workflows ativos
3. Ver mesmo número no Grafana
   - [ ] Números conferem

### 7.3. Validar Execuções

1. Executar um workflow manualmente no N8N
2. Anotar tempo de execução
3. Aguardar 3 minutos
4. Verificar no Grafana (N8N Node Performance)
   - [ ] Workflow aparece
   - [ ] Tempo de execução similar

---

## 📊 FASE 8: MONITORAMENTO (24h)

### Primeira Hora
- [ ] Verificar logs a cada 15 min
- [ ] Sem erros críticos
- [ ] Métricas continuam sendo coletadas

### Primeiras 4 Horas
- [ ] Verificar uso de disco
- [ ] Verificar uso de memória
- [ ] Dashboards atualizando

### Primeiras 24 Horas
- [ ] Sistema estável
- [ ] Sem gaps nos dados
- [ ] Performance OK

---

## 🎉 CONCLUSÃO

### Checklist Final
- [ ] Todos os containers rodando
- [ ] Cron executando a cada 3 min
- [ ] Grafana acessível e configurado
- [ ] Dashboards com dados corretos
- [ ] Validação de acuracidade OK
- [ ] Logs sem erros críticos
- [ ] Documentação atualizada

### Próximos Passos
- [ ] Configurar alertas (opcional)
- [ ] Ajustar retenção de dados (opcional)
- [ ] Criar backup schedule
- [ ] Documentar baseline de performance

---

## 🆘 SE ALGO FALHAR

1. **Containers não sobem**: Ver `docker-compose logs`
2. **Grafana sem dashboards**: Verificar permissões em `docker/grafana/`
3. **Sem dados no VictoriaMetrics**: Verificar credenciais + logs do cron
4. **Scripts Python com erro**: Verificar `.secrets/credentials.json`

**Documentação completa**: [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)

---

**✅ Deploy Validado em**: ___/___/______  
**👤 Validado por**: ________________  
**📝 Observações**: ________________
