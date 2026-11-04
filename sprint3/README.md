# Sprint 3: Integração do QML ao Digital Twin (FORZY)

Solução funcional de ponta a ponta: leituras de sensores, pré-processamento, inferência
híbrida (clássico e quântico via simulador Qiskit), persistência em SQLite e dashboard.

Reusa os modelos e o pipeline validados nos Sprints 1 e 2 (`CS2Quantica/Sprint2Quantica`).

## Autores

- Augusto Oliveira Codo de Sousa - RM502080
- Felipe de Oliveira Cabral - RM561720
- Gabriel Tonelli Avelino Dos Santos - RM564705
- Sofia Bueris Netto de Souza - RM565818
- Vinícius Adrian Siqueira de Oliveira - RM564962

Disciplina: Computação Quântica e IA. Turma: 2TIAPF. Curso: Inteligência Artificial. Faculdade: FIAP.

## Instalação e execução

```bash
cd sprint3
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 1. Treina e persiste todos os modelos em models/ (5 a 10 minutos pela parte quântica)
python train_and_persist.py

# 2. Sobe a API na porta 8000
uvicorn api:app --port 8000

# 3. Em outro terminal: dashboard na porta 8501
streamlit run dashboard.py
```

Smoke test sem servidores: `python inference.py` (self-check com asserções).

Suíte de testes automatizados: `pytest tests/ -v` (32 casos, cobrindo o serviço de
inferência e o contrato da API).

## Autenticação da API (opcional)

Por padrão a API roda sem autenticação, adequado para desenvolvimento e demonstração.
Para exigir uma chave em qualquer ambiente exposto além da rede local, defina a
variável de ambiente `FORZY_API_KEY` no servidor e envie o header `X-API-Key` com o
mesmo valor em toda chamada aos endpoints de escrita:

```bash
FORZY_API_KEY=segredo uvicorn api:app --port 8000
curl -X POST http://127.0.0.1:8000/predict -H "X-API-Key: segredo" -H "Content-Type: application/json" -d '{...}'
```

O endpoint `GET /health` nunca exige autenticação.

## Arquitetura

```
replay CSV bruto (telemetria simulada, 1 leitura/min)
        |
        v
API FastAPI /predict: validacao de faixas fisicas + imputacao sinalizada
        |
        +- Camada 1 (sincrona): classico pontual (GB/RF/MLP/SVM, ~0,1 ms)
        |     anomalia (binario) + manutencao (RF 13 features, 4 classes)
        |
        +- Camada 2 (janelada): quantico, QSVC+Amplitude (2 qubits) sobre
        |     buffer de 10 leituras, e VQC (4 qubits) para manutencao,
        |     ~0,35 s/consulta no simulador (8,5 ms/amostra amortizado em lote)
        |
        +- SQLite digital_twin.db (toda predicao registrada, rastreabilidade)
        v
Dashboard Streamlit (estado do ativo, alertas, comparacao classico x quantico)
```

## API: contrato e exemplos

**Sensores obrigatórios** (do enunciado): `tensao_V`, `corrente_A`, `rpm`, `temperatura_C`.
**Opcionais**: `vibracao_mm_s`, `pressao_bar`, `eficiencia_pct`, `harmonicos_thd_pct`,
`corrente_partida_A`. Quando ausentes, são imputados pela mediana de operação normal e
listados em `sensores_imputados`. Atenção: vibração e THD carregam as assinaturas de
falha mais fortes, então quando eles são imputados a sensibilidade da detecção cai.

Documentação interativa (OpenAPI): `http://127.0.0.1:8000/docs`

### POST /predict: diagnóstico de 1 leitura

```bash
curl -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" -d '{
  "equipamento_id": "motor-01",
  "modelo": "ambos",
  "leituras": {
    "tensao_V": 220.1, "corrente_A": 12.3, "rpm": 1452, "temperatura_C": 85.2,
    "vibracao_mm_s": 6.1, "pressao_bar": 6.6, "eficiencia_pct": 84.0,
    "harmonicos_thd_pct": 3.9, "corrente_partida_A": 0.0
  }
}'
```

Resposta real, capturada do sistema em execução com o buffer aquecido por 12 leituras
normais. Por isso a rota quântica janelada, que enxerga as últimas 10 leituras, fica
perto da fronteira enquanto a triagem pontual dispara:

```json
{
  "equipamento_id": "motor-01",
  "sensores_imputados": [],
  "leituras_no_buffer": 13,
  "anomalia_classico": {
    "anomalia": true, "confianca": 0.9362, "score_anomalia": 0.9362,
    "modelo": "classico:gradient_boosting", "latencia_ms": 0.748
  },
  "manutencao_classico": {
    "risco_manutencao": "normal", "confianca": 0.95,
    "probabilidades": {"normal": 0.95, "monitoramento": 0.05, "alerta": 0.0, "critico": 0.0},
    "features_rolantes": {"vib_roll": 3.6262, "harm_roll": 3.6069,
                          "efic_roll": 88.2169, "efic_slope": -0.0462},
    "modelo": "classico:random_forest", "latencia_ms": 26.681
  },
  "anomalia_quantico": {
    "anomalia": false, "confianca": 0.5877, "score_anomalia": 0.4123,
    "modelo": "quantico:qsvc_amplitude (statevector exato/Qiskit, 2 qubits)",
    "latencia_ms": 347.708, "janela": "10 leituras"
  },
  "manutencao_quantico": {
    "risco_manutencao": "normal", "confianca": 0.5331,
    "probabilidades": {"normal": 0.5331, "monitoramento": 0.1351,
                       "alerta": 0.2481, "critico": 0.0837},
    "features_rolantes": {"vib_roll": 3.6262, "harm_roll": 3.6069,
                          "efic_roll": 88.2169, "efic_slope": -0.0462},
    "modelo": "quantico:vqc (PauliFeatureMap+EfficientSU2, 4 qubits)", "latencia_ms": 5.534
  },
  "latencia_total_ms": 381.059
}
```

Campos: `modelo` aceita `classico`, `quantico` ou `ambos`. A rota quântica de anomalia
opera sobre uma **janela de 10 leituras**. O serviço mantém um buffer por
`equipamento_id`; com buffer insuficiente a resposta traz um `aviso` em vez de uma predição.

### POST /predict/janela: anomalia quântica com janela explícita

Envia as 10 leituras de uma vez, sem depender do buffer do servidor:

```bash
curl -X POST http://127.0.0.1:8000/predict/janela -H "Content-Type: application/json" \
  -d '{"equipamento_id": "motor-01", "janela": [ {10 objetos de leituras} ]}'
```

### GET /history?limit=50&equipamento_id=motor-01

Últimas predições persistidas no SQLite, usadas para rastreabilidade e governança.

### GET /models e GET /health

Métricas de holdout de todos os modelos carregados, e status do serviço. O `/health`
também informa se a autenticação por chave está ativa.

### Erros

- `422`: sensor obrigatório ausente ou leitura fora da faixa física (por exemplo,
  `rpm=-50` ou `temperatura_C=300`). As faixas estão em `common.PHYSICAL_RANGES`.
- `401`: header `X-API-Key` ausente ou incorreto, apenas quando `FORZY_API_KEY` está
  configurada no servidor.

## Testes automatizados

```bash
pytest tests/ -v
```

A suíte tem 32 casos em dois arquivos. `tests/test_inference.py` cobre validação de
faixas físicas, imputação de sensores opcionais, rejeição de leituras fora do range,
as quatro combinações de cenário e rota de inferência, a regra determinística de
parada programada e o crescimento do buffer por equipamento. `tests/test_api.py` cobre
o contrato HTTP: diagnóstico completo, rejeição de leituras e payloads inválidos,
exposição de métricas em `/models` e o comportamento da autenticação por chave.

### Integração contínua (CI)

O workflow `.github/workflows/tests.yml` roda a suíte automaticamente a cada push ou
pull request que toque a pasta `sprint3/`. Ele instala as dependências, executa
`pytest tests/ -v` e o smoke test de `inference.py` em um ambiente limpo do GitHub
Actions, para pegar regressões antes de qualquer mudança chegar à branch principal.
Não treina modelos do zero: usa os artefatos já versionados em `models/`.

## Avaliação integrada e teste de carga

```bash
python evaluate_integration.py
```

Mede, de ponta a ponta e com leituras reais do dataset: latência do serviço de
inferência in-process, latência HTTP da API, um teste de carga com concorrência real
(1, 5 e 20 clientes simultâneos disparando requisições ao mesmo tempo contra
`/predict`) e os custos de treino registrados em `models/metrics.json`. O resultado é
salvo em `relatorio/avaliacao_integrada.json` e citado no relatório final (seção 5.3).
No teste realizado, a taxa de sucesso se manteve em 100% em todos os níveis de
concorrência, com o throughput saturando entre 19 e 21 requisições por segundo por
causa do GIL do Python (inferência clássica em CPU, no mesmo processo). Isso é
suficiente para o volume esperado do projeto (1 leitura por minuto por ativo), mas é
uma limitação real de escala, documentada no relatório junto com o caminho de mitigação
(múltiplos workers de processo ou fila de tarefas).

## Arquivos

| Arquivo | Papel |
|---|---|
| `sprint2_core/` | Código e dataset do Sprint 2 embarcados (entrega autossuficiente, sem depender da pasta `CS2Quantica/`) |
| `common.py` | Ponte com o código do Sprint 2, constantes compartilhadas e QNN do VQC |
| `train_and_persist.py` | Fase 1: treina e serializa todos os modelos em `models/` |
| `inference.py` | Fase 2: `HybridInferenceService` (validação, buffer, predição unitária) |
| `api.py` | Fase 3: FastAPI, autenticação opcional e log em SQLite |
| `dashboard.py` | Fase 4: Digital Twin visual (replay, alertas, comparação) |
| `tests/` | Fase adicional: suíte de testes automatizados (pytest) |
| `.github/workflows/tests.yml` | Integração contínua: roda a suíte a cada push/PR |
| `evaluate_integration.py` | Fase 5: avaliação integrada (latência, teste de carga, custos) |
| `models/metrics.json` | Métricas de holdout geradas pelo treino |

## Limitações conhecidas (documentadas no relatório)

- Os modelos quânticos rodam **apenas no simulador** (`FidelityStatevectorKernel` e
  Sampler de statevector). Em hardware NISQ real, a inferência do kernel custaria de
  1 a 10 segundos por consulta (ver o roadmap no relatório).
- A janela de 10 minutos da rota quântica dilui falhas mais curtas que a janela. A
  rota clássica pontual é a mitigação para esse caso.
- O dataset é o mesmo conjunto sintético definido e consolidado nos Sprints 1 e 2
  (seed 42). O enunciado deste sprint orienta reaproveitar os modelos e os dados já
  definidos, sem retreinar do zero, então isso não é uma limitação de execução, é o
  dado de entrada correto para a etapa de integração. Conectar o pipeline a
  telemetria real da FORZY é um passo natural de uma futura fase de operação, fora
  do escopo deste sprint, e está registrado no roadmap do relatório.
- O VQC do Cenário 2 quântico é exploratório: treinado em subamostra com SPSA, com
  acurácia bem abaixo do RF clássico. Três rodadas adicionais de melhoria foram
  testadas depois da primeira entrega (mais iterações do SPSA, três reinícios com
  sementes diferentes, e uma mudança estrutural real no feature map e no ansatz), e
  nenhuma superou a configuração original, que foi mantida como modelo persistido. A
  tentativa estrutural, inclusive, teve o pior resultado das três, um sintoma de
  barren plateau. O relatório (seção 6.4) documenta os números de cada tentativa.
- A API roda sem autenticação por padrão. Configure `FORZY_API_KEY` antes de expor o
  serviço além da rede local.
