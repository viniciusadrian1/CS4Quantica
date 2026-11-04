"""
Sprint 3, Fase 5: avaliacao da solucao integrada.

Mede de ponta a ponta, com leituras reais do dataset:
  1. Latência do serviço de inferência (in-process): p50/p95 por rota
  2. Latência HTTP da API (round-trip completo, se estiver no ar)
  3. Teste de carga: throughput e latência sob concorrência (se a API estiver no ar)
  4. Custos de treino e recursos quânticos (de models/metrics.json)

Saída: relatorio/avaliacao_integrada.json

Uso: python evaluate_integration.py   (API opcional em http://127.0.0.1:8000)
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

from common import BRUTO_CSV, SENSOR_COLS, SPRINT3_DIR
from inference import HybridInferenceService

API_URL = "http://127.0.0.1:8000"
N_POINT = 200
N_HTTP = 50


def pct(values, p):
    return round(float(np.percentile(values, p)), 3)


def stats(values):
    return {"p50_ms": pct(values, 50), "p95_ms": pct(values, 95),
            "media_ms": round(float(np.mean(values)), 3), "n": len(values)}


def main():
    df = pd.read_csv(BRUTO_CSV)
    # Mistura: metade operação normal, metade anomalias injetadas
    rows_anom = df[df["label_anomalia"] == 1].sample(N_POINT // 2, random_state=42)
    rows_norm = df[(df["label_anomalia"] == 0) & (df["ciclo_operacao"] == "normal")].sample(
        N_POINT // 2, random_state=42)
    rows = pd.concat([rows_norm, rows_anom]).sample(frac=1.0, random_state=42)
    leituras_list = [{c: float(r[c]) for c in SENSOR_COLS} for _, r in rows.iterrows()]

    svc = HybridInferenceService()
    out = {"config": {"n_pontual": N_POINT, "n_http": N_HTTP,
                      "fonte": "dataset_motor_sprint2_bruto.csv (50% anômalas)"}}

    # ── 1. Serviço in-process ────────────────────────────────────────
    print("[1/3] Latências in-process …")
    lat = {"anomalia_classico": [], "anomalia_quantico": [],
           "manutencao_classico": [], "manutencao_quantico": []}
    acertos = {"classico": 0, "quantico": 0}
    y_true = rows["label_anomalia"].values

    for i, leituras in enumerate(leituras_list):
        completed, _ = svc.validate_and_impute(leituras)
        svc.push_reading("bench", completed)

        t0 = time.perf_counter()
        r_ac = svc.predict_anomaly_classical(completed)
        lat["anomalia_classico"].append((time.perf_counter() - t0) * 1000)
        acertos["classico"] += int(r_ac["anomalia"] == bool(y_true[i]))

        t0 = time.perf_counter()
        r_aq = svc.predict_anomaly_quantum("bench")
        if r_aq is not None:
            lat["anomalia_quantico"].append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        svc.predict_maintenance("bench", completed, use_quantum=False)
        lat["manutencao_classico"].append((time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        svc.predict_maintenance("bench", completed, use_quantum=True)
        lat["manutencao_quantico"].append((time.perf_counter() - t0) * 1000)

    out["latencia_inferencia_in_process"] = {k: stats(v) for k, v in lat.items()}
    out["sanidade_acuracia_pontual_classico"] = round(acertos["classico"] / N_POINT, 3)
    print(f"      clássico {stats(lat['anomalia_classico'])['p50_ms']} ms p50 · "
          f"QSVC {stats(lat['anomalia_quantico'])['p50_ms']} ms p50 · "
          f"VQC {stats(lat['manutencao_quantico'])['p50_ms']} ms p50")

    # ── 2. API HTTP ──────────────────────────────────────────────────
    print("[2/3] Latências HTTP (API) …")
    try:
        import requests

        requests.get(f"{API_URL}/health", timeout=3)
        http_lat = {}
        for modelo in ["classico", "quantico", "ambos"]:
            # warm-up: enche o buffer do equipamento (janela quântica exige 10
            # leituras) antes de cronometrar. Senao as 9 primeiras medem um no-op
            for leituras in leituras_list[:10]:
                requests.post(f"{API_URL}/predict", timeout=30, json={
                    "equipamento_id": f"bench-http-{modelo}",
                    "leituras": leituras, "modelo": "classico"})
            vals = []
            for leituras in leituras_list[:N_HTTP]:
                t0 = time.perf_counter()
                resp = requests.post(f"{API_URL}/predict", timeout=30, json={
                    "equipamento_id": f"bench-http-{modelo}",
                    "leituras": leituras, "modelo": modelo})
                resp.raise_for_status()
                vals.append((time.perf_counter() - t0) * 1000)
            http_lat[modelo] = stats(vals)
            print(f"      modelo={modelo}: p50 {http_lat[modelo]['p50_ms']} ms")
        out["latencia_api_http"] = http_lat
    except Exception as exc:
        out["latencia_api_http"] = f"API indisponível ({exc})"
        print(f"      API indisponivel, pulando ({exc})")

    # ── 3. Teste de carga (concorrência real contra a API) ────────────
    print("[3/4] Teste de carga (concorrência) …")
    try:
        import requests

        requests.get(f"{API_URL}/health", timeout=3)

        def _one_call(i):
            leituras = leituras_list[i % len(leituras_list)]
            t0 = time.perf_counter()
            resp = requests.post(f"{API_URL}/predict", timeout=30, json={
                "equipamento_id": f"loadtest-{i % 8}",
                "leituras": leituras, "modelo": "classico"})
            ok = resp.status_code == 200
            return (time.perf_counter() - t0) * 1000, ok

        load_results = {}
        for concurrency in [1, 5, 20]:
            n_requests = max(40, concurrency * 4)
            t_start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                results_lc = list(pool.map(_one_call, range(n_requests)))
            wall_s = time.perf_counter() - t_start
            lats = [r[0] for r in results_lc]
            oks = sum(1 for r in results_lc if r[1])
            load_results[f"concorrencia_{concurrency}"] = {
                **stats(lats),
                "throughput_req_s": round(n_requests / wall_s, 2),
                "taxa_sucesso": round(oks / n_requests, 3),
                "n_requests": n_requests,
            }
            print(f"      concorrencia={concurrency}: "
                  f"{load_results[f'concorrencia_{concurrency}']['throughput_req_s']} req/s, "
                  f"p50 {load_results[f'concorrencia_{concurrency}']['p50_ms']} ms, "
                  f"sucesso {load_results[f'concorrencia_{concurrency}']['taxa_sucesso']:.0%}")
        out["teste_de_carga_classico"] = load_results
    except Exception as exc:
        out["teste_de_carga_classico"] = f"API indisponivel ({exc})"
        print(f"      API indisponivel, pulando teste de carga ({exc})")

    # ── 4. Custos de treino + recursos quânticos ─────────────────────
    print("[4/4] Consolidando custos de treino …")
    with open(SPRINT3_DIR / "models" / "metrics.json", encoding="utf-8") as f:
        metrics = json.load(f)
    out["custo_treino_s"] = {
        cen: {m: v["fit_s"] for m, v in metrics[cen].items()}
        for cen in ["cenario1_anomalia", "cenario2_manutencao"]
    }
    out["recursos_quanticos"] = metrics["recursos_quanticos"]
    out["metricas_holdout"] = metrics

    dest = SPRINT3_DIR / "relatorio" / "avaliacao_integrada.json"
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"OK: {dest}")


if __name__ == "__main__":
    main()
