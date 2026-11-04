# FORZY - QML integrado ao Digital Twin

Documentação final do Challenge, disciplina de Computação Quântica e IA, FIAP, turma 2TIAPF. Consolidação da sprint 4 em **03/11/2026**.

O projeto integra detecção de anomalias e classificação de estados de manutenção de um motor industrial. Usa dados sintéticos, modelos clássicos, QSVC e VQC em simulador Qiskit, API FastAPI, histórico SQLite e dashboard Streamlit.

**A sprint 4 não altera o código nem retreina os modelos.** Os arquivos da sprint 3 foram preservados. O README histórico continua em `sprint3/README.md`; use este guia e o relatório final para as ressalvas identificadas na consolidação.

## Materiais finais

- [Relatório final (PDF)](docs/sprint4/entrega/Documentacao_Final_FORZY_Sprint4.pdf)
- [Apresentação editável (PPTX)](docs/sprint4/entrega/Apresentacao_Final_FORZY_Sprint4.pptx)
- [Apresentação (PDF)](docs/sprint4/entrega/Apresentacao_Final_FORZY_Sprint4.pdf)
- [Roteiro](docs/sprint4/entrega/Roteiro_de_Apresentacao.md)

## Autores

- Augusto Oliveira Codo de Sousa - RM502080
- Felipe de Oliveira Cabral - RM561720
- Gabriel Tonelli Avelino Dos Santos - RM564705
- Sofia Bueris Netto de Souza - RM565818
- Vinícius Adrian Siqueira de Oliveira - RM564962

## Navegação

```text
repositorio/
  README.md                         Guia atual de navegação e reprodução
  sprint3/
    api.py                          Contrato HTTP, chave opcional e SQLite
    common.py                       Parâmetros e conexão com o núcleo S2
    inference.py                    Serviço híbrido e buffer por ativo
    dashboard.py                    Interface Streamlit e replay
    train_and_persist.py             Treino original, opcional nesta entrega
    evaluate_integration.py          Benchmark original, opcional
    requirements.txt                Faixas de dependências do projeto
    models/                         Modelos, pré-processadores e métricas
    sprint2_core/                   Pipeline e dataset sintético herdados
    tests/                          Suíte original de testes
    relatorio/                      JSONs, capturas, GIF e relatório S3
  docs/
    sprint3/                        Planejamento e relatório histórico
    sprint4/
      entrega/                     PDF final, slides, roteiro e guia de submissão
      BIBLIOGRAFIA_TECNICA.md       Referências consultadas na revisão S4
      RELATORIO_FINAL.md            Fonte textual do relatório final
      REGISTRO_EVOLUCAO.md          Registro antes/depois e evidências
      PENDENCIAS_E_ROADMAP.md       Lacunas, razões e critérios de aceite
      metricas_consolidadas.csv     Valores históricos com fonte
      conferencia_dataset.json     Contagens diretas do CSV
      inventario_fontes.json        37 arquivos originais com SHA-256
      conferencia_regra_manutencao.json
                                   Concordância total e no teste reconstruído
      baseline_majoritaria_manutencao.json
                                   Baseline, índices e sobreposição temporal
      conferir_regra.py             Recompõe a regra e avalia os índices da baseline
      conferir_baseline.py          Reconstrói a divisão, baseline e sobreposição
```

O relatório final, a apresentação e o roteiro estão em [`docs/sprint4/entrega/`](docs/sprint4/entrega/). No pacote ZIP, também estão na raiz da entrega. Os artefatos originais completos da sprint 1 não foram fornecidos. A sprint 2 está representada pelo núcleo embarcado e pelo histórico da sprint 3.

## Instalação em Windows / PowerShell

Parta da pasta `repositorio/`. Os comandos abaixo usam diretamente o Python do ambiente virtual, sem depender de ativação de scripts.

```powershell
Set-Location .\sprint3
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

O material anterior menciona Qiskit 1.4 e qiskit-machine-learning 0.8. O arquivo de requisitos usa faixas mais amplas e não há lockfile nem versão de Python registrada no benchmark. Preserve ou recupere o ambiente original quando possível. A instalação e a carga dos arquivos joblib devem ser validadas antes de uma demonstração; não foram executadas nesta sprint documental.

## Execução com modelos já persistidos

Terminal 1, dentro de `sprint3/`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Terminal 2, também dentro de `sprint3/`:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501
```

Abra [dashboard local](http://127.0.0.1:8501), [OpenAPI](http://127.0.0.1:8000/docs) ou [saúde da API](http://127.0.0.1:8000/health). O dashboard fornece replay do dataset, seleção de rota, alertas e comparação dos resultados. A API cria `digital_twin.db` ao iniciar e mantém o buffer em memória.

Não é necessário executar `train_and_persist.py` para o fluxo normal. Ele **sobrescreve os modelos e as métricas**. Se houver necessidade de reproduzir o treino, use uma cópia de trabalho separada dos originais inventariados. O fallback de re-fit do QSVC referenciado no código não está incluído no pacote; se a desserialização falhar, a primeira ação deve ser conferir versões e ambiente.

## Requisição de demonstração

Com a API no ar, em outro terminal:

```powershell
$payloadForzy = @{
    equipamento_id = 'motor-01'
    modelo = 'ambos'
    leituras = @{
        tensao_V = 220.1
        corrente_A = 12.3
        rpm = 1452
        temperatura_C = 85.2
        vibracao_mm_s = 6.1
        pressao_bar = 6.6
        eficiencia_pct = 84.0
        harmonicos_thd_pct = 3.9
        corrente_partida_A = 0.0
    }
} | ConvertTo-Json -Depth 4
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/predict' -ContentType 'application/json' -Body $payloadForzy
```

Esse comando ilustra o contrato; não promete reproduzir uma classificação específica. Sem dez leituras no buffer, a anomalia quântica retorna um aviso. Para demonstração representativa, use o replay de leituras consecutivas do dataset, em vez de repetir dez vezes uma leitura idêntica.

## API e autenticação

| Endpoint | Função |
|---|---|
| `POST /predict` | Anomalia e manutenção para uma leitura, com rota `classico`, `quantico` ou `ambos` |
| `POST /predict/janela` | Anomalia QSVC para dez leituras explícitas |
| `GET /history` | Histórico, com filtro por equipamento e limite |
| `GET /models` | Sensores e métricas históricas |
| `GET /health` | Estado do serviço |

A API exige tensão, corrente, RPM e temperatura. Os cinco sensores restantes são opcionais. `/predict` informa as imputações; `/predict/janela` não expõe a mesma lista no retorno.

Se a variável de ambiente `FORZY_API_KEY` estiver definida **antes de iniciar o servidor**, os POST exigem o header `X-API-Key` correspondente. Os GET continuam sem essa proteção. O modo padrão sem chave deve ficar restrito à demonstração local. A compatibilidade do dashboard e do script de benchmark com a configuração de chave precisa ser considerada antes de ativá-la: esses clientes não expõem o mesmo fluxo de configuração de autenticação no material entregue.

## Testes e avaliação existentes

Os comandos pertencem ao produto anterior e estão documentados para reprodução futura:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
.\.venv\Scripts\python.exe inference.py
```

A inspeção estática identifica 32 casos incluindo parametrização, mas não é evidência de aprovação. A suíte e o smoke test **não foram executados na consolidação S4**. O workflow `.github/workflows/tests.yml` citado no README antigo não está no pacote; não há CI comprovada nesta entrega.

`evaluate_integration.py` mede serviço e, quando a API está disponível, HTTP e carga. Ele sobrescreve `relatorio/avaliacao_integrada.json` e pode inserir predições no histórico. Execute somente em uma cópia de trabalho se precisar de um novo ensaio. O script usa requisições sem header de chave. Não confunda métricas de uma nova execução com os números históricos do relatório.

## Resultados principais e limites

| Indicador histórico | Valor | Fonte |
|---|---:|---|
| RF manutenção, acurácia / F1-macro | 96,26% / 0,9279 | `models/metrics.json` |
| VQC manutenção, acurácia / F1-macro | 65,59% / 0,5357 | `models/metrics.json` |
| QSVC anomalia janelada, F1 | 0,8584 | `models/metrics.json` |
| HTTP ambas as rotas, p95 | 718,792 ms | `relatorio/avaliacao_integrada.json` |

- O CSV tem 5.200 leituras e **424 anomalias**. O relatório antigo cita 430.
- Clássicos pontuais e QSVC janelado não constituem comparação equivalente. O F1 do QSVC não comprova vantagem quântica.
- O pré-processamento clássico é ajustado antes do split; as janelas sobrepostas são separadas aleatoriamente. Há limites de independência da avaliação.
- A manutenção classifica estados sintéticos. Não estima tempo até falha ou RUL.
- O código atual é síncrono e a persistência SQLite é best effort. O buffer se perde ao reiniciar e não é compartilhado automaticamente por múltiplos workers.
- O JSON de latência não informa ambiente completo. Tempos amortizados em lote não equivalem à latência unitária ou HTTP.
- As tentativas adicionais de VQC estão somente no relato antigo; desempenho baixo não prova barren plateau.

## Preservação e publicação

`inventario_fontes.json` registra os caminhos **originais** do RAR. O conteúdo de `sprint3/` foi mantido byte a byte. Os dois arquivos da raiz original (`PLANEJAMENTO_SPRINT3.md` e `Relatorio_Final_Sprint3_FORZY.pdf`) foram organizados em `docs/sprint3/`. A cópia do relatório dentro de `sprint3/relatorio/` permanece no lugar.

O histórico anterior não foi reescrito para apagar divergências. A interpretação atual está no relatório final e neste README. Repositório do projeto: [https://github.com/viniciusadrian1/CS4Quantica](https://github.com/viniciusadrian1/CS4Quantica). O histórico desta publicação não permite datar individualmente mudanças das sprints anteriores. Não há licença de redistribuição informada no pacote original.

## Fundamentação da revisão documental

A [bibliografia técnica](docs/sprint4/BIBLIOGRAFIA_TECNICA.md) contém seis referências científicas e oficiais, consultadas nesta revisão. Os números do projeto continuam fundamentados nos arquivos internos E01-E12. As páginas atuais do Qiskit não substituem o registro do ambiente histórico.

## Publicação

Repositório: [https://github.com/viniciusadrian1/CS4Quantica](https://github.com/viniciusadrian1/CS4Quantica). Conta responsável: **viniciusadrian1 — Vinícius Adrian**. A documentação final inclui essa referência; a submissão no Drive e suas permissões devem ser conferidas pelo grupo.

## Conferência metodológica V1.5

Os 96,26% históricos do RF medem aproximação dos rótulos sintéticos de manutenção, derivados das mesmas variáveis rolantes fornecidas aos modelos. A regra existente reproduziu **4.935/4.940 rótulos (99,90%)** no total operacional, com cinco divergências registradas. Isso não comprova previsão de falhas independentes nem a necessidade de ML para reproduzir uma regra conhecida.

Nos **mesmos 988 índices de teste registrados pela baseline**, a regra recomposta obteve **988/988 concordâncias (100,00%) e F1-macro 1,0000**. As cinco divergências do total operacional ficaram fora desse recorte. Não houve ajuste de pesos ou limiares no teste. A igualdade dos índices entre regra e baseline é verificada pelo script, e o JSON registra a matriz de confusão e o hash da fonte dos índices. Essa concordância mede reprodução de rótulos sintéticos, não previsão independente de falhas.

A baseline constante normal, escolhida somente no treino, obteve **674/988 acertos (68,22%) e F1-macro 0,2028**. O holdout foi reconstruído com o protocolo do código (20%, estratificação, seed 42). Sem índices e ambiente históricos, sua identidade exata com o teste antigo não pode ser certificada. Os 68,24% continuam sendo a proporção de normais no dataset completo, uma população diferente.

Artefatos documentais em `docs/sprint4/`:

- `conferencia_regra_manutencao.json`: regra, hashes, ambiente, cinco divergências no total e avaliação dos mesmos 988 índices da baseline.
- `baseline_majoritaria_manutencao.json`: população de treino/teste, índices reconstruídos, métricas, ambiente e auditoria das janelas de manutenção.
- `conferir_regra.py` e `conferir_baseline.py`: scripts de conferência documental; não são novas funcionalidades do produto. Usam os arquivos existentes, não carregam RF/VQC e não alteram os originais. Se executados, atualizam somente seus respectivos JSONs de conferência; preserve uma cópia da entrega antes de repetir.

As versões das bibliotecas utilizadas estão registradas nos JSONs. A conferência da regra requer NumPy e pandas; a baseline também usa scikit-learn. O relatório final, seção 9.1, apresenta a metodologia e suas limitações. Não houve retreino, teste da API ou novo benchmark.

Para repetir a conferência documental, execute primeiro `conferir_baseline.py` e depois `conferir_regra.py`. O segundo lê os índices salvos pelo primeiro e verifica os hashes do CSV e do protocolo de treino. Preserve a entrega original antes de recalcular os JSONs.

## Dependência temporal das janelas de manutenção

Além da definição sintética dos rótulos, há dependência entre partições. Os atributos de manutenção usam janelas causais de 20 leituras sobre a sequência completa, antes do filtro operacional e do split aleatório estratificado. Para uma linha original i, a janela cobre `[max(0, i-19), i]`. O filtro operacional não deve comprimir esses índices.

Na divisão reconstruída, **988/988 janelas de teste (100%)** compartilham leituras com janelas do treino completo de 3.952 registros. A média é **29,25 janelas de treino sobrepostas** por teste (15 a 38). Cada leitura de teste também compõe **3 a 19 janelas posteriores de treino**, média **14,58**. São 28.900 pares de janelas com interseção e 14.401 participações em janelas posteriores.

Os números estão em `temporal_overlap_maintenance`, no JSON da baseline, com índices e contagens por registro. Referem-se à partição completa anterior à subamostra VQC de 400 registros; não são contagens específicas dessa subamostra. A causalidade de uma janela não garante independência de uma divisão aleatória. A auditoria não quantifica eventual inflação dos resultados nem reexecuta RF/VQC.

Proposta futura: blocos cronológicos por ativo, treino anterior ao teste e tratamento explícito das fronteiras, sem leituras brutas compartilhadas entre partições; transformadores ajustados somente no treino. O código e as métricas históricas permanecem preservados. A V1.5 corrige a interpretação documental, não o protocolo do produto.
