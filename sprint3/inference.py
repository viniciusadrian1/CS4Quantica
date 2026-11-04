"""
Sprint 3, Fase 2: servico de inferencia hibrida (classico e quantico).

HybridInferenceService carrega os artefatos de models/ no boot e expõe
predição unitária para os dois cenários:

  Cenário 1 (anomalia)   : clássico pontual (1 leitura) OU quântico janelado
                           (buffer das ultimas 10 leituras, QSVC+Amplitude)
  Cenário 2 (manutenção) : clássico RF (13 features: 9 sensores + 4 rolantes
                           do buffer de 20 leituras) OU quântico VQC (QNN
                           reconstruída + pesos persistidos)

Validação na fronteira: faixas físicas por sensor (rejeita leituras impossíveis),
imputação sinalizada de sensores opcionais e clip [-π,π] pré-encoding quântico.
"""

import json
import threading
import time
from collections import defaultdict, deque

import joblib
import numpy as np

from common import (
    MAINT_FEATURES,
    MAINTENANCE_CLASSES,
    MODELS_DIR,
    OPTIONAL_SENSORS,
    PHYSICAL_RANGES,
    REQUIRED_SENSORS,
    ROLLING_FEATURES,
    RPM_PARADA,
    SENSOR_COLS,
    W_ROLL,
    WINDOW_SIZE,
    build_maintenance_qnn,
    clip_to_pi,
    rolling_features_from_buffer,
)

CLASSICAL_ANOMALY_MODELS = ["gradient_boosting", "random_forest", "mlp", "svm_rbf"]
DEFAULT_CLASSICAL = "gradient_boosting"  # recomendação do Sprint 2 p/ triagem


class ValidationError(ValueError):
    """Leitura fora da faixa física ou sensor obrigatório ausente."""


class HybridInferenceService:
    def __init__(self, models_dir=MODELS_DIR):
        self.models_dir = models_dir
        self.preproc = joblib.load(models_dir / "preproc_pontual.joblib")
        self.preproc_man = joblib.load(models_dir / "preproc_manutencao.joblib")
        self.anomaly_clf = {
            name: joblib.load(models_dir / f"anomalia_{name}.joblib")
            for name in CLASSICAL_ANOMALY_MODELS
        }
        self.rf_man = joblib.load(models_dir / "manutencao_random_forest.joblib")

        # Caminho normal: joblib do pipeline. Fallback (se o dump falhou no treino
        # por incompatibilidade de versão): re-fit determinístico no boot a partir
        # dos dados salvos em anomalia_qsvc_refit.npz.
        try:
            qsvc_bundle = joblib.load(models_dir / "anomalia_qsvc_amplitude.joblib")
            self.qsvc_pipe = qsvc_bundle["pipeline"]
            self.qsvc_platt = qsvc_bundle["platt"]
        except Exception:
            from common import build_amplitude_feature_map, make_hybrid_pipeline

            refit = np.load(models_dir / "anomalia_qsvc_refit.npz")
            self.qsvc_pipe = make_hybrid_pipeline(
                build_amplitude_feature_map(4), n_pca=4, amplitude_encoding=True
            )
            self.qsvc_pipe.fit(refit["X"], refit["y"])
            self.qsvc_platt = joblib.load(models_dir / "anomalia_qsvc_platt.joblib")["platt"]

        vqc_data = np.load(models_dir / "manutencao_vqc.npz", allow_pickle=True)
        self.vqc_weights = vqc_data["weights"]
        self.qnn, _, _ = build_maintenance_qnn()

        with open(models_dir / "imputation_defaults.json", encoding="utf-8") as f:
            self.imputation = json.load(f)
        with open(models_dir / "metrics.json", encoding="utf-8") as f:
            self.metrics = json.load(f)

        # Buffer por equipamento: 20 leituras cobrem a janela quântica (10)
        # e as features rolantes de manutenção (20). Endpoints sync do FastAPI
        # rodam em threadpool → todo acesso ao buffer passa pelo lock.
        self._buffers = defaultdict(lambda: deque(maxlen=W_ROLL))
        self._buffers_lock = threading.Lock()

    # ── Fronteira de entrada ─────────────────────────────────────────
    def validate_and_impute(self, leituras: dict):
        """Valida faixas físicas, imputa sensores opcionais ausentes.
        Retorna (leituras_completas, lista_de_imputados)."""
        missing_req = [s for s in REQUIRED_SENSORS if leituras.get(s) is None]
        if missing_req:
            raise ValidationError(f"Sensores obrigatórios ausentes: {missing_req}")

        completed, imputed = {}, []
        for sensor in SENSOR_COLS:
            value = leituras.get(sensor)
            if value is None:
                completed[sensor] = self.imputation[sensor]
                imputed.append(sensor)
                continue
            value = float(value)
            lo, hi = PHYSICAL_RANGES[sensor]
            if not (lo <= value <= hi):
                raise ValidationError(
                    f"{sensor}={value} fora da faixa física [{lo}, {hi}]"
                )
            completed[sensor] = value
        return completed, imputed

    def push_reading(self, equipamento_id: str, leituras: dict):
        """Adiciona a leitura validada ao buffer do equipamento."""
        with self._buffers_lock:
            self._buffers[equipamento_id].append(leituras)

    def buffer_len(self, equipamento_id: str) -> int:
        with self._buffers_lock:
            return len(self._buffers[equipamento_id])

    def _buffer_snapshot(self, equipamento_id: str) -> list:
        with self._buffers_lock:
            return list(self._buffers[equipamento_id])

    # ── Cenário 1: anomalia ──────────────────────────────────────────
    def predict_anomaly_classical(self, leituras: dict, model=DEFAULT_CLASSICAL):
        if model not in self.anomaly_clf:
            raise ValidationError(
                f"Modelo clássico desconhecido: {model}. Opções: {CLASSICAL_ANOMALY_MODELS}"
            )
        clf = self.anomaly_clf[model]
        x = np.array([[leituras[c] for c in SENSOR_COLS]])
        t0 = time.perf_counter()
        x4 = self.preproc.transform(x)
        proba = float(clf.predict_proba(x4)[0, 1])
        latency = (time.perf_counter() - t0) * 1000.0
        return {
            "anomalia": proba >= 0.5,
            "confianca": round(proba if proba >= 0.5 else 1.0 - proba, 4),
            "score_anomalia": round(proba, 4),
            "modelo": f"classico:{model}",
            "latencia_ms": round(latency, 3),
        }

    def predict_anomaly_quantum(self, equipamento_id=None, janela=None):
        """QSVC+Amplitude sobre janela 10×9. `janela` explícita (lista de 10
        leituras) ou buffer do equipamento; None se buffer insuficiente."""
        if janela is None:
            buf = self._buffer_snapshot(equipamento_id)
            if len(buf) < WINDOW_SIZE:
                return None
            janela = buf[-WINDOW_SIZE:]
        W = np.array([[[r[c] for c in SENSOR_COLS] for r in janela]])
        t0 = time.perf_counter()
        score = float(self.qsvc_pipe.decision_function(W)[0])
        proba = float(self.qsvc_platt.predict_proba([[score]])[0, 1])
        latency = (time.perf_counter() - t0) * 1000.0
        return {
            "anomalia": proba >= 0.5,
            "confianca": round(proba if proba >= 0.5 else 1.0 - proba, 4),
            "score_anomalia": round(proba, 4),
            "modelo": "quantico:qsvc_amplitude (statevector exato/Qiskit, 2 qubits)",
            "latencia_ms": round(latency, 3),
            "janela": f"{WINDOW_SIZE} leituras",
        }

    # ── Cenário 2: manutenção ────────────────────────────────────────
    def _maintenance_vector(self, equipamento_id, leituras):
        """13 features: 9 sensores + 4 rolantes do buffer (inclui a leitura atual)."""
        buf = self._buffer_snapshot(equipamento_id)
        # identidade contra o snapshot inteiro: sob concorrência a leitura pode não
        # ser a ultima do buffer. Checar so buf[-1] a contaria em dobro
        if not any(r is leituras for r in buf):
            buf = buf + [leituras]
        rolls = rolling_features_from_buffer(buf[-W_ROLL:])
        feats = {**leituras, **rolls}
        return np.array([[feats[c] for c in MAINT_FEATURES]]), rolls

    def predict_maintenance(self, equipamento_id: str, leituras: dict, use_quantum=False):
        # Motor parado: regra determinística, sem modelo (rpm ≈ 0 não é degradação)
        if leituras["rpm"] < RPM_PARADA:
            return {
                "risco_manutencao": "parada_programada",
                "confianca": 1.0,
                "probabilidades": None,
                "modelo": "regra:rpm_parada",
                "latencia_ms": 0.0,
            }

        x13, rolls = self._maintenance_vector(equipamento_id, leituras)
        t0 = time.perf_counter()
        if use_quantum:
            # VQC consome as 4 features rolantes de degradação em [-π,π]
            x_roll = np.array([[rolls[c] for c in ROLLING_FEATURES]])
            x4 = clip_to_pi(self.preproc_man.transform(x_roll))
            probs = np.asarray(self.qnn.forward(x4, self.vqc_weights))[0]
            modelo = "quantico:vqc (PauliFeatureMap+EfficientSU2, 4 qubits)"
        else:
            probs = self.rf_man.predict_proba(x13)[0]
            modelo = "classico:random_forest"
        latency = (time.perf_counter() - t0) * 1000.0

        k = int(np.argmax(probs))
        return {
            "risco_manutencao": MAINTENANCE_CLASSES[k],
            "confianca": round(float(probs[k]), 4),
            "probabilidades": {
                c: round(float(p), 4) for c, p in zip(MAINTENANCE_CLASSES, probs)
            },
            "features_rolantes": {k2: round(v, 4) for k2, v in rolls.items()},
            "modelo": modelo,
            "latencia_ms": round(latency, 3),
        }

    # ── Diagnóstico completo (contrato principal da API) ─────────────
    def diagnose(self, equipamento_id: str, leituras: dict, modelo="classico"):
        """Diagnóstico dos dois cenários numa chamada. modelo: classico|quantico|ambos."""
        completed, imputed = self.validate_and_impute(leituras)
        self.push_reading(equipamento_id, completed)

        result = {
            "equipamento_id": equipamento_id,
            "sensores_imputados": imputed,
            "leituras_no_buffer": self.buffer_len(equipamento_id),
        }
        if modelo in ("classico", "ambos"):
            result["anomalia_classico"] = self.predict_anomaly_classical(completed)
            result["manutencao_classico"] = self.predict_maintenance(
                equipamento_id, completed, use_quantum=False
            )
        if modelo in ("quantico", "ambos"):
            result["anomalia_quantico"] = self.predict_anomaly_quantum(equipamento_id)
            if result["anomalia_quantico"] is None:
                result["anomalia_quantico"] = {
                    "aviso": f"buffer com {self.buffer_len(equipamento_id)} leituras; "
                             f"a rota quântica precisa de {WINDOW_SIZE}"
                }
            result["manutencao_quantico"] = self.predict_maintenance(
                equipamento_id, completed, use_quantum=True
            )
        return result


def demo():
    """Self-check: leitura normal e leitura com assinatura de sobreaquecimento.
    Cada leitura recebe jitter gaussiano (~telemetria real). Janelas de leituras
    idênticas têm std=0/FFT degenerada e caem fora da distribuição de treino."""
    rng = np.random.default_rng(42)
    svc = HybridInferenceService()
    normal = {"tensao_V": 220.0, "corrente_A": 8.0, "rpm": 1450.0,
              "temperatura_C": 60.0, "vibracao_mm_s": 3.5, "pressao_bar": 5.0,
              "eficiencia_pct": 88.0, "harmonicos_thd_pct": 3.5,
              "corrente_partida_A": 0.0}
    anomala = {**normal, "temperatura_C": 85.0, "corrente_A": 12.0,
               "vibracao_mm_s": 6.0, "pressao_bar": 6.5}
    sigma = {"tensao_V": 3.0, "corrente_A": 0.8, "rpm": 60.0, "temperatura_C": 2.5,
             "vibracao_mm_s": 0.3, "pressao_bar": 0.3, "eficiencia_pct": 1.5,
             "harmonicos_thd_pct": 0.4, "corrente_partida_A": 0.0}

    def jitter(base):
        leitura = {k: float(np.clip(v + rng.normal(0.0, sigma[k]),
                                    *__import__("common").PHYSICAL_RANGES[k]))
                   for k, v in base.items()}
        return leitura

    for _ in range(12):
        svc.diagnose("motor-01", jitter(normal), modelo="classico")
    r_norm = svc.diagnose("motor-01", jitter(normal), modelo="ambos")
    assert r_norm["anomalia_classico"]["anomalia"] is False, r_norm
    assert "anomalia" in r_norm["anomalia_quantico"], r_norm

    for _ in range(10):
        svc.diagnose("motor-01", jitter(anomala), modelo="classico")
    r_anom = svc.diagnose("motor-01", jitter(anomala), modelo="ambos")
    assert r_anom["anomalia_classico"]["anomalia"] is True, r_anom
    assert r_anom["anomalia_quantico"]["anomalia"] is True, r_anom

    # 4 sensores mínimos (D1): responde com imputação sinalizada
    r_min = svc.diagnose("motor-02", {s: normal[s] for s in
                                      ["tensao_V", "corrente_A", "rpm", "temperatura_C"]})
    assert set(r_min["sensores_imputados"]) == set(OPTIONAL_SENSORS), r_min

    # fora da faixa física → rejeita
    try:
        svc.diagnose("motor-03", {**normal, "rpm": -50})
        raise AssertionError("deveria rejeitar rpm negativo")
    except ValidationError:
        pass

    print("✅ inference.py demo: normal OK, anomalia detectada (clássico e quântico), "
          "imputação e validação OK")
    print(json.dumps(r_anom, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    demo()
