"""
Sprint 2 — Parte 2: Arquitetura Híbrida (Clássico + QML)
=========================================================

Pipeline scikit-learn end-to-end:
    ClassicalFeatureExtractor → MinMaxScaler[-π,π] → PCA(4)
                              → MinMaxScaler[-π,π]
                              → [AmplitudeNormalizer]            (só p/ amplitude encoding)
                              → QSVC (kernel quântico)

Etapa clássica
--------------
ClassicalFeatureExtractor é um `sklearn.BaseEstimator+TransformerMixin` que
recebe janelas temporais 3D (n_windows, n_timesteps, n_sensores) e devolve, por
sensor, 10 features:

  Estatísticas (7) : mean, std, max, min, RMS, kurtosis, skewness
  Frequência   (3) : pico FFT, frequência dominante, entropia espectral

  NB: com fs=1/60Hz e janela=10, a rfft só produz 6 bins. Features espectrais
  têm resolução limitada por design (granularidade minutada do dataset). Em
  vibração industrial real, fs estaria em kHz.

Etapa quântica
--------------
QSVC do `qiskit-machine-learning` usando `FidelityStatevectorKernel` com três
quantum feature maps comparáveis sobre a mesma entrada PCA(4):

  1. ZZFeatureMap (reps=2)        — angle embedding + correlações ZZ
  2. Fourier Feature Map canônico — multi-frequência (ω∈{1,2}), Schuld 2021
  3. RawFeatureVector             — amplitude encoding (avaliação experimental,
                                    n_qubits = ⌈log₂(n_features)⌉ = 2)

Validação estatística
---------------------
Stratified K-fold CV (k=5) reportando MÉDIA ± DESVIO de:
  - Acurácia, F1-score, AUC-ROC
  - Tempo de fit, ms/amostra na inferência

Profundidade do circuito é medida APÓS transpilação para basis {u, cx} —
expõe o custo real NISQ (o depth nativo do RawFeatureVector é 1, mas em basis
{u,cx} cresce exponencialmente com n_qubits — calcanhar de Aquiles conhecido).

Notas de implementação
----------------------
* `FidelityStatevectorKernel` em vez de `FidelityQuantumKernel`+ComputeUncompute:
  o RawFeatureVector não suporta inversão com parâmetros não vinculados, o que
  quebraria o ComputeUncompute. Mesma semântica matemática |⟨ψ(x)|ψ(y)⟩|².
  Em hardware NISQ real seria substituído por ComputeUncompute com shots
  limitados (impacto avaliado na Parte 3 — Benchmarking).
* QSVC não expõe `predict_proba` nativamente — usamos `decision_function`
  (distância à margem) como score para o AUC-ROC. É o melhor disponível na API
  e suficiente para ROC, que só requer ordenação relativa, não calibração.
* fit_time medido aqui NÃO reflete custo NISQ real — o StatevectorKernel é
  ~100-1000× mais rápido que ComputeUncompute em hardware. A relação
  custo×desempenho aqui é só didática.

Outputs gerados
---------------
  - feature_maps_comparacao.csv   (tabela com média ± std)
  - feature_maps_comparacao.json  (dump estruturado completo, incluindo per-fold)
"""

import json
import sys
import time
import warnings

import numpy as np
import pandas as pd
from scipy import stats

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import PCA
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler

from qiskit import QuantumCircuit, transpile
from qiskit.circuit import ParameterVector
from qiskit.circuit.library import ZZFeatureMap

from qiskit_machine_learning.algorithms import QSVC
from qiskit_machine_learning.circuit.library import RawFeatureVector
from qiskit_machine_learning.kernels import FidelityStatevectorKernel

warnings.filterwarnings("ignore")

# Console UTF-8 (Windows cp1252 quebra com → π …)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

np.random.seed(42)

SENSOR_COLS = [
    "tensao_V", "corrente_A", "temperatura_C", "rpm",
    "vibracao_mm_s", "pressao_bar", "eficiencia_pct",
    "harmonicos_thd_pct", "corrente_partida_A",
]

# ════════════════════════════════════════════════════════════════════
# 1. EXTRATOR CLÁSSICO DE FEATURES (estatísticas + frequência)
# ════════════════════════════════════════════════════════════════════

class ClassicalFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extrai 10 features por sensor a partir de janelas temporais.

    Entrada : array 3D (n_janelas, n_timesteps, n_sensores)
    Saída   : array 2D (n_janelas, n_sensores · 10)

    Features por sensor (índice relativo):
        0  mean
        1  std
        2  max
        3  min
        4  RMS                  = sqrt(mean(x²))
        5  kurtosis             (scipy.stats.kurtosis, Fisher=True)
        6  skewness             (scipy.stats.skew)
        7  pico FFT             max(|rfft(x)|)
        8  frequência dominante argmax(|rfft(x)|) → freq
        9  entropia espectral   −Σ p log p, p = |X|² / Σ|X|²
    """

    def __init__(self, fs=1.0 / 60.0):
        # 1 amostra por minuto no dataset Sprint 2 → fs = 1/60 Hz
        self.fs = fs

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        n_win, n_steps, n_sens = X.shape
        out = np.zeros((n_win, n_sens * 10), dtype=float)

        for w in range(n_win):
            for s in range(n_sens):
                sig = X[w, :, s]
                off = s * 10

                # ── Estatísticas ────────────────────────────
                out[w, off + 0] = np.mean(sig)
                out[w, off + 1] = np.std(sig)
                out[w, off + 2] = np.max(sig)
                out[w, off + 3] = np.min(sig)
                out[w, off + 4] = np.sqrt(np.mean(sig ** 2))   # RMS
                out[w, off + 5] = stats.kurtosis(sig)
                out[w, off + 6] = stats.skew(sig)

                # ── Frequência (FFT real) ───────────────────
                fft_mag = np.abs(np.fft.rfft(sig))
                freqs   = np.fft.rfftfreq(len(sig), d=1.0 / self.fs)
                if fft_mag.sum() > 1e-12:
                    psd = fft_mag ** 2
                    psd = psd / psd.sum()
                    spectral_ent = float(-np.sum(psd * np.log(psd + 1e-12)))
                else:
                    spectral_ent = 0.0
                out[w, off + 7] = float(fft_mag.max())
                out[w, off + 8] = float(freqs[np.argmax(fft_mag)])
                out[w, off + 9] = spectral_ent

        # kurtosis em sinal constante → NaN; sanitiza
        return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


# ════════════════════════════════════════════════════════════════════
# 2. AUXILIAR — normalizador L2 (necessário p/ amplitude encoding)
# ════════════════════════════════════════════════════════════════════

class AmplitudeNormalizer(BaseEstimator, TransformerMixin):
    """Normaliza cada linha para norma L2 unitária — pré-requisito do amplitude encoding."""
    def fit(self, X, y=None):
        return self
    def transform(self, X):
        X = np.asarray(X, dtype=float)
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return X / norms


# ════════════════════════════════════════════════════════════════════
# 3. QUANTUM FEATURE MAPS
# ════════════════════════════════════════════════════════════════════

def build_zz_feature_map(n_qubits, reps=2):
    """ZZFeatureMap — angle embedding com correlações ZZ de segunda ordem."""
    return ZZFeatureMap(feature_dimension=n_qubits, reps=reps, entanglement="linear")


def build_fourier_feature_map(n_qubits, frequencies=(1, 2)):
    """
    Fourier feature map CANÔNICO (Schuld et al. 2021).

    Codifica MÚLTIPLAS frequências distintas ω_k em camadas separadas
    de Rz(ω_k · x_i) · Ry(ω_k · x_i), gerando um polinômio trigonométrico
    com termos de Fourier de diferentes ordens. Cada frequência adiciona
    uma camada distinta com seu próprio rotor + entanglement em cadeia.

    Ref: Schuld, Sweke, Meyer (2021), "Effect of data encoding on the
    expressive power of variational quantum machine learning models".

    Default: ω ∈ {1, 2} — duas frequências, alinhado a `reps=2` do ZZ.
    """
    x = ParameterVector("x", n_qubits)
    qc = QuantumCircuit(n_qubits, name="FourierFM")
    for omega in frequencies:
        for i in range(n_qubits):
            qc.h(i)
            qc.rz(float(omega) * x[i], i)
            qc.ry(float(omega) * x[i], i)
        for i in range(n_qubits - 1):
            qc.cx(i, i + 1)
    return qc


def build_amplitude_feature_map(n_features):
    """Amplitude encoding via RawFeatureVector. n_qubits = ⌈log₂(n_features)⌉."""
    return RawFeatureVector(feature_dimension=n_features)


# ════════════════════════════════════════════════════════════════════
# 4. PIPELINE HÍBRIDO
# ════════════════════════════════════════════════════════════════════

def make_hybrid_pipeline(feature_map, n_pca, *, amplitude_encoding=False):
    """
    Pipeline scikit-learn:
        ClassicalFeatureExtractor → MinMaxScaler → PCA → MinMaxScaler
                                  → [AmplitudeNormalizer] → QSVC
    """
    steps = [
        ("features", ClassicalFeatureExtractor()),
        ("scaler1",  MinMaxScaler(feature_range=(-np.pi, np.pi))),
        ("pca",      PCA(n_components=n_pca, random_state=42)),
        ("scaler2",  MinMaxScaler(feature_range=(-np.pi, np.pi))),
    ]
    if amplitude_encoding:
        steps.append(("amp_norm", AmplitudeNormalizer()))

    # FidelityStatevectorKernel computa |⟨ψ(x)|ψ(y)⟩|² direto via simulação de
    # statevector, sem precisar inverter o circuito (importante: RawFeatureVector
    # não suporta inversão com parâmetros não vinculados). Em hardware real seria
    # substituído por FidelityQuantumKernel(ComputeUncompute) ou ProjectedQuantumKernel.
    kernel = FidelityStatevectorKernel(feature_map=feature_map)
    # class_weight='balanced' compensa desbalanceamento — relevante para label_mode='center'
    # ou 'threshold' (que produzem classes muito desiguais). Para 'any' o efeito é leve.
    steps.append(("qsvc", QSVC(quantum_kernel=kernel, class_weight="balanced")))
    return Pipeline(steps)


# ════════════════════════════════════════════════════════════════════
# 5. CARGA + JANELAMENTO
# ════════════════════════════════════════════════════════════════════

def label_window(y_window, mode="center", threshold=0.2):
    """
    Estratégias de rotulagem de janela:
      - "any"       : 1 se houver QUALQUER anomalia na janela (original).
                      Tende a "diluir" o sinal adversarial (janela quase-normal
                      ainda recebe label=1 por uma única amostra anômala).
      - "center"    : 1 se a amostra CENTRAL da janela for anomalia (default).
                      Mantém o problema "estado atual é anomalia, dado contexto".
      - "threshold" : 1 se a fração de anomalias na janela > threshold.
                      Mais conservador que "any", mais agressivo que "center"
                      para janelas com agrupamentos.
    """
    y_window = np.asarray(y_window)
    if mode == "any":
        return int(y_window.any())
    if mode == "center":
        return int(y_window[len(y_window) // 2])
    if mode == "threshold":
        return int(np.mean(y_window) > threshold)
    raise ValueError(f"label_mode inválido: {mode}")


def build_windows_from_bruto(csv_path, window_size=10, step=5,
                             label_mode="any", label_threshold=0.2,
                             sample_fraction=None, seed=42):
    """
    Lê o bruto, gera janelas 3D (n_windows, window_size, 9) e labels.
    sample_fraction subamostra estratificadamente para manter o QSVC viável no simulador.

    label_mode controla a rotulagem da janela (ver `label_window`).
    Default "any": balanceamento ~50/50, alinhado ao caso "detecção/alerta".
    Para "predizer se o estado central é anomalia", use label_mode="center" —
    produz ~8% positivos (o class_weight='balanced' no QSVC compensa).
    """
    df = pd.read_csv(csv_path)
    X_raw = df[SENSOR_COLS].values
    y_raw = df["label_anomalia"].values

    starts = list(range(0, len(X_raw) - window_size + 1, step))
    X = np.array([X_raw[s:s + window_size] for s in starts])
    y = np.array([label_window(y_raw[s:s + window_size], mode=label_mode,
                                threshold=label_threshold) for s in starts])

    if sample_fraction is not None and sample_fraction < 1.0:
        rng = np.random.default_rng(seed)
        idx_pos = np.where(y == 1)[0]
        idx_neg = np.where(y == 0)[0]
        n_pos = max(1, int(len(idx_pos) * sample_fraction))
        n_neg = max(1, int(len(idx_neg) * sample_fraction))
        sel = np.concatenate([
            rng.choice(idx_pos, size=n_pos, replace=False),
            rng.choice(idx_neg, size=n_neg, replace=False),
        ])
        rng.shuffle(sel)
        X, y = X[sel], y[sel]

    return X, y


# ════════════════════════════════════════════════════════════════════
# 6. BENCHMARK DOS FEATURE MAPS
# ════════════════════════════════════════════════════════════════════

def safe_native_depth(circuit):
    """Profundidade nativa (sem decompor para basis gates)."""
    try:
        return int(circuit.depth())
    except Exception:
        return -1


def basis_depth(circuit, basis_gates=("u", "cx")):
    """
    Profundidade APÓS transpilação para basis {u, cx} (sem otimização).
    Proxy do custo real em hardware NISQ — expõe o calcanhar de Aquiles do
    amplitude encoding, cuja preparação de estado cresce exponencialmente
    com n_qubits depois de decomposta em gates 1/2-qubit.
    """
    try:
        n = circuit.num_parameters
        if n > 0:
            dummy = np.ones(n, dtype=float) / np.sqrt(n)
            circuit = circuit.assign_parameters(dummy)
        transpiled = transpile(circuit, basis_gates=list(basis_gates),
                                optimization_level=0)
        return int(transpiled.depth())
    except Exception:
        return -1


def benchmark_feature_maps_cv(X, y, n_pca=4, n_splits=5, seed=42):
    """
    Stratified K-fold CV (k=5) para cada feature map. Retorna estatísticas
    agregadas (média ± desvio) e per-fold raw para análise.

    Em datasets pequenos (centenas de janelas), um único train/test split
    produz métricas com intervalo de confiança de ±0.1 ou pior — o ranking
    entre feature maps pode mudar com o random_state. CV mitiga isso.
    """
    fmap_configs = [
        ("ZZFeatureMap (reps=2)",
            lambda: build_zz_feature_map(n_pca, reps=2), False,
            "Angle embedding + correlações ZZ de 2ª ordem"),
        ("Fourier Feature Map (ω={1,2})",
            lambda: build_fourier_feature_map(n_pca, frequencies=(1, 2)), False,
            "Codificação periódica multi-frequência (Schuld 2021)"),
        ("RawFeatureVector (amplitude)",
            lambda: build_amplitude_feature_map(n_pca), True,
            "Amplitude encoding — depth basis-gate cresce expon. com n_qubits"),
    ]

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    results = []

    for name, fmap_fn, is_amp, descr in fmap_configs:
        ref_fmap = fmap_fn()
        depth_native = safe_native_depth(ref_fmap)
        depth_basis  = basis_depth(ref_fmap)

        print(f"\n  ── {name}")
        print(f"     {descr}")
        print(f"     qubits = {ref_fmap.num_qubits} | depth native = {depth_native} | depth basis(u,cx) = {depth_basis}")

        per_fold = {"acc": [], "f1": [], "auc": [], "fit_s": [], "ms_sample": []}
        for fold_idx, (tr_idx, te_idx) in enumerate(skf.split(X, y), start=1):
            X_tr, X_te = X[tr_idx], X[te_idx]
            y_tr, y_te = y[tr_idx], y[te_idx]

            pipe = make_hybrid_pipeline(fmap_fn(), n_pca,
                                        amplitude_encoding=is_amp)

            t0 = time.perf_counter()
            pipe.fit(X_tr, y_tr)
            per_fold["fit_s"].append(time.perf_counter() - t0)

            t0 = time.perf_counter()
            y_pred = pipe.predict(X_te)
            ms = (time.perf_counter() - t0) / max(len(y_te), 1) * 1000.0
            per_fold["ms_sample"].append(ms)

            try:
                y_score = pipe.decision_function(X_te)
            except Exception:
                y_score = y_pred
            per_fold["acc"].append(accuracy_score(y_te, y_pred))
            per_fold["f1"].append(f1_score(y_te, y_pred, zero_division=0))
            try:
                per_fold["auc"].append(roc_auc_score(y_te, y_score))
            except ValueError:
                per_fold["auc"].append(np.nan)

            print(f"       fold {fold_idx}/{n_splits}: "
                  f"acc={per_fold['acc'][-1]:.3f} "
                  f"f1={per_fold['f1'][-1]:.3f} "
                  f"auc={per_fold['auc'][-1]:.3f} "
                  f"fit={per_fold['fit_s'][-1]:.2f}s")

        def m(k): return float(np.nanmean(per_fold[k]))
        def s(k): return float(np.nanstd(per_fold[k]))

        print(f"     [agregado k={n_splits}]")
        print(f"       AUC-ROC   : {m('auc'):.3f} ± {s('auc'):.3f}")
        print(f"       F1-score  : {m('f1'):.3f} ± {s('f1'):.3f}")
        print(f"       accuracy  : {m('acc'):.3f} ± {s('acc'):.3f}")
        print(f"       fit_time  : {m('fit_s'):.2f}s ± {s('fit_s'):.2f}s")
        print(f"       ms/amostra: {m('ms_sample'):.2f} ± {s('ms_sample'):.2f}")

        results.append({
            "feature_map": name,
            "descricao": descr,
            "n_qubits": int(ref_fmap.num_qubits),
            "depth_native": depth_native,
            "depth_basis_ucx": depth_basis,
            "n_splits": n_splits,
            "fit_s_mean":         round(m("fit_s"),     4),
            "fit_s_std":          round(s("fit_s"),     4),
            "ms_per_sample_mean": round(m("ms_sample"), 4),
            "ms_per_sample_std":  round(s("ms_sample"), 4),
            "accuracy_mean":      round(m("acc"),       4),
            "accuracy_std":       round(s("acc"),       4),
            "f1_mean":            round(m("f1"),        4),
            "f1_std":             round(s("f1"),        4),
            "auc_mean":           round(m("auc"),       4),
            "auc_std":            round(s("auc"),       4),
            "per_fold_auc":       [round(v, 4) for v in per_fold["auc"]],
            "per_fold_f1":        [round(v, 4) for v in per_fold["f1"]],
            "per_fold_accuracy":  [round(v, 4) for v in per_fold["acc"]],
        })

    return results


# ════════════════════════════════════════════════════════════════════
# 7. MAIN
# ════════════════════════════════════════════════════════════════════

def main(sample_fraction=0.20, n_pca=4, n_splits=5, label_mode="any"):
    print("=" * 70)
    print("SPRINT 2 — PARTE 2: ARQUITETURA HÍBRIDA (CLÁSSICO + QML)")
    print("=" * 70)

    # ── Dados ─────────────────────────────────────────
    print(f"\n[1/3] Carregando bruto e janelando (label_mode={label_mode}) …")
    X_win, y_win = build_windows_from_bruto(
        "dataset_motor_sprint2_bruto.csv",
        window_size=10, step=5,
        label_mode=label_mode,
        sample_fraction=sample_fraction,
    )
    print(f"      janelas: {X_win.shape} | label dist: {np.bincount(y_win)}")

    # Cada fold do CV produz seu próprio train/test estratificado
    print(f"\n[2/3] Benchmark CV (k={n_splits}) dos 3 quantum feature maps …")
    results = benchmark_feature_maps_cv(X_win, y_win, n_pca=n_pca, n_splits=n_splits)

    # ── Persistência ──────────────────────────────────
    print("\n[3/3] Salvando comparação …")
    # Versão CSV "limpa" sem listas per_fold (legível em planilha)
    df_res = pd.DataFrame(results).drop(
        columns=["per_fold_auc", "per_fold_f1", "per_fold_accuracy"]
    )
    df_res.to_csv("feature_maps_comparacao.csv", index=False)
    with open("feature_maps_comparacao.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"RESUMO COMPARATIVO — Stratified {n_splits}-Fold CV")
    print("=" * 70)
    summary_cols = [
        "feature_map", "n_qubits", "depth_native", "depth_basis_ucx",
        "auc_mean", "auc_std", "f1_mean", "f1_std",
        "accuracy_mean", "accuracy_std",
        "fit_s_mean", "ms_per_sample_mean",
    ]
    print(df_res[summary_cols].to_string(index=False))
    print("=" * 70)
    print("✅ Outputs: feature_maps_comparacao.csv + feature_maps_comparacao.json")


if __name__ == "__main__":
    main()
