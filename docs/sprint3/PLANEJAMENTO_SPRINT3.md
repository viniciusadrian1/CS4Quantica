# Planejamento — Sprint 3: Integração do QML ao Digital Twin (FORZY)

**Autores:** Augusto Oliveira Codo de Sousa - RM502080 · Felipe de Oliveira Cabral - RM561720 ·
Gabriel Tonelli Avelino Dos Santos - RM564705 · Sofia Bueris Netto de Souza - RM565818 ·
Vinícius Adrian Siqueira de Oliveira - RM564962
**Disciplina:** Computação Quântica · **Turma:** 2TIAPF · **Curso:** Inteligência Artificial · **Faculdade:** FIAP

> Base: inventário completo da pasta `CS2Quantica/Sprint2Quantica` (3 PDFs, 2 scripts, 4 notebooks, 5 CSVs, JSONs de métricas). Data: 2026-08-12.

> **STATUS: EXECUTADO.** Todas as 7 fases entregues em `sprint3/` — modelos treinados e persistidos,
> serviço de inferência com self-check, API testada, dashboard capturado, avaliação medida e
> Relatório Final em `Relatorio_Final_Sprint3_FORZY.pdf` (raiz do zip; 10 páginas).
> Desvios do plano: (1) Cenário 2 clássico ganhou 4 features rolantes causais (F1-macro 0,93);
> (2) o VQC consome as 4 features rolantes direto (sem PCA) — acc 0,66 vs. 0,25 do piloto;
> (3) confiança do QSVC via Platt scaling manual (sem CalibratedClassifierCV).
> Pós-entrega: revisão adversarial multi-agente confirmou 10 defeitos (lock nos buffers,
> validação do limit no /history, log best-effort, dedup de rerun no dashboard, fallback de
> re-fit do QSVC, warm-up no benchmark HTTP, score quântico no gráfico) — todos corrigidos
> e revalidados (self-check, API reiniciada, avaliação re-medida, PDF reconstruído).

---

## 1. O que já temos (herança do Sprint 2)

### Dados (prontos, nenhum trabalho necessário)
| Arquivo | Conteúdo | Uso no Sprint 3 |
|---|---|---|
| `dataset_motor_sprint2_bruto.csv` | 5.200 registros, 15 colunas, 9 sensores, 430 anomalias (8,15%), 120 adversariais SNR 8 dB | Fonte de treino + **replay como simulador de sensores** do dashboard |
| `dataset_motor_sprint2_preprocessado.csv` | PCA 4D em [-π,π], por amostra | Treino dos modelos clássicos |
| `dataset_motor_sprint2_windowed.csv` | 1.039 janelas (10×9→90D→PCA4) | Treino do pipeline quântico |
| `dataset_motor_sprint2_smote.csv` | Balanceado 50/50 | Só referência — **não usar em produção** |
| `class_weights.json` | Pesos balanced {0: 0,544; 1: 6,132} | Alternativa ao SMOTE no retreino |

### Código reutilizável (`arquitetura_hibrida_sprint2.py`)
- `ClassicalFeatureExtractor` — 10 features/sensor sobre janelas (n,10,9)→(n,90); stateless, compatível com sklearn Pipeline.
- `AmplitudeNormalizer`, `build_zz_feature_map`, `build_fourier_feature_map`, `build_amplitude_feature_map`.
- `make_hybrid_pipeline(feature_map, n_pca, amplitude_encoding)` — monta o Pipeline completo.
- `build_windows_from_bruto(csv, window_size=10, step=5, label_mode='any', seed=42)`.
- Determinismo total: `np.random.seed(42)`, `PCA(random_state=42)`, CV com `random_state=42`.

### Modelos validados (Cenário 1 — detecção de anomalias, 5-fold CV)
| Modelo | AUC | F1 (anomalia) | Latência inferência |
|---|---|---|---|
| MLP (64,32) | **0,969** | 0,708 | 0,001 ms |
| Gradient Boosting | 0,958 | 0,666 | 0,001 ms |
| Random Forest | 0,958 | 0,670 | 0,010 ms |
| SVM-RBF | 0,953 | 0,592 (recall 1,0 / precisão 0,415) | 0,026 ms |
| QSVC + Amplitude (2 qubits, depth 4) | 0,913 | **0,842** | 8,0 ms |
| QSVC + Fourier ω={1,2} (4 qubits, depth 11) | 0,909 | 0,825 | 9,9 ms |
| QSVC + ZZFeatureMap (descartado) | 0,643 | 0,629 | 11,4 ms |

### Decisões já tomadas no Sprint 2 (adotar, não rediscutir)
- **Arquitetura em 2 camadas**: triagem online clássica (GB/RF, <1 ms) + auditoria quântica assíncrona (QSVC+Amplitude no AerSimulator/statevector).
- ZZFeatureMap descartado (AUC baixa, depth 19, inviável NISQ).
- `class_weight='balanced'` em vez de SMOTE em produção.
- Roadmap NISQ já projetado: Amplitude fid. >0,98 (viável hoje); Fourier ~0,90 (requer ZNE); hardware real = 1–10 s/consulta, ~4 h/fold de treino → quântico fora do caminho síncrono.

### Lacunas herdadas (nada disso existe hoje)
1. **Nenhum modelo/scaler/PCA persistido** — tudo treinado em CV e descartado em memória. Sem isso, nada roda.
2. **Cenário 2 (predição de manutenção) sem modelo algum** — nem clássico nem quântico. Só existe o rótulo `classe_manutencao` (score determinístico causal: 0,40·vib + 0,30·harm + 0,20·efic + 0,10·slope; thresholds 1,5/0,8/0,3).
3. Nenhuma API, nenhum dashboard, nenhuma persistência de resultados.
4. `decision_function` do QSVC não é probabilidade calibrada — "confiança" honesta exige calibração.

---

## 2. O que o Sprint 3 pede (entregáveis × pesos)

| Entregável | Peso | Status atual |
|---|---|---|
| Arquitetura end-to-end (diagrama) | 15% | Decisão pronta em texto; diagrama do zero |
| Pipeline de inferência híbrida | 20% | Peças prontas; serviço do zero; **Cenário 2 do zero** |
| API de predição | 15% | Do zero (contratos de validação prontos) |
| Dashboard / Digital Twin | 15% | Do zero (replay do CSV como fonte) |
| Roadmap quântico + governança | 15% | Roadmap ~80% pronto nos PDFs; **LGPD/governança do zero** |
| Relatório Final PDF | 20% | Do zero (58 páginas de material citável) |

---

## 3. Decisões a tomar antes de codar

### D1 — Contrato de sensores: 4 pedidos vs. 9 treinados ⚠️ (risco central)
O enunciado pede API com tensão, corrente, RPM e temperatura; os modelos usam 9 canais (+ vibração, pressão, eficiência, THD, corrente de partida — justamente vibração e THD carregam as assinaturas de falha).
**Recomendação**: API aceita os 9 sensores, com os 4 do enunciado obrigatórios e os 5 restantes opcionais (imputação pela média da fase normal quando ausentes, com flag `imputed: true` e confiança rebaixada na resposta). Documentar explicitamente no contrato e no relatório.

### D2 — Cenário 2 (manutenção): o que servir
**Recomendação (esforço/honestidade)**: treinar um classificador clássico multiclasse (RF ou GB) sobre `classe_manutencao` do CSV bruto (dados prontos, ~30 min de trabalho) + **VQC** (EfficientSU2 + SPSA, já apontado como próximo passo no Sprint 2) como lado quântico, treinado em subamostra. Fallback se o VQC não convergir a tempo: QSVC binário sobre classes agregadas (crítico+alerta vs. resto), com a limitação documentada.

### D3 — Persistência dos modelos
`joblib.dump` do Pipeline completo após fit (transformers + QSVC são picklable). Plano B se o kernel não serializar na versão pinada: persistir transformers + dados de treino e re-fit determinístico (seed 42) no boot do serviço.

### D4 — Persistência de resultados/histórico
SQLite (stdlib, zero infra) — tabela única de predições (timestamp, leituras, saída de cada modelo, latência, model_id). Suficiente para o escopo acadêmico e cobre "rastreabilidade" da governança.

### D5 — Stack
FastAPI + Uvicorn (API), Streamlit (dashboard), joblib (modelos), SQLite (histórico). Reusar `requirements.txt` do Sprint 2 e adicionar só essas.

---

## 4. Arquitetura proposta (end-to-end)

```
┌─────────────┐   ┌──────────────────┐   ┌─────────────────────────────┐
│ Simulador de │   │ Pré-processamento │   │  Serviço de inferência       │
│ sensores     │──▶│ validação de faixa│──▶│  híbrida                     │
│ (replay CSV  │   │ buffer janela 10  │   │ ┌─────────────────────────┐ │
│  bruto, 1/s) │   │ scaler → PCA(4)   │   │ │Camada 1: clássico (<1ms)│ │
└─────────────┘   └──────────────────┘   │ │  GB/RF/MLP  anomalia+man.│ │
                                          │ └────────────┬────────────┘ │
                                          │        gatilho/sob demanda   │
                                          │ ┌────────────▼────────────┐ │
                                          │ │Camada 2: quântico (~8ms)│ │
                                          │ │ QSVC+Amplitude (Aer)    │ │
                                          │ │ VQC p/ manutenção       │ │
                                          │ └─────────────────────────┘ │
                                          └──────────┬──────────────────┘
                                                     ▼
                     ┌──────────┐   ┌───────────────────────┐
                     │ SQLite   │◀──│  API FastAPI           │
                     │ histórico│   │  /predict /health /docs│
                     └────┬─────┘   └──────────┬────────────┘
                          └────────────────────▼
                               ┌────────────────────┐
                               │ Dashboard Streamlit │
                               │ gauges, alertas,    │
                               │ histórico, status   │
                               └────────────────────┘
```

- O componente quântico entra como **camada 2**: acionado por parâmetro (`?model=quantum`), por gatilho (triagem clássica inconclusiva, score perto do limiar) ou em lote assíncrono — nunca no caminho crítico.
- Clássico opera ponto a ponto (1 leitura); quântico opera por janela (buffer das últimas 10 leituras) — as duas semânticas ficam explícitas no contrato da API.

## 5. Estrutura de pastas proposta

```
CS3Quantica/
├── CS2Quantica/…                  # herança intocada
└── sprint3/
    ├── requirements.txt           # Sprint 2 + fastapi, uvicorn, streamlit, joblib
    ├── train_and_persist.py       # Fase 1: treina TODOS os modelos e faz joblib.dump
    ├── models/                    # artefatos .joblib gerados (scalers, PCA, clássicos, QSVC, VQC)
    ├── inference.py               # serviço: carrega modelos, buffer de janela, predict unitário
    ├── api.py                     # FastAPI: /predict, /predict/quantum, /health, /history
    ├── dashboard.py               # Streamlit: replay do CSV → API → gauges/alertas/histórico
    ├── digital_twin.db            # SQLite (gerado em runtime)
    └── relatorio/                 # relatório final + diagramas
```

---

## 6. Plano de execução (ordem = dependência)

### Fase 1 — Treino e persistência (base de tudo) — ~½ dia
1. `train_and_persist.py`: importa `make_hybrid_pipeline`/`build_windows_from_bruto` do Sprint 2.
2. Treina e salva: 4 clássicos (anomalia) + QSVC+Amplitude (anomalia, janelado) + clássico multiclasse (manutenção) + VQC (manutenção).
3. Calibração da confiança: `CalibratedClassifierCV` (sigmoid) sobre os que não têm `predict_proba`.
4. Registra métricas de holdout + tempos de fit + n_qubits/depth (alimenta o roadmap).
5. **Checagem**: `joblib.load` + predict de 1 amostra reproduz o resultado do treino.

### Fase 2 — Serviço de inferência (`inference.py`) — ~½ dia
1. Classe `HybridInferenceService`: carrega artefatos no boot; mantém buffer deque(10) por equipamento.
2. `predict(leituras, scenario, model)` → {classe, risco, confiança, modelo_usado, latência}.
3. Validação de faixas físicas (corrente [0,20] A, temp [-10,120] °C, rpm [0,2000], vibração [0,12] mm/s…) + **clip pós-scaler para [-π,π]** (entradas fora do range de treino quebram o angle encoding).
4. Imputação dos sensores opcionais (D1) com flag na resposta.

### Fase 3 — API (`api.py`) — ~½ dia
- `POST /predict` (clássico, síncrono), `POST /predict/quantum` (janelado), `GET /history`, `GET /health`, `GET /models`.
- Resposta: `{anomalia: bool, risco_manutencao: str, confianca: float, modelo: str, latencia_ms: float, imputed: [...]}`.
- Toda predição gravada no SQLite. Documentação = OpenAPI automática do FastAPI + exemplos de request/response no README.

### Fase 4 — Dashboard (`dashboard.py`) — ~1 dia
- Replay do `bruto.csv` acelerado (1 linha/s = "tempo quase real"), chamando a API.
- Painéis: gauges dos 9 sensores, status do ativo (normal/monitoramento/alerta/crítico), alerta de anomalia com qual modelo detectou, comparação clássico×quântico lado a lado, histórico (do SQLite), latências.
- Casos de demonstração prontos: as 3 assinaturas de anomalia injetadas (sobreaquecimento +25 °C/+4 A; rolamento +3,5 mm/s; sobrecorrente +5 A) devem acender alertas visíveis.

### Fase 5 — Avaliação da solução integrada — ~½ dia
- Medir de ponta a ponta: latência API clássica vs. quântica, custo do simulador vs. n amostras de treino, throughput do replay.
- Registrar n_qubits, depth, tempos — sustenta o roadmap (pedido explícito do enunciado).

### Fase 6 — Roadmap + governança — ~½ dia (escrita)
- Roadmap: reaproveitar as projeções NISQ do Sprint 2 (Amplitude viável hoje; Fourier com ZNE; ~14 M shots/fold ≈ 4 h em hardware; inferência 1–10 s → quântico assíncrono). Acrescentar custo de QPU (pricing IBM Quantum) e a restrição `RawFeatureVector`×`ComputeUncompute` como limitação declarada.
- Governança (conteúdo novo): procedência dos dados (sintéticos, seed 42, versionados), rastreabilidade (model_id + log SQLite de toda predição), LGPD (dados de sensores industriais não são dados pessoais — argumentação curta), responsabilidade sobre alertas (humano no loop para ações de manutenção; alerta ≠ ordem de serviço).

### Fase 7 — Relatório Final (PDF) — ~1 dia
Estrutura já dada pelo enunciado: introdução (POC→integração), arquitetura (diagrama), pipeline+API (exemplos reais de request/response), dashboard (capturas), avaliação (números da Fase 5), roadmap+governança. Reusar tabelas/figuras dos 3 PDFs do Sprint 2 (58 págs. citáveis) e `feature_maps_comparacao.png`.

---

## 7. Riscos e mitigações

| # | Risco | Mitigação |
|---|---|---|
| 1 | Modelos não persistidos (herdado) | Fase 1 resolve; plano B = re-fit determinístico no boot (seed 42 + versões pinadas) |
| 2 | Cenário 2 sem modelo | Clássico multiclasse é barato; VQC com fallback binário agregado documentado |
| 3 | Mismatch 4×9 sensores | Contrato D1: 4 obrigatórios + 5 opcionais com imputação sinalizada |
| 4 | Kernel QSVC escala O(n²)/linear no predict | Treinar com fração controlada; medir antes de prometer latência; quântico fora do caminho síncrono |
| 5 | Entrada fora do range de treino → ângulo inválido | Clip para [-π,π] pós-transform na API |
| 6 | Janela de 10 min dilui falhas curtas | Rota clássica ponto a ponto cobre; documentar granularidade do alerta quântico |
| 7 | Comparação Q×C assimétrica (20% vs 100% dos dados) | Nunca citar "quântico vence em F1" sem a ressalva — vale para dashboard e relatório |
| 8 | Dataset 100% sintético | Ressalva padrão em toda métrica exibida |

## 8. Critério de pronto (Definition of Done)

- [ ] `python train_and_persist.py` gera todos os `.joblib` e imprime métricas de holdout.
- [ ] `uvicorn api:app` sobe; `POST /predict` com exemplo do README responde anomalia+risco+confiança+modelo em <100 ms (clássico) e <2 s (quântico simulado).
- [ ] Ambos os cenários (anomalia e manutenção) alternam clássico/quântico via parâmetro.
- [ ] `streamlit run dashboard.py` mostra replay com os 3 tipos de anomalia acendendo alertas.
- [ ] Toda predição registrada no SQLite com model_id (rastreabilidade).
- [ ] Relatório PDF cobre as 6 seções do enunciado, com capturas do dashboard e números medidos.
