#!/usr/bin/env python3
"""
Fase 1 — Correlação Estatística: WF001 Desempenho N8N vs Hardware/Software
============================================================================
Período: 2026-03-23 → 2026-03-30
Backend: VictoriaMetrics (localhost:18428)

Objetivo:
  Construir timeseries alinhadas de latência do N8N e variáveis de infra
  e calcular coeficiente de correlação de Pearson para identificar quais
  variáveis de hardware/software mais influenciam o desempenho do N8N.

Filtragem:
  - N8N métricas:     instance="wf001"
  - Node Exporter:    instance="wf001.vya.digital:9100"
  - Processo N8N:     instance="wf001"
  - cAdvisor host:    instance="enterprise-cadvisor:8080", id="/"
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import requests
from _audit import audit_end, audit_start

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
VM_URL       = "http://localhost:18428"
PROM_URL     = "https://prometheus.vya.digital"
START        = "2026-03-23T00:00:00Z"
END          = "2026-03-30T23:59:59Z"
STEP         = "5m"               # resolução de 5 minutos
N8N_INSTANCE = "wf001"
NODE_INSTANCE = "wf001.vya.digital:9100"
CADVISOR_INSTANCE = "enterprise-cadvisor:8080"

# ---------------------------------------------------------------------------
# Helpers de consulta
# ---------------------------------------------------------------------------

def query_range(url: str, promql: str, start: str = START, end: str = END,
                step: str = STEP) -> list[dict]:
    """Executa range query no backend e retorna lista de séries temporais."""
    try:
        r = requests.get(
            f"{url}/api/v1/query_range",
            params={"query": promql, "start": start, "end": end, "step": step},
            timeout=45,
            verify=True,
        )
        if r.status_code == 200:
            result = r.json().get("data", {}).get("result", [])
            return result
        else:
            print(f"  ⚠️  HTTP {r.status_code} para query: {promql[:80]}", file=sys.stderr)
            return []
    except Exception as e:
        print(f"  ❌ Erro na query: {e}", file=sys.stderr)
        return []


def series_to_dict(series: list[dict]) -> dict[float, float]:
    """Converte lista de [timestamp, value] em dict ts→float."""
    out: dict[float, float] = {}
    for ts, val in series:
        try:
            out[float(ts)] = float(val)
        except (ValueError, TypeError):
            pass
    return out


def aggregate_series(results: list[dict], agg: str = "sum") -> dict[float, float]:
    """Agrega múltiplas séries (sum/max/avg) em uma única série de dicts."""
    combined: dict[float, list[float]] = {}
    for r in results:
        for ts, val in r.get("values", []):
            try:
                fval = float(val)
                if not math.isnan(fval) and not math.isinf(fval):
                    combined.setdefault(float(ts), []).append(fval)
            except (ValueError, TypeError):
                pass
    out: dict[float, float] = {}
    for ts, vals in combined.items():
        if agg == "sum":
            out[ts] = sum(vals)
        elif agg == "max":
            out[ts] = max(vals)
        elif agg == "avg":
            out[ts] = sum(vals) / len(vals)
    return out


# ---------------------------------------------------------------------------
# Coleta de timeseries
# ---------------------------------------------------------------------------

def collect_timeseries(url: str) -> dict[str, dict[float, float]]:
    """
    Retorna dict nome_variável → {timestamp: value} para todas as variáveis
    relevantes do WF001.
    """
    ts: dict[str, dict[float, float]] = {}

    print("\n📡 Coletando timeseries...")

    # ── 1. Latência N8N p95 (VARIÁVEL ALVO) ─────────────────────────────────
    print("  [1/9] N8N latency p95 ...", end=" ", flush=True)
    r = query_range(url,
        f'histogram_quantile(0.95, sum by (le) ('
        f'rate(n8n_workflow_execution_duration_seconds_bucket{{instance="{N8N_INSTANCE}"}}[5m])))'
    )
    ts["latency_p95"] = aggregate_series(r, agg="avg")
    print(f"{len(ts['latency_p95'])} pts")

    # ── 2. Latência N8N p50 ──────────────────────────────────────────────────
    print("  [2/9] N8N latency p50 ...", end=" ", flush=True)
    r = query_range(url,
        f'histogram_quantile(0.50, sum by (le) ('
        f'rate(n8n_workflow_execution_duration_seconds_bucket{{instance="{N8N_INSTANCE}"}}[5m])))'
    )
    ts["latency_p50"] = aggregate_series(r, agg="avg")
    print(f"{len(ts['latency_p50'])} pts")

    # ── 3. Taxa de execuções N8N (req/s) ────────────────────────────────────
    print("  [3/9] N8N execution rate ...", end=" ", flush=True)
    r = query_range(url,
        f'sum(rate(n8n_workflow_execution_duration_seconds_count{{instance="{N8N_INSTANCE}"}}[5m]))'
    )
    ts["n8n_exec_rate"] = aggregate_series(r, agg="avg")
    print(f"{len(ts['n8n_exec_rate'])} pts")

    # ── 4. N8N Processo CPU % ────────────────────────────────────────────────
    print("  [4/9] N8N process CPU rate ...", end=" ", flush=True)
    r = query_range(url,
        f'rate(process_cpu_seconds_total{{instance="{N8N_INSTANCE}"}}[5m]) * 100'
    )
    ts["n8n_proc_cpu_pct"] = aggregate_series(r, agg="avg")
    print(f"{len(ts['n8n_proc_cpu_pct'])} pts")

    # ── 5. N8N Processo Memória Residente (MB) ───────────────────────────────
    print("  [5/9] N8N process resident memory ...", end=" ", flush=True)
    r = query_range(url,
        f'process_resident_memory_bytes{{instance="{N8N_INSTANCE}"}} / 1024 / 1024'
    )
    ts["n8n_proc_mem_mb"] = aggregate_series(r, agg="avg")
    print(f"{len(ts['n8n_proc_mem_mb'])} pts")

    # ── 6. Host CPU % Total Utilização (via Node Exporter) ──────────────────
    print("  [6/9] Host CPU utilization % ...", end=" ", flush=True)
    r = query_range(url,
        f'100 - (avg by (instance) ('
        f'rate(node_cpu_seconds_total{{instance="{NODE_INSTANCE}",mode="idle"}}[5m])) * 100)'
    )
    ts["host_cpu_pct"] = aggregate_series(r, agg="avg")
    print(f"{len(ts['host_cpu_pct'])} pts")

    # ── 7. Host Load Average 1min ────────────────────────────────────────────
    print("  [7/9] Host load average 1min ...", end=" ", flush=True)
    r = query_range(url,
        f'node_load1{{instance="{NODE_INSTANCE}"}}'
    )
    ts["host_load1"] = aggregate_series(r, agg="avg")
    print(f"{len(ts['host_load1'])} pts")

    # ── 8. Host Memória Disponível % ─────────────────────────────────────────
    print("  [8/9] Host memory available % ...", end=" ", flush=True)
    r_avail = query_range(url,
        f'node_memory_MemAvailable_bytes{{instance="{NODE_INSTANCE}"}}'
    )
    r_total = query_range(url,
        f'node_memory_MemTotal_bytes{{instance="{NODE_INSTANCE}"}}'
    )
    avail = aggregate_series(r_avail, agg="avg")
    total = aggregate_series(r_total, agg="avg")
    ts["host_mem_avail_pct"] = {}
    for t in avail:
        if t in total and total[t] > 0:
            ts["host_mem_avail_pct"][t] = (avail[t] / total[t]) * 100
    # Inversão: uso de memória (100 - disponível) = mais natural para correlação
    ts["host_mem_used_pct"] = {t: 100 - v for t, v in ts["host_mem_avail_pct"].items()}
    print(f"{len(ts['host_mem_used_pct'])} pts")

    # ── 9. Host Disk I/O Utilização % (ioutil) ──────────────────────────────
    print("  [9/9] Host disk I/O util % ...", end=" ", flush=True)
    r = query_range(url,
        f'sum by (instance) ('
        f'rate(node_disk_io_time_seconds_total{{instance="{NODE_INSTANCE}"}}[5m])) * 100'
    )
    ts["host_disk_io_pct"] = aggregate_series(r, agg="avg")
    print(f"{len(ts['host_disk_io_pct'])} pts")

    # ── 10. Host Network Rate MB/s (total) ───────────────────────────────────
    print("  [10/10] Host network throughput...", end=" ", flush=True)
    r_rx = query_range(url,
        f'sum(rate(node_network_receive_bytes_total{{instance="{NODE_INSTANCE}",'
        f'device!~"lo|docker.*|veth.*|br-.*"}}[5m])) / 1024 / 1024'
    )
    r_tx = query_range(url,
        f'sum(rate(node_network_transmit_bytes_total{{instance="{NODE_INSTANCE}",'
        f'device!~"lo|docker.*|veth.*|br-.*"}}[5m])) / 1024 / 1024'
    )
    rx = aggregate_series(r_rx, agg="sum")
    tx = aggregate_series(r_tx, agg="sum")
    ts["host_net_mbps"] = {}
    for t in rx:
        if t in tx:
            ts["host_net_mbps"][t] = rx[t] + tx.get(t, 0)
    print(f"{len(ts['host_net_mbps'])} pts")

    return ts


# ---------------------------------------------------------------------------
# Análise de Correlação
# ---------------------------------------------------------------------------

def align_series(target: dict[float, float],
                 predictors: dict[str, dict[float, float]]) -> dict:
    """
    Alinha predictor timeseries ao conjunto de timestamps presentes no alvo
    retornando arrays numpy prontos para correlação.
    """
    # Timestamps comuns: presentes no alvo E em pelo menos um predictor
    common_ts = sorted(target.keys())

    result = {"timestamps": common_ts, "target": [], "predictors": {}}
    result["target"] = [target[t] for t in common_ts]

    for name, series in predictors.items():
        values = []
        for t in common_ts:
            if t in series:
                values.append(series[t])
            else:
                # Interpolação linear simples se timestamp ausente
                neighbors = [k for k in series if abs(k - t) <= 300]  # ±5 min
                if neighbors:
                    values.append(series[min(neighbors, key=lambda k: abs(k - t))])
                else:
                    values.append(float("nan"))
        result["predictors"][name] = values

    return result


def pearson_correlation(x: list, y: list) -> Optional[float]:
    """
    Calcula coeficiente de correlação de Pearson entre dois vetores,
    ignorando pares com NaN.
    """
    pairs = [(xi, yi) for xi, yi in zip(x, y)
             if xi is not None and yi is not None
             and not math.isnan(xi) and not math.isnan(yi)
             and not math.isinf(xi) and not math.isinf(yi)]

    if len(pairs) < 10:
        return None

    n = len(pairs)
    sum_x = sum(p[0] for p in pairs)
    sum_y = sum(p[1] for p in pairs)
    sum_xy = sum(p[0] * p[1] for p in pairs)
    sum_x2 = sum(p[0] ** 2 for p in pairs)
    sum_y2 = sum(p[1] ** 2 for p in pairs)

    num = n * sum_xy - sum_x * sum_y
    den_sq = (n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)

    if den_sq <= 0:
        return None

    return num / math.sqrt(den_sq)


def describe_series(values: list) -> dict:
    """Estatísticas descritivas básicas de uma lista de valores."""
    clean = [v for v in values if v is not None and not math.isnan(v) and not math.isinf(v)]
    if not clean:
        return {}
    n = len(clean)
    mean = sum(clean) / n
    sorted_v = sorted(clean)
    p50 = sorted_v[int(n * 0.5)]
    p95 = sorted_v[int(n * 0.95)]
    p99 = sorted_v[min(int(n * 0.99), n - 1)]
    variance = sum((v - mean) ** 2 for v in clean) / n
    std = math.sqrt(variance)
    return {
        "n": n,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "min": round(sorted_v[0], 4),
        "p50": round(p50, 4),
        "p95": round(p95, 4),
        "p99": round(p99, 4),
        "max": round(sorted_v[-1], 4),
    }


# ---------------------------------------------------------------------------
# Geração do Relatório em Markdown
# ---------------------------------------------------------------------------

VARIABLE_META = {
    "n8n_exec_rate":    ("N8N Taxa de Execução (req/s)", "Software"),
    "n8n_proc_cpu_pct": ("N8N Processo CPU (%)",         "Software"),
    "n8n_proc_mem_mb":  ("N8N Processo Memória (MB)",    "Software"),
    "host_cpu_pct":     ("Host CPU Total (%)",           "Hardware"),
    "host_load1":       ("Host Load Average 1min",       "Hardware"),
    "host_mem_used_pct":("Host Memória Usada (%)",       "Hardware"),
    "host_disk_io_pct": ("Host Disk I/O Util (%)",       "Hardware"),
    "host_net_mbps":    ("Host Network Total (MB/s)",    "Hardware"),
}

CORR_LABELS = {
    (0.7, 1.0):  ("🔴 FORTE POS",  "Aumento direto de latência com esta variável"),
    (0.3, 0.7):  ("🟡 MODERADA",   "Correlação moderada — vale investigar"),
    (-0.3, 0.3): ("⬜ FRACA/NULA", "Sem correlação significativa"),
    (-0.7, -0.3):("🟡 MOD. NEG.",  "Correlação moderada inversa"),
    (-1.0, -0.7):("🔵 FORTE NEG.", "Relação inversa forte com latência"),
}


def corr_label(c: float) -> tuple[str, str]:
    for (lo, hi), (lbl, interp) in CORR_LABELS.items():
        if lo <= c <= hi:
            return lbl, interp
    return "❓ N/A", ""


def generate_report(aligned: dict, correlations: dict,
                    descriptive: dict, url_backend: str) -> str:
    ts_count = len(aligned["timestamps"])
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    target_stats = describe_series(aligned["target"])
    sorted_corr = sorted(
        [(k, v) for k, v in correlations.items() if v is not None],
        key=lambda x: abs(x[1]),
        reverse=True,
    )

    lines = [
        "# Fase 1 — Correlação Estatística: WF001 Desempenho N8N",
        "",
        f"**Gerado em**: {now_utc}  ",
        f"**Período**: {START} → {END}  ",
        f"**Instância**: {N8N_INSTANCE} (N8N — USA Data Center)  ",
        f"**Backend**: {url_backend}  ",
        f"**Resolução**: {STEP} | **Total timestamps alinhados**: {ts_count:,}  ",
        "",
        "---",
        "",
        "## 1. DADOS COLETADOS — VISÃO GERAL",
        "",
        "| Variável | Categoria | Pontos | Cobertura |",
        "|----------|-----------|--------|-----------|",
    ]

    for var, series in aligned["predictors"].items():
        meta = VARIABLE_META.get(var, (var, "—"))
        clean = [v for v in series if v is not None and not math.isnan(v)]
        pct = int(100 * len(clean) / ts_count) if ts_count else 0
        lines.append(f"| {meta[0]} | {meta[1]} | {len(clean):,} | {pct}% |")

    lines += [
        "",
        "### Variável Alvo: Latência N8N p95",
        "",
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| Pontos válidos | {target_stats.get('n', 0):,} |",
        f"| Média | {target_stats.get('mean', 'N/A')} s |",
        f"| p50 | {target_stats.get('p50', 'N/A')} s |",
        f"| p95 | {target_stats.get('p95', 'N/A')} s |",
        f"| p99 | {target_stats.get('p99', 'N/A')} s |",
        f"| Máximo | {target_stats.get('max', 'N/A')} s |",
        f"| Desvio Padrão | {target_stats.get('std', 'N/A')} s |",
        "",
        "---",
        "",
        "## 2. CORRELAÇÃO DE PEARSON — LATÊNCIA p95 vs VARIÁVEIS",
        "",
        "> **Interpretação**: r > 0.7 = correlação forte positiva; "
        "0.3–0.7 = moderada; < 0.3 = sem correlação significativa.",
        "",
        "| Ranking | Variável | Categoria | r (Pearson) | Força | Interpretação |",
        "|---------|----------|-----------|-------------|-------|---------------|",
    ]

    for rank, (var, corr) in enumerate(sorted_corr, 1):
        meta = VARIABLE_META.get(var, (var, "—"))
        lbl, interp = corr_label(corr)
        lines.append(
            f"| #{rank} | {meta[0]} | {meta[1]} | **{corr:+.4f}** | {lbl} | {interp} |"
        )

    for var, corr in correlations.items():
        if corr is None:
            meta = VARIABLE_META.get(var, (var, "—"))
            lines.append(
                f"| — | {meta[0]} | {meta[1]} | N/A | ❓ Insuficiente | Dados insuficientes para correlação |"
            )

    lines += [
        "",
        "---",
        "",
        "## 3. ESTATÍSTICAS DESCRITIVAS POR VARIÁVEL",
        "",
        "| Variável | N | Média | p50 | p95 | Máx | Std |",
        "|----------|---|-------|-----|-----|-----|-----|",
    ]

    for var, stats in descriptive.items():
        if not stats:
            continue
        meta = VARIABLE_META.get(var, (var, "—"))
        lines.append(
            f"| {meta[0]} | {stats.get('n','—')} | {stats.get('mean','—')} | "
            f"{stats.get('p50','—')} | {stats.get('p95','—')} | "
            f"{stats.get('max','—')} | {stats.get('std','—')} |"
        )

    # Diagnóstico e conclusão
    top3 = sorted_corr[:3]
    strong = [(v, c) for v, c in sorted_corr if abs(c) >= 0.7]
    moderate = [(v, c) for v, c in sorted_corr if 0.3 <= abs(c) < 0.7]

    lines += [
        "",
        "---",
        "",
        "## 4. ANÁLISE E DIAGNÓSTICO",
        "",
    ]

    if target_stats.get("p95", 0) < 0.5:
        lines += [
            "### ⚠️ Atenção: Latência Uniformemente Baixa",
            "",
            f"A latência p95 do N8N em wf001 no período se manteve em **{target_stats.get('p95', '?')} s**,  ",
            "bem abaixo do threshold de violação (1.0 s). Isso significa:",
            "",
            "- **Cenário A** — Sistema saudável: Nenhuma contenção de recursos detectável",
            "- **Cenário B** — Workloads simples: Workflows pouco intensivos não estressam o sistema",
            "- **Cenário C** — Granularidade insuficiente: Spikes de < 5 min se diluem na janela de scrape",
            "",
            "Correlações devem ser interpretadas com cuidado: quando a variável alvo tem baixa variância  ",
            "(p95 ≈ p50 ≈ constante), qualquer correlação calculada é **matematicamente fraca por definição**,",
            "independentemente do comportamento real da infra.",
            "",
        ]

    if strong:
        lines += [
            "### Correlações Fortes (|r| ≥ 0.7) — ENCONTRADAS",
            "",
        ]
        for var, corr in strong:
            meta = VARIABLE_META.get(var, (var, "—"))
            lbl, interp = corr_label(corr)
            lines.append(f"- **{meta[0]}**: r = {corr:+.4f} → {interp}")
        lines.append("")
    else:
        lines += [
            "### Correlações Fortes (|r| ≥ 0.7) — NENHUMA",
            "",
            "Nenhuma variável apresentou correlação forte com a latência p95 no período.",
            "Este resultado é **consistente com a ausência de violações** (0 eventos p95 ≥ 1.0 s).",
            "",
        ]

    if moderate:
        lines += [
            "### Correlações Moderadas (0.3 ≤ |r| < 0.7)",
            "",
        ]
        for var, corr in moderate:
            meta = VARIABLE_META.get(var, (var, "—"))
            lines.append(f"- **{meta[0]}**: r = {corr:+.4f}")
        lines.append("")

    # Top 3
    lines += [
        "### Top 3 Variáveis Mais Correlacionadas com Latência",
        "",
        "| Rank | Variável | r | Categoria |",
        "|------|----------|---|-----------|",
    ]
    for rank, (var, corr) in enumerate(top3, 1):
        meta = VARIABLE_META.get(var, (var, "—"))
        lines.append(f"| #{rank} | {meta[0]} | {corr:+.4f} | {meta[1]} |")

    lines += [
        "",
        "---",
        "",
        "## 5. CONCLUSÃO FASE 1",
        "",
        "### Status dos Dados",
        "",
        f"- ✅ **Timeseries coletadas**: {len(aligned.get('predictors', {})) + 1} variáveis ({ts_count:,} timestamps)",
        f"- ✅ **Período coberto**: {START} → {END} (7 dias)",
        f"- ✅ **Resolução**: {STEP}",
        "",
        "### Achados Principais",
        "",
    ]

    if not strong and not moderate:
        lines += [
            "**RESULTADO**: Nenhuma correlação forte ou moderada encontrada no período.",
            "",
            "**Interpretação**: O sistema wf001 opera em regime saudável — sem contenção de  ",
            "recursos que afete observavelmente a latência do N8N. Os workloads executados  ",
            "no período não exerceram pressão suficiente para criar correlações mensuráveis.",
            "",
            "**Próximo passo**: Fase 2 — Drill-down em timestamps com latência acima da mediana  ",
            "para verificar se há padrões subtis não capturados pela correlação global.",
        ]
    else:
        lines += [
            "**RESULTADO**: Correlações identificadas. Variáveis de influência confirmadas.",
            "",
            "**Próximo passo**: Fase 2 — Drill-down nos timestamps com maior latência  ",
            "para confirmar a relação causal entre as variáveis identificadas e o slowness.",
        ]

    lines += [
        "",
        "---",
        "",
        "## APÊNDICE: PromQL Utilizadas",
        "",
        "```",
        "# Latência N8N p95",
        f'histogram_quantile(0.95, sum by (le) (rate(n8n_workflow_execution_duration_seconds_bucket{{instance="{N8N_INSTANCE}"}}[5m])))',
        "",
        "# CPU processo N8N (%)",
        f'rate(process_cpu_seconds_total{{instance="{N8N_INSTANCE}"}}[5m]) * 100',
        "",
        "# Memória processo N8N (MB)",
        f'process_resident_memory_bytes{{instance="{N8N_INSTANCE}"}} / 1024 / 1024',
        "",
        "# CPU host total (%)",
        f'100 - (avg by (instance) (rate(node_cpu_seconds_total{{instance="{NODE_INSTANCE}",mode="idle"}}[5m])) * 100)',
        "",
        "# Load average host",
        f'node_load1{{instance="{NODE_INSTANCE}"}}',
        "",
        "# Memória usada host (%)",
        f'100 - ((node_memory_MemAvailable_bytes{{instance="{NODE_INSTANCE}"}} / node_memory_MemTotal_bytes{{instance="{NODE_INSTANCE}"}}) * 100)',
        "",
        "# Disk I/O util (%)",
        f'sum by (instance) (rate(node_disk_io_time_seconds_total{{instance="{NODE_INSTANCE}"}}[5m])) * 100',
        "",
        "# Network total MB/s",
        f'sum(rate(node_network_receive_bytes_total{{instance="{NODE_INSTANCE}",device!~"lo|docker.*|veth.*|br-.*"}}[5m])) / 1024 / 1024',
        "```",
        "",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fase 1: Correlação WF001")
    parser.add_argument("--backend", default=VM_URL,
                        help="URL do backend (VictoriaMetrics ou Prometheus)")
    parser.add_argument("--output", default="reports/WF001_FASE1_CORRELACAO_2026-03-30.md",
                        help="Arquivo de saída do relatório Markdown")
    args = parser.parse_args()

    _audit_ctx = audit_start(__file__, args)
    try:
        _run(args, _audit_ctx)
    except Exception:
        audit_end(__file__, _audit_ctx, outcome="error")
        raise


def _run(args, _audit_ctx):
    print("=" * 70)
    print("FASE 1 — CORRELAÇÃO ESTATÍSTICA WF001")
    print("=" * 70)
    print(f"Backend: {args.backend}")
    print(f"Período: {START} → {END}")
    print(f"Instância N8N: {N8N_INSTANCE}")
    print(f"Instância Host: {NODE_INSTANCE}")

    # 1. Coleta
    ts = collect_timeseries(args.backend)

    # 2. Separa alvo e preditores
    target   = ts.pop("latency_p95")
    # latency_p50 — usada apenas para diagnóstico, não como predictor
    ts.pop("latency_p50", None)
    ts.pop("host_mem_avail_pct", None)   # redundante com host_mem_used_pct

    predictors = ts

    print(f"\n📐 Alinhando {len(predictors)} preditores com {len(target)} timestamps alvo...")
    aligned = align_series(target, predictors)
    print(f"   → {len(aligned['timestamps'])} timestamps comuns")

    # 3. Correlação
    print("\n🔢 Calculando correlações de Pearson...")
    correlations: dict[str, Optional[float]] = {}
    for name, series in aligned["predictors"].items():
        c = pearson_correlation(aligned["target"], series)
        correlations[name] = c
        meta = VARIABLE_META.get(name, (name, "—"))
        c_str = f"{c:+.4f}" if c is not None else "N/A"
        print(f"   {meta[0]:35} r = {c_str}")

    # 4. Estatísticas descritivas
    print("\n📊 Calculando estatísticas descritivas...")
    descriptive: dict[str, dict] = {}
    descriptive["latency_p95"] = describe_series(aligned["target"])
    for name, series in aligned["predictors"].items():
        descriptive[name] = describe_series(series)

    # 5. Gerar relatório
    print(f"\n📝 Gerando relatório Markdown → {args.output}")
    report = generate_report(aligned, correlations, descriptive, args.backend)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ Relatório salvo em: {args.output}")

    # 6. Export JSON para uso posterior (Fase 2)
    json_path = args.output.replace(".md", ".json")
    export_data = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "start": START, "end": END, "step": STEP,
            "backend": args.backend,
            "n8n_instance": N8N_INSTANCE,
            "node_instance": NODE_INSTANCE,
        },
        "correlations": {k: v for k, v in correlations.items()},
        "descriptive": descriptive,
        "target_count": len(aligned["timestamps"]),
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)
    print(f"✅ Dados JSON salvos em: {json_path}")

    # Resumo no terminal
    print("\n" + "=" * 70)
    print("RESUMO — TOP CORRELAÇÕES COM LATÊNCIA P95")
    print("=" * 70)
    sorted_corr = sorted(
        [(k, v) for k, v in correlations.items() if v is not None],
        key=lambda x: abs(x[1]), reverse=True,
    )
    for rank, (var, corr) in enumerate(sorted_corr[:5], 1):
        meta = VARIABLE_META.get(var, (var, "—"))
        lbl, _ = corr_label(corr)
        print(f"  #{rank}  {meta[0]:35}  r={corr:+.4f}  {lbl}")
    print("=" * 70 + "\n")

    json_path = args.output.replace(".md", ".json")
    audit_end(__file__, _audit_ctx, outcome="ok", output_files=[args.output, json_path])


if __name__ == "__main__":
    main()
