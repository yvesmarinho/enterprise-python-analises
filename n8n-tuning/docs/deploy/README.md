# 🚀 Guias de Deploy - N8N Performance Monitoring

**Última Atualização**: 05/02/2026

---

## 📚 Documentos Disponíveis

### 1. [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) 📖
**Guia Completo de Deploy** - 16 KB, 13 seções

Documento principal com instruções detalhadas passo-a-passo para fazer o deploy completo do sistema de monitoramento N8N para o servidor de produção.

**Conteúdo**:
- Checklist rápido
- Arquivos a copiar
- Preparação do servidor
- Configuração de credenciais
- Deploy Docker (Grafana + VictoriaMetrics)
- Instalação Python
- Configuração de cron jobs
- Validação completa
- Troubleshooting (5 cenários)
- Validação de acuracidade
- Manutenção e backup

**Use quando**: Fazer o primeiro deploy ou redeploy completo

---

### 2. [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md) ✅
**Checklist Interativo** - 6 KB, 8 fases

Lista de verificação passo-a-passo para garantir que nada seja esquecido durante o deploy.

**Fases**:
1. Preparação (10 min)
2. Instalação no Servidor (15 min)
3. Docker (10 min)
4. Python (10 min)
5. Cron (5 min)
6. Validação (10 min)
7. Validação de Acuracidade (10 min)
8. Monitoramento (24h)

**Tempo total estimado**: 60-70 minutos

**Use quando**: Executar o deploy seguindo um checklist

---

## 🛠️ Scripts de Deploy

### 1. `scripts/create_deploy_package.sh`
Cria arquivo `.tar.gz` com todos os arquivos necessários para o deploy.

**Uso**:
```bash
cd n8n-tuning/
./scripts/create_deploy_package.sh
```

**Resultado**: Arquivo `n8n-monitoring-deploy-YYYYMMDD_HHMMSS.tar.gz`

---

### 2. `scripts/validate_deploy.sh`
Valida se o deploy foi realizado corretamente, verificando:
- Arquivos essenciais
- Containers Docker
- Credenciais
- Cron jobs
- Dados no VictoriaMetrics
- Acuracidade (API vs VictoriaMetrics)
- Dashboards do Grafana
- Python e dependências

**Uso**:
```bash
cd /opt/n8n-tuning/
./scripts/validate_deploy.sh
```

**Output**: Relatório colorido com status de cada verificação

---

## 📋 Arquivos de Configuração

### `.secrets/credentials.template.json`
Template de credenciais para facilitar a configuração.

**Uso**:
```bash
# Copiar template
cp .secrets/credentials.template.json .secrets/credentials.json

# Editar com suas credenciais
nano .secrets/credentials.json

# Proteger arquivo
chmod 600 .secrets/credentials.json
```

**Credenciais necessárias**:
- N8N URL e API Key
- PostgreSQL (host, port, database, user, password)
- VictoriaMetrics URL (geralmente localhost:8428)

---

## 🚦 Workflow Recomendado

### Deploy Inicial

```
1. No Ambiente Local
   ├─ Executar: create_deploy_package.sh
   └─ Copiar pacote para servidor (scp/rsync)

2. No Servidor
   ├─ Extrair pacote
   ├─ Configurar credenciais
   ├─ Seguir: DEPLOY_CHECKLIST.md
   └─ Validar: validate_deploy.sh

3. Validação
   ├─ Acessar Grafana
   ├─ Verificar dashboards
   ├─ Comparar com N8N UI
   └─ Monitorar por 24h
```

### Troubleshooting

Se algo falhar durante o deploy:

1. **Consultar**: [DEPLOY_GUIDE.md - Seção 8 (Troubleshooting)](DEPLOY_GUIDE.md#8-troubleshooting)
2. **Executar**: `./scripts/validate_deploy.sh` para diagnóstico
3. **Verificar logs**:
   - Docker: `docker-compose logs`
   - Cron: `tail -f logs/cron.log`
   - Sistema: `journalctl -u docker -f`

---

## 📊 Validação de Acuracidade

Após o deploy, é crítico validar que os dados estão corretos.

### Método 1: Comparar Workflows
```bash
# Total de workflows na API
curl -H "X-N8N-API-KEY: $KEY" $N8N_URL/api/v1/workflows | jq '.data | length'

# Total no VictoriaMetrics
curl 'http://localhost:8428/api/v1/query?query=count(n8n_workflow_info)' | jq -r '.data.result[0].value[1]'

# Devem ser IGUAIS
```

### Método 2: Executar Workflow Manual
1. Executar workflow no N8N UI
2. Anotar tempo de execução
3. Aguardar 3 minutos (cron)
4. Verificar no Grafana dashboard "N8N Node Performance"
5. Comparar tempo (diferença < 100ms)

### Método 3: Script Automático
```bash
./scripts/validate_deploy.sh
# Verifica automaticamente consistência
```

---

## � Gestão de Dados Dev vs Prod

### Dados são Independentes ✅

**Dev (seu PC)**: `localhost:8428` → Volume Docker local  
**Prod (servidor)**: `servidor:8428` → Volume Docker no servidor

**Resultado**: Completamente separados, sem misturas!

**Documentação completa**: [DEV_VS_PROD_DATA.md](../DEV_VS_PROD_DATA.md)

### Opções Disponíveis:
1. **Separado** (Padrão) - Recomendado ✅
2. **Centralizado** - Para análise comparativa
3. **Exportar/Importar** - Para migração ou backup

---

## �🔐 Segurança

### Credenciais
- ✅ Sempre use `.secrets/credentials.json` (não versionado)
- ✅ Mantenha permissão 600 (`chmod 600`)
- ✅ Não compartilhe arquivo de credenciais
- ✅ Use senhas fortes para Grafana

### Acesso
- ✅ Grafana: Mude senha padrão (`W123Mudar`)
- ✅ VictoriaMetrics: Considere firewall (porta 8428)
- ✅ SSH: Use chaves, não senhas

---

## 🔄 Manutenção

### Backups (Semanal)
```bash
cd /opt/n8n-tuning/docker/
docker-compose stop

# Backup VictoriaMetrics
docker run --rm \
  -v docker_victoria-metrics-data:/source:ro \
  -v /backup:/backup \
  alpine tar czf /backup/victoria-metrics-$(date +%Y%m%d).tar.gz -C /source .

# Backup Grafana
docker run --rm \
  -v docker_grafana-data:/source:ro \
  -v /backup:/backup \
  alpine tar czf /backup/grafana-$(date +%Y%m%d).tar.gz -C /source .

docker-compose start
```

### Monitoramento
```bash
# Uso de disco
df -h | grep -E 'victoria|grafana'

# Logs de erro
docker-compose logs --tail=100 | grep -i error

# Cron executando
grep -c "✅ Coleta de métricas concluída" logs/cron.log
```

---

## ❓ FAQ

### P: Quanto tempo leva o deploy?
**R**: 60-70 minutos seguindo o checklist, incluindo validações.

### P: Posso fazer o deploy em produção direto?
**R**: Recomendado testar em homologação primeiro, mas o guia é para produção.

### P: E se as portas 8428 ou 3100 estiverem ocupadas?
**R**: Edite `docker/docker-compose.yml` nas linhas de `ports:` antes de subir.

### P: Como sei se os dados estão corretos?
**R**: Execute `validate_deploy.sh` e compare workflows API vs VictoriaMetrics.

### P: Preciso do PostgreSQL para funcionar?
**R**: Não. Os nodes metrics usam PostgreSQL, mas o sistema básico (workflows e execuções) funciona só com a API do N8N.

### P: Posso usar outra porta para o Grafana?
**R**: Sim, edite `docker-compose.yml` mudando `3100:3000` para `PORTA:3000`.

### P: Os dados do dev e prod vão se misturar?
**R**: NÃO! São completamente independentes. Ver [DEV_VS_PROD_DATA.md](../DEV_VS_PROD_DATA.md) para detalhes.

---

## 📞 Suporte

### Logs Importantes
```bash
# Docker
docker-compose logs -f victoria-metrics
docker-compose logs -f grafana

# Python/Cron
tail -f /opt/n8n-tuning/logs/cron.log

# Sistema
journalctl -u docker -f
```

### Comandos Úteis
```bash
# Status dos containers
docker ps | grep n8n

# Uso de recursos
docker stats n8n-victoria-metrics n8n-grafana

# Reiniciar tudo
cd /opt/n8n-tuning/docker/
docker-compose restart

# Ver métricas disponíveis
curl -s 'http://localhost:8428/api/v1/labels' | jq '.data'
```

---

## 📝 Histórico de Versões

| Versão | Data | Alterações |
|--------|------|------------|
| 1.0 | 05/02/2026 | Versão inicial dos guias de deploy |

---

**Escolha seu guia**: [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) (completo) ou [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md) (rápido)
