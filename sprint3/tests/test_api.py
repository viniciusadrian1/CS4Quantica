"""
Testes de contrato da API (FastAPI TestClient, sem precisar subir uvicorn).

Cobre: health check, predicao classica de ponta a ponta, rejeicao de leitura
invalida (422), indicacao do modelo na resposta, autenticacao por API key
quando FORZY_API_KEY esta configurada, e o endpoint /models.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

LEITURA_NORMAL = {
    "tensao_V": 220.0, "corrente_A": 8.0, "rpm": 1450.0, "temperatura_C": 60.0,
    "vibracao_mm_s": 3.5, "pressao_bar": 5.0, "eficiencia_pct": 88.0,
    "harmonicos_thd_pct": 3.5, "corrente_partida_A": 0.0,
}


@pytest.fixture()
def client_sem_auth(monkeypatch):
    monkeypatch.delenv("FORZY_API_KEY", raising=False)
    # api.py le common.API_KEY na importacao do modulo; forcamos reimport
    # limpo dos dois modulos para refletir a variavel de ambiente do teste.
    for mod in ("common", "api"):
        sys.modules.pop(mod, None)
    import api as api_module
    from fastapi.testclient import TestClient

    with TestClient(api_module.app) as c:
        yield c


@pytest.fixture()
def client_com_auth(monkeypatch):
    monkeypatch.setenv("FORZY_API_KEY", "segredo-de-teste")
    for mod in ("common", "api"):
        sys.modules.pop(mod, None)
    import api as api_module
    from fastapi.testclient import TestClient

    with TestClient(api_module.app) as c:
        yield c


def test_health_nao_exige_autenticacao(client_sem_auth):
    resp = client_sem_auth.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["autenticacao_ativa"] is False


def test_predict_classico_retorna_diagnostico_completo(client_sem_auth):
    resp = client_sem_auth.post("/predict", json={
        "equipamento_id": "teste-01", "modelo": "classico", "leituras": LEITURA_NORMAL,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "anomalia_classico" in body
    assert "manutencao_classico" in body
    assert body["anomalia_classico"]["modelo"].startswith("classico:")
    assert "latencia_total_ms" in body


def test_predict_rejeita_leitura_fora_da_faixa_fisica(client_sem_auth):
    leitura_invalida = {**LEITURA_NORMAL, "rpm": -50}
    resp = client_sem_auth.post("/predict", json={
        "equipamento_id": "teste-02", "modelo": "classico", "leituras": leitura_invalida,
    })
    assert resp.status_code == 422


def test_predict_rejeita_payload_sem_sensor_obrigatorio(client_sem_auth):
    resp = client_sem_auth.post("/predict", json={
        "equipamento_id": "teste-03", "modelo": "classico",
        "leituras": {"tensao_V": 220.0, "corrente_A": 8.0, "rpm": 1450.0},
    })
    assert resp.status_code == 422  # falha de validacao do Pydantic (campo obrigatorio ausente)


def test_models_expoe_metricas_de_holdout(client_sem_auth):
    resp = client_sem_auth.get("/models")
    assert resp.status_code == 200
    body = resp.json()
    assert "metricas_holdout" in body
    assert "cenario1_anomalia" in body["metricas_holdout"]


def test_history_retorna_lista(client_sem_auth):
    client_sem_auth.post("/predict", json={
        "equipamento_id": "teste-historico", "modelo": "classico", "leituras": LEITURA_NORMAL,
    })
    resp = client_sem_auth.get("/history", params={"limit": 5})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


class TestAutenticacaoPorApiKey:
    def test_sem_chave_no_header_e_rejeitado_quando_auth_ativa(self, client_com_auth):
        resp = client_com_auth.post("/predict", json={
            "equipamento_id": "teste-auth", "modelo": "classico", "leituras": LEITURA_NORMAL,
        })
        assert resp.status_code == 401

    def test_chave_incorreta_e_rejeitada(self, client_com_auth):
        resp = client_com_auth.post(
            "/predict",
            json={"equipamento_id": "teste-auth", "modelo": "classico", "leituras": LEITURA_NORMAL},
            headers={"X-API-Key": "chave-errada"},
        )
        assert resp.status_code == 401

    def test_chave_correta_e_aceita(self, client_com_auth):
        resp = client_com_auth.post(
            "/predict",
            json={"equipamento_id": "teste-auth", "modelo": "classico", "leituras": LEITURA_NORMAL},
            headers={"X-API-Key": "segredo-de-teste"},
        )
        assert resp.status_code == 200

    def test_health_continua_livre_mesmo_com_auth_ativa(self, client_com_auth):
        resp = client_com_auth.get("/health")
        assert resp.status_code == 200
        assert resp.json()["autenticacao_ativa"] is True
