# 🔐 Secrets - Credenciais do Projeto

Esta pasta contém as credenciais necessárias para executar os scripts de análise do N8N.

## ⚠️ IMPORTANTE

**NUNCA commite arquivos de credenciais reais no Git!**

Esta pasta está protegida pelo `.gitignore` para evitar commits acidentais.

---

## 📄 Arquivos

### credentials.json
**Status**: ✅ Criado (precisa ser configurado)  
**Descrição**: Arquivo com as credenciais reais do projeto

**Ação Necessária**: Edite este arquivo e substitua os valores de exemplo pelas credenciais reais.

### credentials.template.json
**Status**: ✅ Template versionado  
**Descrição**: Template de exemplo (SEM credenciais reais)

Este arquivo PODE ser commitado no Git, pois serve apenas como exemplo.

---

## 🔧 Configuração

### 1. Editar credentials.json

Abra o arquivo e configure cada seção:

```json
{
  "n8n": {
    "url": "https://n8n.vya.digital",           // ← URL real do N8N
    "api_key": "n8n_api_xxxxxxxxxxxxx"          // ← API Key real
  },
  "postgresql": {
    "host": "wf005.vya.digital",                // ← Host do PostgreSQL
    "port": 5432,
    "database": "n8n",
    "user": "n8n_readonly",
    "password": "senha_real_aqui"               // ← Senha real
  },
  // ... outras configurações
}
```

### 2. Como Obter as Credenciais

#### N8N API Key
1. Acessar N8N (https://n8n.sua-empresa.com)
2. Ir em **Settings** → **API**
3. Gerar nova API Key
4. Copiar e colar em `credentials.json`

#### PostgreSQL
1. Conectar ao servidor: `ssh user@wf005.vya.digital`
2. Verificar credenciais do N8N:
   ```bash
   docker exec n8n_n8n env | grep DB_
   ```
3. Criar usuário read-only se necessário:
   ```sql
   CREATE USER n8n_readonly WITH PASSWORD 'senha_segura';
   GRANT CONNECT ON DATABASE n8n TO n8n_readonly;
   GRANT USAGE ON SCHEMA public TO n8n_readonly;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO n8n_readonly;
   ```

#### Grafana API Key
1. Acessar Grafana
2. Ir em **Configuration** → **API Keys**
3. Criar nova key com permissão de **Viewer**
4. Copiar para `credentials.json`

---

## 🔒 Segurança

### Boas Práticas

✅ **FAZER**:
- Manter `credentials.json` apenas localmente
- Usar senhas fortes e únicas
- Criar usuários read-only quando possível
- Rotacionar API keys periodicamente
- Compartilhar credenciais de forma segura (1Password, LastPass, etc)

❌ **NÃO FAZER**:
- Commitar `credentials.json` no Git
- Compartilhar credenciais por email/chat
- Usar mesma senha em múltiplos lugares
- Dar permissões desnecessárias

### Verificar se .gitignore está Funcionando

```bash
# Verificar status do Git
cd /path/to/n8n-tuning/.secrets
git status

# Se credentials.json aparecer, PARE e verifique o .gitignore
# Se não aparecer, está protegido ✅
```

---

## 📚 Uso nos Scripts

Os scripts Python carregam automaticamente as credenciais:

```python
import json
from pathlib import Path

# Carregar credenciais
secrets_file = Path(__file__).parent.parent / ".secrets" / "credentials.json"
with open(secrets_file) as f:
    credentials = json.load(f)

# Usar credenciais
n8n_url = credentials["n8n"]["url"]
api_key = credentials["n8n"]["api_key"]
```

**Alternativa**: Usar variáveis de ambiente

```bash
# Exportar como variáveis de ambiente
export N8N_URL=$(jq -r '.n8n.url' .secrets/credentials.json)
export N8N_API_KEY=$(jq -r '.n8n.api_key' .secrets/credentials.json)

# Usar nos scripts
python scripts/n8n_metrics_collector.py
```

---

## 🆘 Troubleshooting

### Erro: "credentials.json not found"
**Solução**: Copie o template e configure
```bash
cp credentials.template.json credentials.json
# Edite credentials.json com valores reais
```

### Erro: "Invalid API Key"
**Solução**: Verifique se a API key está correta
- Gere nova key no N8N
- Confirme que copiou corretamente (sem espaços extras)
- Teste manualmente:
  ```bash
  curl -H "X-N8N-API-KEY: sua-key" https://n8n.example.com/api/v1/workflows
  ```

### Erro: "Database connection refused"
**Solução**: Verifique conectividade
- Confirme host e porta corretos
- Teste conexão:
  ```bash
  psql -h host -p 5432 -U user -d database
  ```
- Verifique firewall/rede

---

## 📋 Checklist de Configuração

- [ ] `credentials.json` criado
- [ ] N8N URL configurada
- [ ] N8N API Key configurada e testada
- [ ] PostgreSQL host/port configurados
- [ ] PostgreSQL credenciais configuradas e testadas
- [ ] Grafana configurado (opcional)
- [ ] SSH configurado (opcional)
- [ ] `.gitignore` funcionando (git status não mostra credentials.json)
- [ ] Scripts testados e funcionando

---

**Última Atualização**: 02/02/2026  
**Responsável**: DevOps Team
