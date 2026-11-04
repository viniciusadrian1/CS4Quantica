"""Gera o diagrama de arquitetura end-to-end (relatorio/arquitetura.png)."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

FIG_W, FIG_H = 14, 8.2
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, 14)
ax.set_ylim(0, 8.2)
ax.axis("off")

C_INGEST = "#DBEAFE"
C_PRE = "#E0E7FF"
C_CLASS = "#DCFCE7"
C_QUANT = "#F3E8FF"
C_PERSIST = "#FEF9C3"
C_VIEW = "#FFE4E6"
EDGE = "#334155"


def box(x, y, w, h, title, lines, color, title_size=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                                facecolor=color, edgecolor=EDGE, linewidth=1.4))
    ax.text(x + w / 2, y + h - 0.34, title, ha="center", va="center",
            fontsize=title_size, fontweight="bold", color="#0F172A")
    for i, line in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.72 - i * 0.30, line, ha="center",
                va="center", fontsize=8.6, color="#1E293B")


def arrow(x1, y1, x2, y2, label=None, style="-", lw=1.8):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=16, linewidth=lw,
                                 linestyle=style, color=EDGE))
    if label:
        ax.text((x1 + x2) / 2 + 0.06, (y1 + y2) / 2 + 0.14, label,
                fontsize=8.2, color="#475569", ha="center")


ax.text(7, 7.9, "FORZY Digital Twin: Arquitetura de Integracao End-to-End (Sprint 3)",
        ha="center", fontsize=14, fontweight="bold", color="#0F172A")

# Camada 1: ingestão
box(0.2, 5.6, 3.0, 1.7, "Ingestão de sensores",
    ["Telemetria do motor (9 canais)", "replay do dataset Sprint 2",
     "1 leitura/min (OPC-UA/IoT", "em planta real)"], C_INGEST)

# Camada 2: pré-processamento
box(3.9, 5.6, 3.2, 1.7, "Pré-processamento",
    ["Validação de faixas físicas", "Imputação sinalizada (D1)",
     "Buffer 20 leituras/ativo", "Scaler[-π,π] → PCA(4) → Scaler"], C_PRE)

# API central
box(7.8, 5.35, 3.0, 2.05, "API de predição (FastAPI)",
    ["POST /predict", "POST /predict/janela", "GET /history · /models",
     "roteia clássico | quântico", "| ambos"], "#F1F5F9")

# Camada clássica
box(4.6, 2.7, 4.0, 2.0, "Camada 1: Triagem classica (~0,1 ms)",
    ["síncrona, sempre no caminho crítico",
     "Anomalia: GB · RF · MLP · SVM-RBF (binário)",
     "Manutenção: RF 13 features (4 classes)",
     "features rolantes causais de degradação"], C_CLASS, title_size=9.5)

# Camada quântica
box(9.1, 2.7, 4.6, 2.0, "Camada 2: Auditoria quantica (~0,35 s/consulta, sim.)",
    ["Qiskit · fora do caminho crítico em hardware real",
     "Anomalia: QSVC + Amplitude Encoding (2 qubits, depth 4)",
     "kernel FidelityStatevectorKernel · janela 10×9",
     "Manutenção: VQC PauliFM + EfficientSU2 (4 qubits)"], C_QUANT, title_size=9.5)

# Persistência
box(0.6, 2.7, 3.0, 2.0, "Persistência",
    ["SQLite digital_twin.db", "toda predição registrada",
     "(rastreabilidade/governança)", "models/*.joblib + VQC .npz"], C_PERSIST)

# Dashboard
box(4.6, 0.2, 6.0, 1.7, "Dashboard / Digital Twin visual (Streamlit)",
    ["estado do ativo · alertas de anomalia · risco de manutenção",
     "comparação clássico × quântico · histórico (GET /history)"],
    C_VIEW, title_size=10.5)

# Fluxos
arrow(3.2, 6.45, 3.9, 6.45)
arrow(7.1, 6.45, 7.8, 6.45)
arrow(8.6, 5.35, 7.4, 4.7, "leitura pontual")
arrow(10.0, 5.35, 10.9, 4.7, "janela/buffer")
arrow(4.6, 3.7, 3.6, 3.7, "log")
arrow(9.1, 2.85, 8.6, 2.85, style=":")
ax.text(8.85, 2.55, "gatilho / sob demanda", fontsize=7.6, ha="center", color="#475569")
arrow(6.6, 2.7, 6.9, 1.9)
arrow(2.1, 2.7, 4.7, 1.3, "histórico")
arrow(10.6, 2.7, 9.6, 1.9)

fig.savefig("relatorio/arquitetura.png", dpi=160, bbox_inches="tight",
            facecolor="white")
print("OK: relatorio/arquitetura.png gerado")
