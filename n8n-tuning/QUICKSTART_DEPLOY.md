# 🚀 QUICK START - Deploy para Servidor

**Tempo estimado**: 60-70 minutos  
**Última atualização**: 05/02/2026

---

## 📦 PASSO 1: Criar Pacote (Local)

```bash
cd /home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-tuning/

# Criar pacote de deploy
./scripts/create_deploy_package.sh

# Resultado: n8n-monitoring-deploy-YYYYMMDD_HHMMSS.tar.gz
```

---

## 📤 PASSO 2: Copiar para Servidor

```bash
# Opção 1: SCP
scp n8n-monitoring-deploy-*.tar.gz user@servidor:/opt/

# Opção 2: RSYNC (mais rápido)
rsync -avz --progress n8n-monitoring-deploy-*.tar.gz user@servidor:/opt/
```

---

## 🖥️ PASSO 3: Instalar no Servidor

```bash
# Conectar ao servidor
ssh user@servidor

# Extrair
cd /opt/
tar -xzf n8n-monitoring-deploy-*.tar.gz
cd n8n-tuning/

# Criar pastas
mkdir -p .secrets data/{metrics,logs,workflows} logs

# Configurar credenciais
cp .secrets/credentials.template.json .secrets/credentials.json
nano .secrets/credentials.json  # Preencher com suas credenciais
chmod 600 .secrets/credentials.json

# Subir Docker
cd docker/
docker-compose up -d

# Aguardar 30 segundos
sleep 30

# Voltar ao diretório raiz
cd ..

# Instalar Python
python3 -m venv .venv
source .venv/bin/activate
pip install requests psycopg2-binary

# Testar scripts
python scripts/n8n_metrics_exporter.py
python scripts/n8n_node_metrics_exporter.py

# Configurar cron
nano scripts/cron_executions.sh  # Ajustar PROJECT_DIR e PYTHON_VENV
chmod +x scripts/cron_executions.sh
crontab -e  # Adicionar: */3 * * * * /opt/n8n-tuning/scripts/cron_executions.sh >> /opt/n8n-tuning/logs/cron.log 2>&1
```

---

## ✅ PASSO 4: Validar

```bash
# Executar validação
cd /opt/n8n-tuning/
./scripts/validate_deploy.sh

# Aguardar 5 minutos e verificar dados
sleep 300
curl -s 'http://localhost:8428/api/v1/labels' | jq '.data | length'

# Acessar Grafana
# http://SERVIDOR_IP:3100
# Login: admin / W123Mudar
```

---

## 🎯 Checklist Rápido

- [ ] Pacote criado
- [ ] Copiado para servidor
- [ ] Extraído em /opt/
- [ ] Credenciais configuradas
- [ ] Docker rodando (victoria-metrics + grafana)
- [ ] Python instalado
- [ ] Scripts testados sem erro
- [ ] Cron instalado
- [ ] Validação OK
- [ ] Grafana acessível
- [ ] Dashboards com dados

---

## 📚 Documentação Completa

Se precisar de detalhes ou troubleshooting:

- **Guia Completo**: [docs/DEPLOY_GUIDE.md](docs/DEPLOY_GUIDE.md)
- **Checklist Detalhado**: [docs/DEPLOY_CHECKLIST.md](docs/DEPLOY_CHECKLIST.md)
- **Índice de Docs**: [docs/deploy/README.md](docs/deploy/README.md)

---

## 🆘 Problemas?

```bash
# Ver logs
docker-compose logs victoria-metrics
docker-compose logs grafana
tail -f logs/cron.log

# Reiniciar
cd /opt/n8n-tuning/docker/
docker-compose restart

# Validar novamente
cd /opt/n8n-tuning/
./scripts/validate_deploy.sh
```

---

**✅ Pronto!** Seu sistema de monitoramento N8N está no ar!
