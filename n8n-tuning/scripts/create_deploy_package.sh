#!/bin/bash
#
# Script para criar pacote de deploy
# Gera arquivo .tar.gz com tudo necessário para o servidor
#

set -e

echo "📦 Criando pacote de deploy do N8N Monitoring..."
echo ""

# Diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Nome do arquivo
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="n8n-monitoring-deploy-${TIMESTAMP}.tar.gz"

# Criar lista de arquivos a incluir
cat > /tmp/deploy-files.txt <<EOF
docker/
scripts/
docs/
pyproject.toml
.python-version
README.md
.gitignore
EOF

echo "📋 Arquivos a incluir:"
cat /tmp/deploy-files.txt
echo ""

# Criar tarball
echo "🗜️ Compactando arquivos..."
cd ..
tar -czf "/tmp/${PACKAGE_NAME}" \
    -T /tmp/deploy-files.txt \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='data/metrics/*.json' \
    --exclude='data/workflows/*.json' \
    --exclude='logs/*.log' \
    --exclude='logs/*.csv' \
    --exclude='.secrets/*.json' \
    n8n-tuning/

cd n8n-tuning

# Mover para pasta atual
mv "/tmp/${PACKAGE_NAME}" .

# Limpar arquivo temporário
rm /tmp/deploy-files.txt

# Informações do pacote
SIZE=$(du -h "${PACKAGE_NAME}" | cut -f1)

echo ""
echo "✅ Pacote criado com sucesso!"
echo ""
echo "📦 Arquivo: ${PACKAGE_NAME}"
echo "📊 Tamanho: ${SIZE}"
echo ""
echo "🚀 Próximos passos:"
echo "   1. Copiar para o servidor:"
echo "      scp ${PACKAGE_NAME} user@servidor:/opt/"
echo ""
echo "   2. No servidor, extrair:"
echo "      cd /opt/"
echo "      tar -xzf ${PACKAGE_NAME}"
echo ""
echo "   3. Seguir: docs/DEPLOY_GUIDE.md"
echo ""
