"""
Sprint 3, modulo comum: ponte com o codigo do Sprint 2 e constantes compartilhadas.

Todo reuso do Sprint 2 passa por aqui:
  - sys.path aponta para a pasta do Sprint 2 (necessário também para o joblib
    despicklar objetos cujas classes vivem em `arquitetura_hibrida_sprint2`);
  - constantes de sensores, faixas físicas e score de manutenção replicados
    do `refinamento_dataset_sprint2.py` (função causal, reimplementável em stream).
"""

import sys
from pathlib import Path

import numpy as np

SPRINT3_DIR = Path(__file__).resolve().parent
# Preferência: cópia local embarcada (sprint2_core/, entrega autossuficiente);
# fallback: pasta irmã do repositório de desenvolvimento.
_LOCAL_SPRINT2 = SPRINT3_DIR / "sprint2_core"
_SIBLING_SPRINT2 = SPRINT3_DIR.parent / "CS2Quantica" / "Sprint2Quantica"
SPRINT2_DIR = (
    _LOCAL_SPRINT2
    if (_LOCAL_SPRINT2 / "arquitetura_hibrida_sprint2.py").exists()
    else _SIBLING_SPRINT2
)
MODELS_DIR = SPRINT3_DIR / "models"
DB_PATH = SPRINT3_DIR / "digital_twin.db"
BRUTO_CSV = SPRINT2_DIR / "dataset_motor_sprint2_bruto.csv"

# Autenticacao da API (ver api.py). Se a variavel de ambiente FORZY_API_KEY
# estiver definida, toda chamada precisa do header X-API-Key com o mesmo
# valor. Se nao estiver definida, a API roda sem autenticacao (modo
# desenvolvimento/demonstracao), documentado no README.
import os

API_KEY_ENV_VAR = "FORZY_API_KEY"
API_KEY = os.environ.get(API_KEY_ENV_VAR)

sys.path.insert(0, str(SPRINT2_DIR))

# Reuso direto do Sprint 2 (classes/fábricas validadas na Parte 2)
from arquitetura_hibrida_sprint2 import (  # noqa: E402
    SENSOR_COLS,
    AmplitudeNormalizer,
    ClassicalFeatureExtractor,
    build_amplitude_feature_map,
    build_windows_from_bruto,
    make_hybrid_pipeline,
)

# Faixas físicas de validação (clips do refinamento_dataset_sprint2.py).
# Tensão não tem clip no Sprint 2; faixa generosa em torno de 200-230 V nominais.
PHYSICAL_RANGES = {
    "tensao_V": (150.0, 280.0),
    "corrente_A": (0.0, 20.0),
    "temperatura_C": (-10.0, 120.0),
    "rpm": (0.0, 2000.0),
    "vibracao_mm_s": (0.0, 12.0),
    "pressao_bar": (0.0, 15.0),
    "eficiencia_pct": (0.0, 100.0),
    "harmonicos_thd_pct": (0.0, 20.0),
    "corrente_partida_A": (0.0, 70.0),
}

# Contrato da API (decisão D1): 4 sensores do enunciado obrigatórios,
# demais opcionais com imputação sinalizada.
REQUIRED_SENSORS = ["tensao_V", "corrente_A", "rpm", "temperatura_C"]
OPTIONAL_SENSORS = [c for c in SENSOR_COLS if c not in REQUIRED_SENSORS]

# Cenario 2, classes operacionais de manutencao (ordem de severidade crescente)
MAINTENANCE_CLASSES = ["normal", "monitoramento", "alerta", "critico"]
WINDOW_SIZE = 10
WINDOW_STEP = 5
W_ROLL = 20  # janela rolante (min) das features de degradacao, igual ao Sprint 2

# Features do Cenário 2: sensores instantâneos + degradação rolante causal.
# O rótulo classe_manutencao foi construído sobre stats rolantes (Sprint 2);
# fornecê-las ao modelo é o feature set causal correto, disponível em stream.
ROLLING_FEATURES = ["vib_roll", "harm_roll", "efic_roll", "efic_slope"]
MAINT_FEATURES = SENSOR_COLS + ROLLING_FEATURES

# rpm abaixo disso = motor parado → parada_programada por regra, sem modelo
RPM_PARADA = 300.0


def maintenance_score(vib_roll, harm_roll, efic_roll, efic_slope):
    """Score de degradacao do Sprint 2 (pesos 0.40/0.30/0.20/0.10), causal."""
    return (
        0.40 * max(vib_roll - 3.5, 0.0)
        + 0.30 * max(harm_roll - 4.0, 0.0)
        + 0.20 * max(88.0 - efic_roll, 0.0) / 10.0
        + 0.10 * max(-efic_slope, 0.0) * 10.0
    )


def maintenance_class_from_score(score):
    if score >= 1.5:
        return "critico"
    if score >= 0.8:
        return "alerta"
    if score >= 0.3:
        return "monitoramento"
    return "normal"


def _modulo_interpret(num_classes):
    """Mesmo interpret do VQC do qiskit-machine-learning 0.8 (x % num_classes).
    O treino deve passar output_shape=num_classes ao VQC. Sem isso o VQC fixa
    interpret em x % 2 no construtor e as classes 2..n ficam inalcançáveis."""
    def parity(x, num_classes=num_classes):
        return x % num_classes
    return parity


def build_maintenance_qnn(num_classes=len(MAINTENANCE_CLASSES)):
    """
    QNN do Cenário 2 (VQC): PauliFeatureMap(Z,ZZ) + EfficientSU2, 4 qubits.
    Reconstruida identicamente no treino e na inferencia. So os pesos sao
    persistidos (evita picklar primitives do Qiskit).
    """
    from qiskit.circuit import QuantumCircuit
    from qiskit.circuit.library import EfficientSU2, PauliFeatureMap
    from qiskit_machine_learning.neural_networks import SamplerQNN

    n_qubits = 4
    feature_map = PauliFeatureMap(feature_dimension=n_qubits, reps=1, paulis=["Z", "ZZ"])
    ansatz = EfficientSU2(n_qubits, reps=2)
    circuit = QuantumCircuit(n_qubits)
    circuit.compose(feature_map, inplace=True)
    circuit.compose(ansatz, inplace=True)

    qnn = SamplerQNN(
        circuit=circuit,
        input_params=feature_map.parameters,
        weight_params=ansatz.parameters,
        interpret=_modulo_interpret(num_classes),
        output_shape=num_classes,
    )
    return qnn, feature_map, ansatz


def clip_to_pi(X):
    """Leituras fora do range de treino extrapolam o MinMaxScaler → clip [-π, π]
    obrigatório antes do angle encoding (risco #5 do planejamento)."""
    return np.clip(X, -np.pi, np.pi)


def _slope(values):
    """Slope de regressão linear (como o _rolling_slope do refinamento)."""
    if len(values) < 3:
        return 0.0
    return float(np.polyfit(np.arange(len(values)), np.asarray(values, dtype=float), 1)[0])


def add_rolling_features(df):
    """Anexa vib_roll/harm_roll/efic_roll/efic_slope (W=20, causais) a um
    DataFrame do bruto em ordem temporal. Replica o refinamento do Sprint 2."""
    import pandas as pd

    out = df.copy()
    out["vib_roll"] = out["vibracao_mm_s"].rolling(W_ROLL, min_periods=1).mean()
    out["harm_roll"] = out["harmonicos_thd_pct"].rolling(W_ROLL, min_periods=1).mean()
    out["efic_roll"] = out["eficiencia_pct"].rolling(W_ROLL, min_periods=1).mean()
    out["efic_slope"] = (
        out["eficiencia_pct"]
        .rolling(W_ROLL, min_periods=3)
        .apply(lambda y: np.polyfit(np.arange(len(y)), y, 1)[0], raw=True)
        .fillna(0.0)
    )
    return out


def rolling_features_from_buffer(readings):
    """Mesmas 4 features rolantes, calculadas sobre um buffer de leituras
    (lista de dicts, mais antiga → mais recente). Semântica idêntica ao
    rolling(min_periods) do treino para buffers curtos."""
    vib = [r["vibracao_mm_s"] for r in readings]
    harm = [r["harmonicos_thd_pct"] for r in readings]
    efic = [r["eficiencia_pct"] for r in readings]
    return {
        "vib_roll": float(np.mean(vib)),
        "harm_roll": float(np.mean(harm)),
        "efic_roll": float(np.mean(efic)),
        "efic_slope": _slope(efic),
    }
