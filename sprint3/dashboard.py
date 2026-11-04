"""
Sprint 3, Fase 4: Dashboard / Digital Twin visual (Streamlit).

Materializa o gêmeo digital do motor FORZY: faz replay do dataset bruto do
Sprint 2 como se fosse telemetria ao vivo (1 leitura/refresh), envia cada
leitura à API de predição e exibe estado do ativo, alertas de anomalia,
risco de manutenção, comparação clássico × quântico e histórico.

Uso:
  1. uvicorn api:app --port 8000
  2. streamlit run dashboard.py
"""

import time

import pandas as pd
import requests
import streamlit as st

from common import BRUTO_CSV, SENSOR_COLS

st.set_page_config(page_title="FORZY Digital Twin", page_icon="⚙️", layout="wide")

RISK_STYLE = {
    "normal": ("🟢", "Normal"),
    "monitoramento": ("🟡", "Monitoramento"),
    "alerta": ("🟠", "Alerta"),
    "critico": ("🔴", "CRÍTICO"),
    "parada_programada": ("⚪", "Parada programada"),
}
SENSOR_LABELS = {
    "tensao_V": "Tensão (V)", "corrente_A": "Corrente (A)",
    "temperatura_C": "Temperatura (°C)", "rpm": "RPM",
    "vibracao_mm_s": "Vibração (mm/s)", "pressao_bar": "Pressão (bar)",
    "eficiencia_pct": "Eficiência (%)", "harmonicos_thd_pct": "THD (%)",
    "corrente_partida_A": "Corr. partida (A)",
}


@st.cache_data
def load_telemetry():
    return pd.read_csv(BRUTO_CSV)


def call_api(api_url, equipamento_id, leituras, modelo):
    resp = requests.post(
        f"{api_url}/predict",
        json={"equipamento_id": equipamento_id, "leituras": leituras, "modelo": modelo},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


df = load_telemetry()

# ── Sidebar ──────────────────────────────────────────────────────────
st.sidebar.title("⚙️ FORZY Digital Twin")
api_url = st.sidebar.text_input("URL da API", "http://127.0.0.1:8000")
modelo = st.sidebar.radio(
    "Rota de inferência", ["ambos", "classico", "quantico"], index=0,
    help="'ambos' mostra a comparação clássico × quântico lado a lado",
)
speed = st.sidebar.slider("Velocidade do replay (s/leitura)", 0.2, 3.0, 0.6, 0.2)
start_at = st.sidebar.number_input(
    "Iniciar replay na linha", 0, len(df) - 1, 240,
    help="240 ≈ fim do 1º ciclo; anomalias injetadas aparecem nos ciclos de operação "
         "normal. O valor é aplicado ao clicar em ↺ Reset.",
)

if "idx" not in st.session_state:
    st.session_state.idx = int(start_at)
    st.session_state.running = False
    st.session_state.history = []

col_a, col_b, col_c = st.sidebar.columns(3)
if col_a.button("▶ Iniciar"):
    st.session_state.running = True
if col_b.button("⏸ Pausar"):
    st.session_state.running = False
if col_c.button("↺ Reset"):
    st.session_state.idx = int(start_at)
    st.session_state.history = []
    st.session_state.running = False

try:
    health = requests.get(f"{api_url}/health", timeout=3).json()
    st.sidebar.success("API online")
except Exception:
    st.sidebar.error("API offline, suba com `uvicorn api:app --port 8000`")
    st.stop()

# ── Avanca o replay ──────────────────────────────────────────────────
row = df.iloc[st.session_state.idx]
leituras = {c: float(row[c]) for c in SENSOR_COLS}
timestamp = row["timestamp"]

# 1 predicao por leitura. Reruns causados por interacao de widget (pausado)
# reusam o ultimo resultado, sem duplicar o buffer da API nem o historico.
cache_key = (st.session_state.idx, modelo)
if st.session_state.get("last_key") == cache_key:
    result = st.session_state.last_result
else:
    try:
        result = call_api(api_url, "motor-01", leituras, modelo)
    except Exception as exc:
        st.error(f"Falha ao chamar a API ({exc}), replay pausado. "
                 "Verifique o servidor e clique em ▶ Iniciar.")
        st.session_state.running = False
        st.stop()
    st.session_state.last_key = cache_key
    st.session_state.last_result = result
    st.session_state.history.append({
        "timestamp": timestamp,
        **leituras,
        "rotulo_real": int(row["label_anomalia"]),
        "tipo_real": row["tipo_anomalia"],
        "resultado": result,
    })
    st.session_state.history = st.session_state.history[-300:]

# ── Cabeçalho de estado ──────────────────────────────────────────────
diag_cls = result.get("manutencao_classico") or result.get("manutencao_quantico") or {}
anom_cls = result.get("anomalia_classico") or {}
anom_qtm = result.get("anomalia_quantico") or {}

risco = diag_cls.get("risco_manutencao", "normal")
icon, label = RISK_STYLE.get(risco, ("⚪", risco))
anomalia_detectada = bool(anom_cls.get("anomalia")) or bool(anom_qtm.get("anomalia"))

st.title("⚙️ Digital Twin: Motor Industrial FORZY")
h1, h2, h3, h4 = st.columns([2, 2, 2, 3])
h1.metric("Estado do ativo", f"{icon} {label}")
h2.metric("Anomalia", "🚨 DETECTADA" if anomalia_detectada else "✅ Ausente")
h3.metric("Leitura", f"#{st.session_state.idx}")
h4.metric("Timestamp da telemetria", str(timestamp))

if anomalia_detectada:
    detec = []
    if anom_cls.get("anomalia"):
        detec.append(f"clássico ({anom_cls['confianca']:.0%})")
    if anom_qtm.get("anomalia"):
        detec.append(f"quântico ({anom_qtm['confianca']:.0%})")
    st.error(f"🚨 **Anomalia detectada por: {' e '.join(detec)}**. "
             f"Rótulo real desta leitura: "
             f"{'anômala (' + str(row['tipo_anomalia']) + ')' if row['label_anomalia'] else 'normal'}")

# ── Sensores ─────────────────────────────────────────────────────────
st.subheader("Sensores (leitura atual)")
cols = st.columns(9)
hist_df = pd.DataFrame([
    {k: h[k] for k in SENSOR_COLS} for h in st.session_state.history
])
for i, sensor in enumerate(SENSOR_COLS):
    delta = None
    if len(hist_df) > 1:
        delta = round(leituras[sensor] - float(hist_df[sensor].iloc[-2]), 2)
    cols[i].metric(SENSOR_LABELS[sensor], f"{leituras[sensor]:.1f}", delta)

# ── Comparação clássico × quântico ──────────────────────────────────
st.subheader("Inferência híbrida: clássico × quântico")
c1, c2 = st.columns(2)

with c1:
    st.markdown("**🖥️ Rota clássica** (triagem em tempo real)")
    if anom_cls:
        st.write(f"Anomalia: {'🚨 sim' if anom_cls['anomalia'] else '✅ não'} · "
                 f"confiança {anom_cls['confianca']:.1%} · "
                 f"{anom_cls['latencia_ms']:.2f} ms · `{anom_cls['modelo']}`")
    man_c = result.get("manutencao_classico")
    if man_c:
        ic, lb = RISK_STYLE.get(man_c["risco_manutencao"], ("⚪", "?"))
        st.write(f"Risco de manutenção: {ic} **{lb}** · "
                 f"confiança {man_c['confianca']:.1%} · `{man_c['modelo']}`")
        if man_c.get("probabilidades"):
            st.progress(man_c["confianca"], text=f"prob. {man_c['risco_manutencao']}")
    if not anom_cls and not man_c:
        st.caption("rota clássica desativada (modelo = quantico)")

with c2:
    st.markdown("**⚛️ Rota quântica** (simulador Qiskit, auditoria)")
    if anom_qtm.get("modelo"):
        st.write(f"Anomalia: {'🚨 sim' if anom_qtm['anomalia'] else '✅ não'} · "
                 f"confiança {anom_qtm['confianca']:.1%} · "
                 f"{anom_qtm['latencia_ms']:.2f} ms · janela de {anom_qtm.get('janela', '10')}")
        st.caption(anom_qtm["modelo"])
    elif anom_qtm.get("aviso"):
        st.info(anom_qtm["aviso"])
    man_q = result.get("manutencao_quantico")
    if man_q:
        ic, lb = RISK_STYLE.get(man_q["risco_manutencao"], ("⚪", "?"))
        st.write(f"Risco de manutenção: {ic} **{lb}** · "
                 f"confiança {man_q['confianca']:.1%}")
        st.caption(man_q["modelo"])
    if not anom_qtm and not man_q:
        st.caption("rota quântica desativada (modelo = classico)")

# ── Séries temporais ─────────────────────────────────────────────────
st.subheader("Histórico recente (replay)")
if len(st.session_state.history) > 2:
    def _score(h):
        # score da rota ativa: clássico quando existe, senão o quântico
        s = (h["resultado"].get("anomalia_classico") or {}).get("score_anomalia")
        if s is None:
            s = (h["resultado"].get("anomalia_quantico") or {}).get("score_anomalia")
        return s

    plot_df = pd.DataFrame([
        {
            "temperatura_C": h["temperatura_C"],
            "corrente_A": h["corrente_A"],
            "vibracao_mm_s": h["vibracao_mm_s"],
            "score_anomalia": _score(h),
            "rotulo_real": h["rotulo_real"],
        }
        for h in st.session_state.history
    ])
    g1, g2 = st.columns(2)
    g1.line_chart(plot_df[["temperatura_C", "corrente_A", "vibracao_mm_s"]],
                  height=260)
    g2.line_chart(plot_df[["score_anomalia", "rotulo_real"]], height=260)
    st.caption("Esquerda: sensores-chave. Direita: score de anomalia da rota ativa "
               "(clássica; quântica quando só ela está ligada) × rótulo real das "
               "leituras injetadas no dataset (validação visual da detecção).")

# ── Histórico persistido (API/SQLite) ────────────────────────────────
with st.expander("📜 Últimas predições registradas (SQLite via GET /history)"):
    try:
        hist = requests.get(f"{api_url}/history", params={"limit": 15}, timeout=5).json()
        rows = []
        for h in hist:
            res = h["resultado"]
            ac = res.get("anomalia_classico") or {}
            mc = res.get("manutencao_classico") or {}
            rows.append({
                "ts": pd.to_datetime(h["ts"], unit="s").strftime("%H:%M:%S"),
                "equipamento": h["equipamento_id"],
                "modelo": h["modelo_solicitado"],
                "anomalia": ac.get("anomalia"),
                "risco": mc.get("risco_manutencao"),
                "latência (ms)": h["latencia_total_ms"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    except Exception as exc:
        st.caption(f"histórico indisponível: {exc}")

# ── Loop de replay ───────────────────────────────────────────────────
if st.session_state.running and st.session_state.idx < len(df) - 1:
    st.session_state.idx += 1
    time.sleep(speed)
    st.rerun()
