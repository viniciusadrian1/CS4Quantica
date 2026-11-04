"""
Sprint 3, Fase 3: API de predicao do Digital Twin FORZY.

Endpoints:
  POST /predict         diagnostico completo (anomalia + manutencao) de 1 leitura
  POST /predict/janela  rota quantica com janela explicita de 10 leituras
  GET  /history         ultimas predicoes registradas (SQLite)
  GET  /models          modelos carregados e metricas de holdout
  GET  /health          status do servico (nao exige autenticacao)

Toda predicao e registrada em digital_twin.db para rastreabilidade e governanca.
Documentacao interativa: http://localhost:8000/docs (OpenAPI automatica).

Autenticacao: se a variavel de ambiente FORZY_API_KEY estiver definida, todo
endpoint de escrita (POST) exige o header X-API-Key com o mesmo valor. Sem a
variavel definida, a API roda sem autenticacao, o que e adequado para
desenvolvimento e demonstracao em ambiente controlado, mas nao para producao.

Uso:  uvicorn api:app --port 8000
      FORZY_API_KEY=segredo uvicorn api:app --port 8000   (com autenticacao)
"""

import json
import sqlite3
import time
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from common import API_KEY, API_KEY_ENV_VAR, DB_PATH, SENSOR_COLS, WINDOW_SIZE
from inference import HybridInferenceService, ValidationError

service: Optional[HybridInferenceService] = None


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            equipamento_id TEXT NOT NULL,
            leituras TEXT NOT NULL,
            resultado TEXT NOT NULL,
            modelo_solicitado TEXT NOT NULL,
            latencia_total_ms REAL NOT NULL
        )
    """)
    return conn


@asynccontextmanager
async def lifespan(app: FastAPI):
    global service
    service = HybridInferenceService()
    _db().close()
    yield


app = FastAPI(
    title="FORZY Digital Twin: API de Predicao Hibrida (Classico + QML)",
    description=(
        "Recebe leituras de sensores do motor e retorna diagnostico de anomalia "
        "e risco de manutencao. A inferencia classica responde em menos de 1 ms "
        "e a inferencia quantica roda no simulador Qiskit (QSVC e VQC). "
        "Sensores obrigatorios: tensao_V, corrente_A, rpm, temperatura_C. Os "
        "demais sao opcionais e, quando ausentes, sao imputados pela mediana de "
        "operacao normal. A imputacao e sinalizada em `sensores_imputados`, e a "
        "confianca da resposta deve ser interpretada com cautela nesses casos."
    ),
    version="1.1.0",
    lifespan=lifespan,
)


def require_api_key(x_api_key: Optional[str] = Header(None)):
    """Dependencia de autenticacao para endpoints de escrita.

    Ativa somente quando FORZY_API_KEY esta definida no ambiente. Isso mantem
    o modo de demonstracao simples (sem chave, sem atrito) e ainda oferece uma
    barreira minima de producao quando a variavel e configurada no deploy.
    """
    if API_KEY is None:
        return
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail=f"Header X-API-Key ausente ou invalido. Configure {API_KEY_ENV_VAR} "
                   "no cliente e no servidor.",
        )


class Leituras(BaseModel):
    tensao_V: float = Field(..., description="Tensao em volts. Obrigatorio.")
    corrente_A: float = Field(..., description="Corrente em amperes. Obrigatorio.")
    rpm: float = Field(..., description="Rotacao em RPM. Obrigatorio.")
    temperatura_C: float = Field(..., description="Temperatura em graus Celsius. Obrigatorio.")
    vibracao_mm_s: Optional[float] = Field(None, description="Vibracao em mm/s.")
    pressao_bar: Optional[float] = Field(None, description="Pressao em bar.")
    eficiencia_pct: Optional[float] = Field(None, description="Eficiencia em porcentagem.")
    harmonicos_thd_pct: Optional[float] = Field(None, description="Harmonicos em %THD.")
    corrente_partida_A: Optional[float] = Field(None, description="Corrente de partida em amperes.")


class PredictRequest(BaseModel):
    equipamento_id: str = Field("motor-01", description="Identificador do ativo.")
    leituras: Leituras
    modelo: Literal["classico", "quantico", "ambos"] = Field(
        "classico",
        description="Rota de inferencia. A opcao 'quantico' exige um buffer com "
                    f"{WINDOW_SIZE} leituras para a anomalia janelada.",
    )


class JanelaRequest(BaseModel):
    equipamento_id: str = "motor-01"
    janela: list[Leituras] = Field(
        ..., min_length=WINDOW_SIZE, max_length=WINDOW_SIZE,
        description=f"Exatamente {WINDOW_SIZE} leituras consecutivas, uma por minuto.",
    )


def _log_prediction(equipamento_id, leituras, resultado, modelo, latencia_ms):
    # Uma falha no log nao pode derrubar uma predicao ja computada, por isso o
    # registro e best effort: o erro e avisado no console, mas a resposta HTTP
    # segue normalmente para o cliente.
    try:
        conn = _db()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO predicoes (ts, equipamento_id, leituras, resultado, "
                    "modelo_solicitado, latencia_total_ms) VALUES (?,?,?,?,?,?)",
                    (time.time(), equipamento_id, json.dumps(leituras),
                     json.dumps(resultado, ensure_ascii=False), modelo, latencia_ms),
                )
        finally:
            conn.close()
    except sqlite3.Error as exc:
        print(f"AVISO: log de predicao falhou ({exc})", flush=True)


@app.post("/predict", summary="Diagnostico de 1 leitura (anomalia e manutencao)")
def predict(req: PredictRequest, _auth=Depends(require_api_key)):
    t0 = time.perf_counter()
    try:
        result = service.diagnose(
            req.equipamento_id, req.leituras.model_dump(), modelo=req.modelo
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    total_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    result["latencia_total_ms"] = total_ms
    _log_prediction(req.equipamento_id, req.leituras.model_dump(), result,
                    req.modelo, total_ms)
    return result


@app.post("/predict/janela", summary="Anomalia quantica com janela explicita de 10 leituras")
def predict_janela(req: JanelaRequest, _auth=Depends(require_api_key)):
    t0 = time.perf_counter()
    try:
        janela = []
        for leitura in req.janela:
            completed, _ = service.validate_and_impute(leitura.model_dump())
            janela.append(completed)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    result = service.predict_anomaly_quantum(janela=janela)
    total_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    result["latencia_total_ms"] = total_ms
    _log_prediction(req.equipamento_id, {"janela": f"{WINDOW_SIZE} leituras"},
                    result, "quantico:janela", total_ms)
    return result


@app.get("/history", summary="Ultimas predicoes registradas (rastreabilidade)")
def history(limit: int = Query(50, ge=1, le=500), equipamento_id: Optional[str] = None):
    conn = _db()
    query = "SELECT ts, equipamento_id, leituras, resultado, modelo_solicitado, " \
            "latencia_total_ms FROM predicoes"
    params: list = []
    if equipamento_id:
        query += " WHERE equipamento_id = ?"
        params.append(equipamento_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    return [
        {"ts": r[0], "equipamento_id": r[1], "leituras": json.loads(r[2]),
         "resultado": json.loads(r[3]), "modelo_solicitado": r[4],
         "latencia_total_ms": r[5]}
        for r in rows
    ]


@app.get("/models", summary="Modelos carregados e metricas de validacao (holdout)")
def models():
    return {
        "sensores": {"obrigatorios": ["tensao_V", "corrente_A", "rpm", "temperatura_C"],
                     "opcionais_imputaveis": [c for c in SENSOR_COLS if c not in
                                              ["tensao_V", "corrente_A", "rpm", "temperatura_C"]]},
        "metricas_holdout": service.metrics,
    }


@app.get("/health", summary="Status do servico (nao exige autenticacao)")
def health():
    return {"status": "ok", "modelos_carregados": True,
            "cenarios": ["deteccao_anomalia", "predicao_manutencao"],
            "rotas_de_inferencia": ["classico", "quantico", "ambos"],
            "autenticacao_ativa": API_KEY is not None}
