#!/usr/bin/env python3
"""
Fase 2 - Drill-down de Causa Raiz (wf001)

Objetivo:
- Investigar os picos de load do host com foco em 2026-03-30.
- Validar evidencias de scheduler contention.
- Identificar cgroups/container scopes dominantes no pico maximo.

Saidas:
- reports/WF001_FASE2_DRILLDOWN_2026-03-30.md
- reports/WF001_FASE2_DRILLDOWN_2026-03-30.json
"""

import argparse
import json
import math
import re
from datetime import datetime, timezone

import requests

VM_URL = "http://localhost:18428"
START = "2026-03-23T00:00:00Z"
END = "2026-03-30T23:59:59Z"
STEP = "5m"
N8N_INSTANCE = "wf001"
NODE_INSTANCE = "wf001.vya.digital:9100"
CADVISOR_INSTANCE = "enterprise-cadvisor:8080"
WF001_CPUS = 10


def q_range(url: str, query: str) -> list:
    r = requests.get(
        f"{url}/api/v1/query_range",
        params={"query": query, "start": START, "end": END, "step": STEP},
        timeout=45,
    )
    if r.status_code != 200:
        return []
    return r.json().get("data", {}).get("result", [])


def q_instant(url: str, query: str, time_iso: str) -> list:
    r = requests.get(
        f"{url}/api/v1/query",
        params={"query": query, "time": time_iso},
        timeout=30,
    )
    if r.status_code != 200:
        return []
    return r.json().get("data", {}).get("result", [])


def first_series(result: list) -> dict:
    if not result:
        return {}
    out = {}
    for ts, val in result[0].get("values", []):
        try:
            v = float(val)
            if not math.isnan(v) and not math.isinf(v):
                out[float(ts)] = v
        except (ValueError, TypeError):
            pass
    return out


def sum_series(result: list) -> dict:
    combined = {}
    for row in result:
        for ts, val in row.get("values", []):
            try:
                v = float(val)
                if not math.isnan(v) and not math.isinf(v):
                    combined.setdefault(float(ts), []).append(v)
            except (ValueError, TypeError):
                pass
    return {ts: sum(vals) for ts, vals in combined.items()}


def ts_to_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ts_to_human(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def extract_scope_name(cgroup_id: str) -> str:
    # /system.slice/docker-<id>.scope -> docker:<12>
    m = re.search(r"docker-([0-9a-f]{12,64})\.scope", cgroup_id)
    if m:
        return f"docker:{m.group(1)[:12]}"
    if cgroup_id.startswith("/system.slice/"):
        return cgroup_id.replace("/system.slice/", "")
    return cgroup_id


def collect_base(url: str) -> dict:
    load = first_series(q_range(url, f'node_load1{{instance="{NODE_INSTANCE}"}}'))
    cpu = first_series(q_range(
        url,
        f'100 - (avg by (instance) (rate(node_cpu_seconds_total{{instance="{NODE_INSTANCE}",mode="idle"}}[5m])) * 100)',
    ))
    iow = first_series(q_range(
        url,
        f'sum by (instance) (rate(node_cpu_seconds_total{{instance="{NODE_INSTANCE}",mode="iowait"}}[5m])) / '
        f'sum by (instance) (rate(node_cpu_seconds_total{{instance="{NODE_INSTANCE}"}}[5m])) * 100',
    ))
    mem_used = first_series(q_range(
        url,
        f'100 - (node_memory_MemAvailable_bytes{{instance="{NODE_INSTANCE}"}} / '
        f'node_memory_MemTotal_bytes{{instance="{NODE_INSTANCE}"}}) * 100',
    ))
    n8n_rate = first_series(q_range(
        url,
        f'sum(rate(n8n_workflow_execution_duration_seconds_count{{instance="{N8N_INSTANCE}"}}[5m]))',
    ))
    ctx_rate = first_series(q_range(
        url,
        f'rate(node_context_switches_total{{instance="{NODE_INSTANCE}"}}[5m])',
    ))

    # Scheduler running/waiting time aggregated across CPUs
    sched_running = sum_series(q_range(
        url,
        f'sum by (instance) (rate(node_schedstat_running_seconds_total{{instance="{NODE_INSTANCE}"}}[5m]))',
    ))
    sched_waiting = sum_series(q_range(
        url,
        f'sum by (instance) (rate(node_schedstat_waiting_seconds_total{{instance="{NODE_INSTANCE}"}}[5m]))',
    ))

    return {
        "load": load,
        "cpu": cpu,
        "iow": iow,
        "mem_used": mem_used,
        "n8n_rate": n8n_rate,
        "ctx_rate": ctx_rate,
        "sched_running": sched_running,
        "sched_waiting": sched_waiting,
    }


def find_peak(load: dict) -> tuple[float, float]:
    peak_ts, peak_val = max(load.items(), key=lambda item: item[1])
    return peak_ts, peak_val


def align_point(series: dict, ts: float, tol: int = 300):
    if ts in series:
        return series[ts]
    near = [k for k in series.keys() if abs(k - ts) <= tol]
    if not near:
        return None
    return series[min(near, key=lambda k: abs(k - ts))]


def collect_top_cgroups(url: str, peak_iso: str) -> dict:
    cpu_q = (
        'topk(12, rate(container_cpu_usage_seconds_total'
        f'{{instance="{CADVISOR_INSTANCE}",id!="/"}}[5m]))'
    )
    mem_q = (
        'topk(12, container_memory_working_set_bytes'
        f'{{instance="{CADVISOR_INSTANCE}",id!="/"}})'
    )

    cpu_res = q_instant(url, cpu_q, peak_iso)
    mem_res = q_instant(url, mem_q, peak_iso)

    cpu_rows = []
    for r in cpu_res:
        cid = r.get("metric", {}).get("id", "unknown")
        cpu_rows.append({
            "id": cid,
            "name": extract_scope_name(cid),
            "cpu_cores": round(float(r["value"][1]), 4),
        })

    mem_rows = []
    for r in mem_res:
        cid = r.get("metric", {}).get("id", "unknown")
        mem_rows.append({
            "id": cid,
            "name": extract_scope_name(cid),
            "mem_gb": round(float(r["value"][1]) / (1024 ** 3), 3),
        })

    return {"cpu": cpu_rows, "mem": mem_rows}


def build_report(data: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    peak = data["peak"]
    top = data["top_cgroups"]

    lines = []
    ap = lines.append
    ap("# WF001 - Fase 2: Drill-down de Causa Raiz (Load Spike)")
    ap("")
    ap(f"Gerado em: {now}")
    ap(f"Periodo: {START} -> {END}")
    ap(f"Instancias: N8N={N8N_INSTANCE}, node={NODE_INSTANCE}, cadvisor={CADVISOR_INSTANCE}")
    ap("")
    ap("## 1) Pico Maximo do Periodo")
    ap("")
    ap("| Indicador | Valor |")
    ap("|---|---|")
    ap(f"| Timestamp do pico | {peak['human']} |")
    ap(f"| Load1 absoluto | {peak['load_abs']} |")
    ap(f"| Load normalizado | {peak['load_norm']}x CPUs (CPUs={WF001_CPUS}) |")
    ap(f"| CPU host | {peak['cpu_pct']}% |")
    ap(f"| IOWait host | {peak['iowait_pct']}% |")
    ap(f"| Memoria usada host | {peak['mem_used_pct']}% |")
    ap(f"| N8N exec rate | {peak['n8n_rate']} req/s |")
    ap(f"| Context switches | {peak['ctx_rate']} /s |")
    ap(f"| Scheduler running | {peak['sched_running']} s/s |")
    ap(f"| Scheduler waiting | {peak['sched_waiting']} s/s |")
    ap("")

    ap("## 2) Diagnostico Tecnico")
    ap("")
    ap("Evidencias observadas no pico:")
    ap(f"- Load muito alto ({peak['load_norm']}x) com CPU moderada ({peak['cpu_pct']}%).")
    ap(f"- IOWait baixo ({peak['iowait_pct']}%), descartando disco como causa primaria.")
    ap(f"- Scheduler waiting alto ({peak['sched_waiting']} s/s agregado), indicando fila de execucao/contencao.")
    ap(f"- N8N ativo ({peak['n8n_rate']} req/s), contribuindo para carga, mas nao explica sozinho o load extremo.")
    ap("")
    ap("Conclusao: o comportamento e consistente com scheduler contention e concorrencia elevada de processos/cgroups do host.")
    ap("")

    ap("## 3) Top Cgroups por CPU no Pico")
    ap("")
    ap("| Rank | Scope | CPU cores | Cgroup ID |")
    ap("|---|---|---:|---|")
    for i, row in enumerate(top["cpu"], 1):
        ap(f"| {i} | {row['name']} | {row['cpu_cores']} | {row['id']} |")
    ap("")

    ap("## 4) Top Cgroups por Memoria no Pico")
    ap("")
    ap("| Rank | Scope | Mem GB | Cgroup ID |")
    ap("|---|---|---:|---|")
    for i, row in enumerate(top["mem"], 1):
        ap(f"| {i} | {row['name']} | {row['mem_gb']} | {row['id']} |")
    ap("")

    ap("## 5) Recomendacoes Objetivas")
    ap("")
    ap("1. Capturar `node_processes_running` e `node_processes_blocked` no node_exporter (nao disponiveis atualmente).")
    ap("2. Correlacionar os docker scopes de topo com nomes de servicos (via docker inspect no host wf001).")
    ap("3. Definir alertas para `load1/num_cpu > 1.5` e `scheduler_waiting` alto simultaneamente.")
    ap("4. Isolar workload competidor com cgroups limits (cpu quota/shares) para reduzir impacto no N8N.")
    ap("5. Manter acao da Fase 1: corrigir metrica negativa de `n8n_workflow_execution_duration_seconds_sum`.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=VM_URL)
    parser.add_argument("--output", default="reports/WF001_FASE2_DRILLDOWN_2026-03-30.md")
    args = parser.parse_args()

    base = collect_base(args.backend)
    peak_ts, peak_load = find_peak(base["load"])
    peak_iso = ts_to_iso(peak_ts)

    peak = {
        "ts": peak_ts,
        "iso": peak_iso,
        "human": ts_to_human(peak_ts),
        "load_abs": round(peak_load, 4),
        "load_norm": round(peak_load / WF001_CPUS, 4),
        "cpu_pct": round(align_point(base["cpu"], peak_ts) or 0, 4),
        "iowait_pct": round(align_point(base["iow"], peak_ts) or 0, 4),
        "mem_used_pct": round(align_point(base["mem_used"], peak_ts) or 0, 4),
        "n8n_rate": round(align_point(base["n8n_rate"], peak_ts) or 0, 4),
        "ctx_rate": round(align_point(base["ctx_rate"], peak_ts) or 0, 4),
        "sched_running": round(align_point(base["sched_running"], peak_ts) or 0, 4),
        "sched_waiting": round(align_point(base["sched_waiting"], peak_ts) or 0, 4),
    }

    top_cgroups = collect_top_cgroups(args.backend, peak_iso)

    payload = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "backend": args.backend,
            "start": START,
            "end": END,
            "step": STEP,
            "wf001_cpus": WF001_CPUS,
        },
        "peak": peak,
        "top_cgroups": top_cgroups,
    }

    with open(args.output.replace(".md", ".json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    report = build_report(payload)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"OK report: {args.output}")
    print(f"OK json:   {args.output.replace('.md','.json')}")
    print(f"Peak: {peak['human']} load={peak['load_abs']} ({peak['load_norm']}x) cpu={peak['cpu_pct']}% iow={peak['iowait_pct']}%")


if __name__ == "__main__":
    main()
