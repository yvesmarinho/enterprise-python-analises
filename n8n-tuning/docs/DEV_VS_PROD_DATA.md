# 🔄 Gestão de Dados - Dev vs Produção

**Data**: 05/02/2026  
**Tópico**: VictoriaMetrics - Dados de Desenvolvimento e Produção

---

## ❓ A PERGUNTA

**"É possível manter as informações do VictoriaMetrics do DEV e do PROD separadas?"**

**Resposta**: ✅ SIM! Os dados são completamente independentes por padrão.

---

## 🏗️ COMO FUNCIONA

### Ambiente de Desenvolvimento (Local)

```
Seu Computador (localhost)
├── VictoriaMetrics: localhost:8428
│   ├── Volume: victoria-metrics-data (local)
│   ├── Coleta de: wf005.vya.digital:5678 (N8N)
│   └── Dados: Últimos 3 dias de testes
│
└── Grafana: localhost:3100
    ├── Volume: grafana-data (local)
    ├── Datasource: http://victoria-metrics:8428
    └── Dashboards: Seus testes e desenvolvimento
```

### Ambiente de Produção (Servidor)

```
Servidor (wf001, wf002, ou outro)
├── VictoriaMetrics: servidor:8428
│   ├── Volume: victoria-metrics-data (servidor)
│   ├── Coleta de: wf005.vya.digital:5678 (N8N)
│   └── Dados: Monitoramento contínuo de produção
│
└── Grafana: servidor:3100
    ├── Volume: grafana-data (servidor)
    ├── Datasource: http://victoria-metrics:8428
    └── Dashboards: Monitoramento de produção
```

---

## ✅ POR QUE OS DADOS NÃO SE MISTURAM

### 1. Volumes Docker Independentes

**Dev (Local)**:
```bash
# Volume local
docker volume ls | grep victoria
# Resultado: docker_victoria-metrics-data
```

**Prod (Servidor)**:
```bash
# Volume no servidor (totalmente separado)
docker volume ls | grep victoria
# Resultado: docker_victoria-metrics-data (mas em outra máquina)
```

### 2. Instâncias Separadas

| Aspecto | Dev (Local) | Prod (Servidor) |
|---------|-------------|-----------------|
| IP/Host | localhost | servidor_ip |
| Porta | 8428 | 8428 |
| Volume | /var/lib/docker/volumes/local | /var/lib/docker/volumes/servidor |
| Dados | Testes | Produção |
| Coleta | Manual/Cron | Automático via Cron |

### 3. Labels Diferentes (Opcional)

Você pode adicionar labels para distinguir:

**Dev**:
```bash
# No script de coleta Dev
ENVIRONMENT="dev"
```

**Prod**:
```bash
# No script de coleta Prod
ENVIRONMENT="prod"
```

Depois consultar por ambiente:
```bash
# Apenas Dev
{environment="dev"}

# Apenas Prod
{environment="prod"}
```

---

## 📊 CENÁRIOS DE USO

### Cenário 1: Dev e Prod Separados (Padrão) ✅

**Recomendado para**: A maioria dos casos

```
Dev (seu PC)               Prod (servidor)
├── Testes                 ├── Monitoramento real
├── Desenvolvimento        ├── Alertas
└── Validação              └── Baseline de produção
```

**Vantagens**:
- ✅ Não contamina dados de produção
- ✅ Pode testar queries sem afetar prod
- ✅ Dados independentes

**Como funciona**:
- Deploy segue o guia normalmente
- Cada ambiente mantém seus dados
- Dashboards são os mesmos (provisioning)

---

### Cenário 2: Centralizar Dados em Um VictoriaMetrics

**Para**: Análise comparativa ou histórico unificado

```
VictoriaMetrics Central
├── Dados de Dev (label: environment=dev)
├── Dados de Prod (label: environment=prod)
└── Dashboards com filtros por ambiente
```

**Como implementar**:

#### Opção A: Todos coletam para um VM central

1. **Escolher onde centralizar** (ex: servidor de monitoramento)

2. **Configurar coletores para apontar para central**:

```json
// .secrets/credentials.json (DEV)
{
  "victoria_metrics": {
    "url": "http://servidor-central:8428"
  }
}
```

```json
// .secrets/credentials.json (PROD)
{
  "victoria_metrics": {
    "url": "http://servidor-central:8428"
  }
}
```

3. **Adicionar label de ambiente** nos scripts:

```python
# scripts/n8n_metrics_exporter.py
import os

ENVIRONMENT = os.getenv('MONITORING_ENV', 'prod')

# Ao exportar métricas, adicionar label
def export_metrics(self, metrics: List[Dict]):
    for metric in metrics:
        metric['environment'] = ENVIRONMENT
        # ... resto do código
```

4. **Atualizar dashboards** para filtrar por ambiente:

```
# Query no Grafana
n8n_workflow_execution_count{environment="$environment"}
```

#### Opção B: Replicação de dados entre VMs

**Usar Remote Write do VictoriaMetrics**:

```yaml
# docker-compose.yml do DEV
services:
  victoria-metrics:
    # ... configuração existente
    command:
      - '-storageDataPath=/victoria-metrics-data'
      - '-retentionPeriod=90d'
      - '-httpListenAddr=:8428'
      - '-remoteWrite.url=http://servidor-central:8428/api/v1/write'
```

**Vantagens**:
- ✅ Histórico centralizado
- ✅ Análise comparativa
- ✅ Backup automático

**Desvantagens**:
- ❌ Mais complexo
- ❌ Requer servidor central
- ❌ Pode misturar dados se não usar labels

---

### Cenário 3: Exportar/Importar Dados

**Para**: Migrar dados entre ambientes ou fazer backup

#### Exportar do Dev:
```bash
# No ambiente DEV
cd /home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-analysis/n8n-tuning/docker/

# Exportar dados (formato nativo do VM)
docker exec n8n-victoria-metrics wget http://localhost:8428/api/v1/export/native \
  -O /victoria-metrics-data/export.bin

# Copiar para fora do container
docker cp n8n-victoria-metrics:/victoria-metrics-data/export.bin ./vm-export-dev.bin

# Copiar para servidor
scp vm-export-dev.bin user@servidor:/opt/n8n-tuning/
```

#### Importar no Prod:
```bash
# No servidor PROD
cd /opt/n8n-tuning/

# Copiar para dentro do container
docker cp vm-export-dev.bin n8n-victoria-metrics:/tmp/

# Importar
docker exec n8n-victoria-metrics \
  wget http://localhost:8428/api/v1/import/native \
  --post-file=/tmp/vm-export-dev.bin
```

**Uso**: Backup, migração, ou análise histórica

---

## 🎯 RECOMENDAÇÃO PARA SEU CASO

### Opção Recomendada: **Cenário 1 - Separado** ✅

**Motivos**:
1. ✅ **Simplicidade**: Cada ambiente independente
2. ✅ **Segurança**: Dados de prod não são afetados por testes
3. ✅ **Performance**: Cada VM otimizado para seu uso
4. ✅ **Facilidade**: Deploy direto conforme guias

**Como proceder**:
- Seguir o DEPLOY_CHECKLIST.md normalmente
- Dev mantém seus dados em `localhost:8428`
- Prod mantém seus dados em `servidor:8428`
- Se precisar comparar, exportar dados específicos

---

## 📋 CHECKLIST DE DECISÃO

### Perguntas para decidir:

1. **Precisa comparar Dev vs Prod em tempo real?**
   - ❌ Não → Separado (Cenário 1)
   - ✅ Sim → Centralizado (Cenário 2)

2. **Precisa manter histórico de Dev em Prod?**
   - ❌ Não → Separado (Cenário 1)
   - ✅ Sim → Exportar/Importar (Cenário 3)

3. **Tem servidor central de monitoramento?**
   - ❌ Não → Separado (Cenário 1)
   - ✅ Sim → Considerar Centralizado (Cenário 2)

4. **Equipe precisa ver dados de Dev?**
   - ❌ Não, só você → Separado (Cenário 1)
   - ✅ Sim, toda equipe → Considerar Centralizado (Cenário 2)

---

## 🛠️ IMPLEMENTAÇÃO

### Para Manter Separado (Recomendado)

**Nada a fazer!** O deploy padrão já mantém separado.

```bash
# Dev
cd n8n-tuning/
docker-compose up -d  # Dados locais

# Prod
ssh servidor
cd /opt/n8n-tuning/docker/
docker-compose up -d  # Dados no servidor
```

### Para Centralizar (Avançado)

**Se decidir centralizar no futuro**:

1. Criar servidor central de monitoramento
2. Instalar VictoriaMetrics central
3. Configurar Remote Write nos coletores
4. Adicionar labels de ambiente
5. Atualizar dashboards com filtros

**Documentação**: [VictoriaMetrics Remote Write](https://docs.victoriametrics.com/vmagent.html#remote-write)

---

## ⚠️ CUIDADOS

### O QUE EVITAR

❌ **Não apontar Dev e Prod para o mesmo VM sem labels**
- Mistura dados sem distinção
- Dificulta análise
- Pode invalidar baseline

❌ **Não copiar volume Docker entre ambientes**
```bash
# NÃO FAÇA ISSO!
docker cp victoria-metrics-data servidor:/volumes/
```
- Pode corromper dados
- Timestamps inconsistentes
- Melhor usar export/import

❌ **Não usar mesmo Grafana para Dev e Prod sem organização**
- Risco de confundir ambientes
- Ações em prod por engano

---

## 📊 RESUMO VISUAL

```
┌─────────────────────────────────────────────────────────┐
│                    CENÁRIO 1: SEPARADO                  │
│                     (RECOMENDADO)                       │
└─────────────────────────────────────────────────────────┘

Dev (localhost)                    Prod (servidor)
┌──────────────────┐              ┌──────────────────┐
│ VictoriaMetrics  │              │ VictoriaMetrics  │
│   :8428          │              │   :8428          │
│                  │    ➜➜➜       │                  │
│ - Dados testes   │  Separados   │ - Dados prod     │
│ - 3 dias         │              │ - 90 dias        │
└──────────────────┘              └──────────────────┘
        ↓                                  ↓
┌──────────────────┐              ┌──────────────────┐
│ Grafana          │              │ Grafana          │
│   :3100          │              │   :3100          │
└──────────────────┘              └──────────────────┘


┌─────────────────────────────────────────────────────────┐
│               CENÁRIO 2: CENTRALIZADO                   │
│                    (AVANÇADO)                           │
└─────────────────────────────────────────────────────────┘

Dev (localhost)                Servidor Central
┌──────────────────┐          ┌──────────────────────┐
│ Coletor Dev      │──────┐   │ VictoriaMetrics      │
│ environment=dev  │      │   │   Central            │
└──────────────────┘      │   │                      │
                          ├──→│ - Dados Dev (label)  │
Prod (servidor)           │   │ - Dados Prod (label) │
┌──────────────────┐      │   │                      │
│ Coletor Prod     │──────┘   └──────────────────────┘
│ environment=prod │                     ↓
└──────────────────┘          ┌──────────────────────┐
                              │ Grafana Central      │
                              │ (filtros por env)    │
                              └──────────────────────┘
```

---

## 🎯 DECISÃO FINAL

Para seu caso, **recomendo Cenário 1 (Separado)**:

### ✅ Vantagens para você:
1. **Simplicidade**: Deploy direto, sem configurações extras
2. **Segurança**: Testes não afetam produção
3. **Independência**: Pode derrubar dev sem afetar prod
4. **Flexibilidade**: Pode centralizar depois se necessário

### 📋 Próximos Passos:
1. Seguir DEPLOY_CHECKLIST.md normalmente
2. Deploy cria novo VictoriaMetrics no servidor
3. Dados de dev ficam no seu PC
4. Dados de prod ficam no servidor
5. **Ambos independentes e seguros** ✅

### 🔄 Se Precisar Comparar Depois:
- Exportar período específico do dev
- Importar no prod com label "dev"
- Criar dashboard comparativo
- Documentação: Cenário 3 deste guia

---

## 📞 FAQ

### P: Os dados do dev vão sumir depois do deploy em prod?
**R**: NÃO! São volumes Docker separados em máquinas diferentes.

### P: Posso testar queries no dev sem afetar prod?
**R**: SIM! Completamente independentes.

### P: Preciso fazer backup do dev antes do deploy?
**R**: Não é necessário, mas recomendado se tiver dados importantes de teste.

### P: Como faço backup dos dados do dev?
**R**: 
```bash
cd n8n-tuning/docker/
docker-compose stop
docker run --rm \
  -v docker_victoria-metrics-data:/source:ro \
  -v $PWD:/backup \
  alpine tar czf /backup/victoria-metrics-dev-backup.tar.gz -C /source .
docker-compose start
```

### P: Posso acessar o Grafana do prod do meu PC?
**R**: SIM! Acesse `http://servidor_ip:3100`

### P: Os dashboards vão aparecer no prod?
**R**: SIM! São provisionados automaticamente via `docker/grafana/dashboards/`

### P: Posso mudar para centralizado depois?
**R**: SIM! Seguir Cenário 2 deste guia.

---

## 📚 Documentação Relacionada

- [DEPLOY_GUIDE.md](../DEPLOY_GUIDE.md) - Deploy completo
- [DEPLOY_CHECKLIST.md](../DEPLOY_CHECKLIST.md) - Checklist do deploy
- [VictoriaMetrics Docs](https://docs.victoriametrics.com/) - Documentação oficial

---

**Resumo**: Seus dados de dev e prod são **completamente independentes** por padrão. Siga o deploy normalmente! ✅

**Última Atualização**: 05/02/2026
