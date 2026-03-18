#!/usr/bin/env bash
# =============================================================================
# Executa ANA-001 no wfdb01 via SSH SPA (fwknop)
#
# O script é necessário porque a query histogram_quantile para 10+ dias com
# step 5m excede o timeout de rede do Prometheus acessado remotamente via HTTPS.
# No wfdb01, o Prometheus e o VictoriaMetrics são acessados localmente (Docker
# network), sem TLS overhead e sem latência de rede.
#
# Arquitetura (dentro do wfdb01):
#   Prometheus      → http://prometheus:9090   (ou http://localhost:9090)
#   VictoriaMetrics → http://victoriametrics:8428
#
# Pré-requisitos locais:
#   fwknop instalado e ~/.fwknoprc com seção [wfdb01] configurada
#   git instalado no wfdb01
#   python3 + pip no wfdb01 (versão 3.11+)
#
# Uso:
#   bash scripts/run_analysis_on_wfdb01.sh
#   bash scripts/run_analysis_on_wfdb01.sh --from 2025-03-01 --to 2026-03-18
#   bash scripts/run_analysis_on_wfdb01.sh --step 1h --no-download
# =============================================================================

set -euo pipefail

# ── Configuração ──────────────────────────────────────────────────────────────
WFDB01_HOST="wfdb01.vya.digital"
WFDB01_USER="archaris"
WFDB01_PORT="5010"
FWKNOP_RC="$HOME/.fwknoprc"
FWKNOP_SECTION="wfdb01"

REMOTE_WORKDIR="~/n8n-analyzer-run"
REMOTE_VENV="$REMOTE_WORKDIR/.venv"

# URLs internas (acessíveis dentro do wfdb01)
PROMETHEUS_INTERNAL="http://prometheus:9090"
VM_INTERNAL="http://victoriametrics:8428"
LOKI_INTERNAL="http://loki-gateway:3100"  # ajuste se necessário

# Defaults de análise (sobrescritos por args)
FROM_DATE="2026-03-04"
TO_DATE="2026-03-14"
STEP="5m"
OUTPUT_FORMAT="markdown"
DOWNLOAD_REPORT=true

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --from)       FROM_DATE="$2"; shift 2 ;;
        --to)         TO_DATE="$2";   shift 2 ;;
        --step)       STEP="$2";      shift 2 ;;
        --format)     OUTPUT_FORMAT="$2"; shift 2 ;;
        --no-download) DOWNLOAD_REPORT=false; shift ;;
        *) echo "Argumento desconhecido: $1" >&2; exit 1 ;;
    esac
done

LOCAL_REPORT_DIR="tmp"
REMOTE_REPORT="$REMOTE_WORKDIR/reports"

SSH_CMD="ssh -p $WFDB01_PORT ${WFDB01_USER}@${WFDB01_HOST}"

# ── Funções ───────────────────────────────────────────────────────────────────
log()  { echo "==> $*"; }
warn() { echo "[WARN] $*" >&2; }

spa_open() {
    log "Abrindo porta via fwknop SPA..."
    fwknop --rc-file "$FWKNOP_RC" -n "$FWKNOP_SECTION"
    sleep 3
    log "Porta aberta."
}

# ── 1. SPA ────────────────────────────────────────────────────────────────────
spa_open

# ── 2. Setup remoto (apenas na primeira vez ou se necessário) ─────────────────
log "Verificando ambiente Python em $WFDB01_HOST..."

$SSH_CMD bash <<EOF
set -euo pipefail

# Garante que o diretório de trabalho existe
mkdir -p $REMOTE_WORKDIR/reports
cd $REMOTE_WORKDIR

# Cria (ou recria) venv se não existir ou estiver incompleto
if [[ ! -f $REMOTE_VENV/bin/activate ]]; then
    echo "Criando venv em $REMOTE_VENV..."
    rm -rf $REMOTE_VENV
    python3 -m venv $REMOTE_VENV || { echo "ERRO: python3-venv não instalado. Instale com: sudo apt install python3-venv" >&2; exit 1; }
fi

# Instala dependências mínimas
source $REMOTE_VENV/bin/activate
pip install --quiet --upgrade pip
pip install --quiet \
    "httpx>=0.27" \
    "click>=8.1" \
    "pydantic>=2.0" \
    "python-dotenv"

echo "Venv OK: \$(python --version)"
EOF

# ── 3. Copia o pacote n8n_analyzer ───────────────────────────────────────────
log "Copiando código n8n_analyzer para $WFDB01_HOST..."

scp -P "$WFDB01_PORT" -q \
    pyproject.toml \
    "${WFDB01_USER}@${WFDB01_HOST}:${REMOTE_WORKDIR}/"

# Copia o src completo
scp -P "$WFDB01_PORT" -rq \
    src/ \
    scripts/analyze_n8n_performance.py \
    "${WFDB01_USER}@${WFDB01_HOST}:${REMOTE_WORKDIR}/"

# ── 4. Instala o pacote e cria .env remoto ────────────────────────────────────
log "Instalando n8n_analyzer no venv remoto..."

$SSH_CMD bash <<EOF
set -euo pipefail
cd $REMOTE_WORKDIR
source $REMOTE_VENV/bin/activate

# Instala o pacote em modo editable
pip install --quiet -e .

# Cria .env apontando para endpoints internos
cat > .env <<ENVFILE
PROMETHEUS_URL=$PROMETHEUS_INTERNAL
VICTORIA_METRICS_URL=$VM_INTERNAL
LOKI_URL=$LOKI_INTERNAL
REQUEST_TIMEOUT_SECONDS=120
CORRELATION_WINDOW_SECONDS=30
ENVFILE

echo "Instalação OK: \$(analyze-n8n --help | head -1)"
EOF

# ── 5. Executa a análise ──────────────────────────────────────────────────────
log "Executando analyze-n8n no wfdb01..."
log "  from=$FROM_DATE  to=$TO_DATE  step=$STEP  format=$OUTPUT_FORMAT"

REPORT_FILE=""
REPORT_FILE=$($SSH_CMD bash <<EOF
set -euo pipefail
cd $REMOTE_WORKDIR
source $REMOTE_VENV/bin/activate

python scripts/analyze_n8n_performance.py \
    --from "$FROM_DATE" \
    --to "$TO_DATE" \
    --step-global "$STEP" \
    --output-format "$OUTPUT_FORMAT" \
    --output-dir reports \
    2>&1

# Retorna caminho do relatório mais recente
ls -t $REMOTE_REPORT/n8n_perf_ANA001_*.${OUTPUT_FORMAT} 2>/dev/null | head -1
EOF
)

if [[ -z "$REPORT_FILE" ]]; then
    warn "Nenhum relatório encontrado após execução."
    exit 1
fi

log "Relatório gerado: $REPORT_FILE"

# ── 6. Download do relatório ──────────────────────────────────────────────────
if [[ "$DOWNLOAD_REPORT" == "true" ]]; then
    mkdir -p "$LOCAL_REPORT_DIR"
    log "Baixando relatório para $LOCAL_REPORT_DIR/..."
    scp -P "$WFDB01_PORT" \
        "${WFDB01_USER}@${WFDB01_HOST}:${REPORT_FILE}" \
        "$LOCAL_REPORT_DIR/"
    BASENAME=$(basename "$REPORT_FILE")
    log "✅ Relatório salvo em: $LOCAL_REPORT_DIR/$BASENAME"
fi
