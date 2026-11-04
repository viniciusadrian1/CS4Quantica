"""
Suite de testes do servico de inferencia hibrida (HybridInferenceService).

Cobre o que o smoke test antigo (demo() em inference.py) nao cobria de forma
isolada: casos de borda de validacao, cada rota de predicao em separado,
comportamento do buffer por equipamento e a regra de parada programada.

Uso: pytest tests/ -v   (executar a partir da pasta sprint3/)
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inference import HybridInferenceService, ValidationError
from common import OPTIONAL_SENSORS, REQUIRED_SENSORS, WINDOW_SIZE

NORMAL = {
    "tensao_V": 220.0, "corrente_A": 8.0, "rpm": 1450.0, "temperatura_C": 60.0,
    "vibracao_mm_s": 3.5, "pressao_bar": 5.0, "eficiencia_pct": 88.0,
    "harmonicos_thd_pct": 3.5, "corrente_partida_A": 0.0,
}
ANOMALA = {**NORMAL, "temperatura_C": 85.0, "corrente_A": 12.0,
           "vibracao_mm_s": 6.0, "pressao_bar": 6.5}


@pytest.fixture(scope="module")
def service():
    return HybridInferenceService()


class TestValidacaoDeEntrada:
    def test_leitura_completa_nao_imputa_nada(self, service):
        completed, imputed = service.validate_and_impute(NORMAL)
        assert imputed == []
        assert completed == NORMAL

    def test_sensores_opcionais_ausentes_sao_imputados(self, service):
        minimal = {s: NORMAL[s] for s in REQUIRED_SENSORS}
        completed, imputed = service.validate_and_impute(minimal)
        assert set(imputed) == set(OPTIONAL_SENSORS)
        assert all(s in completed for s in OPTIONAL_SENSORS)

    def test_sensor_obrigatorio_ausente_rejeita(self, service):
        incompleto = {k: v for k, v in NORMAL.items() if k != "rpm"}
        with pytest.raises(ValidationError):
            service.validate_and_impute(incompleto)

    @pytest.mark.parametrize("sensor,valor", [
        ("rpm", -50), ("temperatura_C", 300), ("corrente_A", -1),
        ("vibracao_mm_s", 999), ("tensao_V", 1000),
    ])
    def test_leitura_fora_da_faixa_fisica_rejeita(self, service, sensor, valor):
        leitura = {**NORMAL, sensor: valor}
        with pytest.raises(ValidationError):
            service.validate_and_impute(leitura)

    def test_leitura_no_limite_da_faixa_e_aceita(self, service):
        # limites inclusivos: nao deve levantar
        completed, _ = service.validate_and_impute({**NORMAL, "rpm": 2000.0})
        assert completed["rpm"] == 2000.0


class TestPredicaoAnomaliaClassica:
    def test_leitura_normal_nao_e_anomalia(self, service):
        r = service.predict_anomaly_classical(NORMAL)
        assert r["anomalia"] is False
        assert 0.0 <= r["score_anomalia"] <= 1.0
        assert r["modelo"].startswith("classico:")

    def test_leitura_anomala_e_detectada(self, service):
        r = service.predict_anomaly_classical(ANOMALA)
        assert r["anomalia"] is True

    def test_modelo_desconhecido_rejeita(self, service):
        with pytest.raises(ValidationError):
            service.predict_anomaly_classical(NORMAL, model="modelo_inexistente")

    def test_latencia_e_reportada_e_positiva(self, service):
        r = service.predict_anomaly_classical(NORMAL)
        assert r["latencia_ms"] >= 0.0


class TestPredicaoAnomaliaQuantica:
    def test_buffer_insuficiente_retorna_none(self, service):
        r = service.predict_anomaly_quantum(equipamento_id="equip-sem-buffer")
        assert r is None

    def test_janela_explicita_de_10_leituras_funciona(self, service):
        rng = np.random.default_rng(0)
        janela = [
            {k: float(v + rng.normal(0, 0.01)) for k, v in NORMAL.items()}
            for _ in range(WINDOW_SIZE)
        ]
        r = service.predict_anomaly_quantum(janela=janela)
        assert r is not None
        assert "qsvc_amplitude" in r["modelo"]
        assert 0.0 <= r["score_anomalia"] <= 1.0

    def test_buffer_do_equipamento_preenche_a_janela(self, service):
        equip = "equip-buffer-cheio"
        for _ in range(WINDOW_SIZE):
            completed, _ = service.validate_and_impute(NORMAL)
            service.push_reading(equip, completed)
        r = service.predict_anomaly_quantum(equipamento_id=equip)
        assert r is not None
        assert r["janela"] == f"{WINDOW_SIZE} leituras"


class TestPredicaoManutencao:
    def test_motor_parado_aciona_regra_sem_modelo(self, service):
        r = service.predict_maintenance("equip-parado", {**NORMAL, "rpm": 0.0})
        assert r["risco_manutencao"] == "parada_programada"
        assert r["modelo"] == "regra:rpm_parada"
        assert r["confianca"] == 1.0

    def test_operacao_normal_classifica_como_normal_ou_monitoramento(self, service):
        equip = "equip-manutencao-normal"
        for _ in range(5):
            completed, _ = service.validate_and_impute(NORMAL)
            service.push_reading(equip, completed)
        r = service.predict_maintenance(equip, NORMAL, use_quantum=False)
        assert r["risco_manutencao"] in ("normal", "monitoramento")
        assert r["modelo"] == "classico:random_forest"

    def test_rota_quantica_retorna_todas_as_classes_possiveis(self, service):
        equip = "equip-manutencao-quantico"
        for _ in range(5):
            completed, _ = service.validate_and_impute(NORMAL)
            service.push_reading(equip, completed)
        r = service.predict_maintenance(equip, NORMAL, use_quantum=True)
        assert "vqc" in r["modelo"]
        assert set(r["probabilidades"].keys()) == {
            "normal", "monitoramento", "alerta", "critico"
        }
        # probabilidades sao arredondadas a 4 casas na resposta (inference.py),
        # entao a soma pode desviar de 1.0 por erro de arredondamento acumulado
        assert abs(sum(r["probabilidades"].values()) - 1.0) < 2e-4


class TestDiagnosticoCompleto:
    def test_diagnose_classico_nao_chama_rota_quantica(self, service):
        r = service.diagnose("equip-diag-classico", NORMAL, modelo="classico")
        assert "anomalia_classico" in r
        assert "anomalia_quantico" not in r

    def test_diagnose_ambos_inclui_as_duas_rotas(self, service):
        equip = "equip-diag-ambos"
        for _ in range(WINDOW_SIZE + 2):
            service.diagnose(equip, NORMAL, modelo="classico")
        r = service.diagnose(equip, NORMAL, modelo="ambos")
        assert "anomalia_classico" in r and "anomalia_quantico" in r
        assert "manutencao_classico" in r and "manutencao_quantico" in r

    def test_buffer_cresce_a_cada_diagnose(self, service):
        equip = "equip-buffer-crescente"
        n0 = service.buffer_len(equip)
        service.diagnose(equip, NORMAL, modelo="classico")
        assert service.buffer_len(equip) == n0 + 1
