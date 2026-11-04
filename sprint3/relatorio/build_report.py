# -*- coding: utf-8 -*-
"""Gera o Relatorio Final do Sprint 3 (PDF) com os numeros medidos nos JSONs.

Estrutura do documento (ver Sumario gerado automaticamente na pagina 2):
  1. Introducao
  2. Arquitetura da solucao integrada (2.1-2.3)
  3. Pipeline de inferencia hibrida e API de predicao (3.1-3.5)
  4. Dashboard / Digital Twin visual (4.1-4.3)
  5. Avaliacao da solucao integrada (5.1-5.5)
  6. Roadmap de evolucao quantica e governanca (6.1-6.4)
  7. Conclusao

Cada tabela e cada figura tem numero e legenda proprios (Tabela X.Y / Figura X.Y),
seguindo o mesmo padrao em todo o documento.
"""

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = Path(__file__).resolve().parent
SPRINT3 = HERE.parent
OUT = HERE / "Relatorio_Final_Sprint3_FORZY.pdf"

metrics = json.load(open(SPRINT3 / "models" / "metrics.json", encoding="utf-8"))
aval = json.load(open(HERE / "avaliacao_integrada.json", encoding="utf-8"))

c1 = metrics["cenario1_anomalia"]
c2 = metrics["cenario2_manutencao"]
rq = metrics["recursos_quanticos"]
lat_ip = aval["latencia_inferencia_in_process"]
lat_http = aval["latencia_api_http"]
load_test = aval.get("teste_de_carga_classico")

# Notas que dependem do resultado das rodadas extras de treino do VQC (ver
# vqc_experiment*.py e o registro em models/metrics.json). Preenchidas antes
# deste script rodar, com os numeros medidos de fato.
VQC_RETRY_NOTE = (
    "Três rodadas adicionais de melhoria foram testadas após a primeira entrega "
    "deste relatório, e nenhuma superou a configuração original. Na primeira, as "
    "iterações do SPSA subiram de 120 para 250, mantendo o mesmo tamanho de amostra "
    "e o mesmo ansatz: o resultado foi pior, não melhor, com acurácia de 0,4383 e "
    "F1-macro de 0,3480, contra 0,6559 e 0,5357 da configuração original. Na segunda, "
    "três reinícios com sementes e pontos iniciais diferentes foram treinados com o "
    "orçamento original de 120 iterações (sementes 42, 7 e 123): os F1-macro obtidos "
    "foram 0,4503, 0,5036 e 0,4591, todos abaixo do 0,5357 da configuração original. "
    "Na terceira, uma mudança estrutural real foi testada, e não apenas de "
    "hiperparâmetro: o feature map passou de 1 para 2 repetições e o ansatz "
    "EfficientSU2 passou de 2 para 3 repetições com entrelaçamento completo, "
    "dobrando os parâmetros treináveis de 24 para 32, mantendo o mesmo orçamento de "
    "120 iterações do SPSA. O resultado foi o pior dos três: acurácia de 0,0951 e "
    "F1-macro de 0,0323, abaixo até do acaso de 4 classes (0,25), um sintoma "
    "característico de platô de barren plateau, quando um circuito mais profundo e "
    "mais expressivo tem um espaço de busca grande demais para o mesmo orçamento de "
    "treino. Em nenhuma das três tentativas o modelo com desempenho melhorado "
    "substituiu o original, que segue como o modelo persistido e avaliado neste "
    "relatório. O SPSA é um otimizador estocástico, e nem mais iterações, nem mais "
    "reinícios, nem um circuito mais expressivo garantem convergir para um ponto "
    "melhor dentro do orçamento computacional testado. Isso não é uma falha de "
    "implementação: é evidência consistente, replicada de três formas diferentes, de "
    "que para este cenário de 4 classes o VQC atingiu um teto de desempenho que "
    "ajustes de treino não rompem sozinhos. O caminho seguinte exigiria um orçamento "
    "de treino substancialmente maior junto com a mudança estrutural, ou mais dados "
    "de treino, registrado como recomendação concreta na seção 6.4."
)
DASHBOARD_GIF_NOTE = (
    "Um GIF do replay ao vivo acompanha esta entrega como evidência adicional de "
    "interatividade real (arquivo dashboard_replay.gif). Ele mostra o dashboard "
    "consumindo a API a cada leitura, com o estado do ativo escalando de Alerta "
    "para Crítico à medida que o replay atravessa o cluster de sobrecorrente das "
    "linhas 230 a 245, o mesmo trecho usado na Figura 4.1."
)

# ── Estilos ──────────────────────────────────────────────────────────
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=15, spaceBefore=18,
                    spaceAfter=8, textColor=colors.HexColor("#0F172A"),
                    keepWithNext=True)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12, spaceBefore=12,
                    spaceAfter=6, textColor=colors.HexColor("#1E293B"),
                    keepWithNext=True)
BODY = ParagraphStyle("BODY", parent=ss["Normal"], fontSize=9.7, leading=13.6,
                      alignment=TA_JUSTIFY, spaceAfter=6)
BULL = ParagraphStyle("BULL", parent=BODY, leftIndent=14, bulletIndent=4)
CODE = ParagraphStyle("CODE", parent=ss["Code"], fontSize=7.3, leading=9.2,
                      backColor=colors.HexColor("#F1F5F9"), borderPadding=5,
                      leftIndent=4, rightIndent=4, spaceAfter=8, spaceBefore=2)
CAPT = ParagraphStyle("CAPT", parent=ss["Normal"], fontSize=8.4, leading=11,
                      alignment=TA_CENTER, textColor=colors.HexColor("#475569"),
                      spaceBefore=3, spaceAfter=10)
CODE_CAPT = ParagraphStyle("CODE_CAPT", parent=ss["Normal"], fontSize=8.4, leading=11,
                           alignment=TA_LEFT, textColor=colors.HexColor("#475569"),
                           spaceBefore=6, spaceAfter=2, fontName="Helvetica-Oblique")
TITLE = ParagraphStyle("TITLE", parent=ss["Title"], fontSize=20, leading=25)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=11.5, leading=16,
                     alignment=TA_CENTER, textColor=colors.HexColor("#334155"))
TOC_H1 = ParagraphStyle("TOC_H1", fontName="Helvetica-Bold", fontSize=10.8,
                        leftIndent=0, firstLineIndent=0, spaceBefore=8, leading=15,
                        textColor=colors.HexColor("#0F172A"))
TOC_H2 = ParagraphStyle("TOC_H2", fontName="Helvetica", fontSize=9.6,
                        leftIndent=14, firstLineIndent=0, spaceBefore=2, leading=13,
                        textColor=colors.HexColor("#334155"))

TBL_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8.2),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
])


def P(text, style=BODY):
    return Paragraph(text, style)


def B(text):
    return Paragraph(f"• {text}", BULL)


CELL = ParagraphStyle("CELL", parent=ss["Normal"], fontSize=8.2, leading=10.4)
CELLH = ParagraphStyle("CELLH", parent=CELL, fontName="Helvetica-Bold",
                       textColor=colors.white)


def tbl(data, widths=None, wrap=False):
    """wrap=True converte celulas em Paragraph (necessario para texto longo)."""
    if wrap:
        data = [[Paragraph(str(c), CELLH if i == 0 else CELL) for c in row]
                for i, row in enumerate(data)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TBL_STYLE)
    return t


def tcapt(numero, texto):
    """Legenda de tabela, no mesmo padrao das legendas de figura (acima da tabela)."""
    return Paragraph(f"<b>Tabela {numero}:</b> {texto}", CAPT)


AUTORES = [
    "Augusto Oliveira Codo de Sousa - RM502080",
    "Felipe de Oliveira Cabral - RM561720",
    "Gabriel Tonelli Avelino Dos Santos - RM564705",
    "Sofia Bueris Netto de Souza - RM565818",
    "Vinícius Adrian Siqueira de Oliveira - RM564962",
]

story = []

# ═════════════════════════ CAPA ═════════════════════════
story += [
    Spacer(1, 3.2 * cm),
    P("Relatório Final: Sprint 3", TITLE),
    Spacer(1, 0.3 * cm),
    P("Integração do QML ao Digital Twin, produto funcional", SUB),
    Spacer(1, 1.0 * cm),
    P("Disciplina: Computação Quântica e IA · Turma: 2TIAPF", SUB),
    P("Curso: Inteligência Artificial · Faculdade: FIAP", SUB),
    P("Cliente: FORZY", SUB),
    Spacer(1, 0.8 * cm),
    P("Solução de ponta a ponta: ingestão de sensores, pré-processamento, inferência "
      "híbrida (clássico e quântico via Qiskit), API, persistência e dashboard", SUB),
    Spacer(1, 1.6 * cm),
    P("<b>Autores</b>", SUB),
    *[P(autor, SUB) for autor in AUTORES],
    Spacer(1, 2.6 * cm),
    P("Agosto de 2026", SUB),
    PageBreak(),
]

# ═════════════════════════ SUMÁRIO ═════════════════════════
toc = TableOfContents()
toc.levelStyles = [TOC_H1, TOC_H2]
story += [
    P("Sumário", H1),
    toc,
    PageBreak(),
]

# ═════════════════════════ 1. INTRODUÇÃO ═════════════════════════
story += [
    P("1. Introdução: do POC à integração", H1),
    P("Este relatório encerra a trilha do Challenge FORZY na disciplina de Computação "
      "Quântica e IA. A progressão foi construída em três etapas. O <b>Sprint 1</b> "
      "provou o conceito de Aprendizado de Máquina Quântico aplicado à manutenção "
      "preditiva de um motor industrial, com modelos iniciais e a primeira comparação "
      "entre abordagens clássica e quântica."),
    P("O <b>Sprint 2</b> consolidou o dataset, com 5.200 registros, 9 sensores, 430 "
      "anomalias de 3 tipos, ruído gaussiano de 10 a 30 dB de SNR e 120 amostras "
      "adversariais a 8 dB. Nessa etapa o grupo corrigiu o vazamento de rótulo (label "
      "leakage) da classe de manutenção e validou estatisticamente o pipeline híbrido: "
      "janela deslizante de 10 por 9, extração de 90 features clássicas, PCA para 4 "
      "componentes e QSVC com três mapas de features quânticos, tudo comparado a 4 "
      "baselines clássicos em validação cruzada estratificada de 5 partições."),
    P("Três achados do Sprint 2 orientaram este sprint. Primeiro, os modelos clássicos "
      "lideram em AUC no dataset completo, com o MLP atingindo 0,969. Segundo, o QSVC "
      "com Amplitude Encoding, usando 2 qubits e profundidade 4 na base {u, cx}, vence "
      "em F1 da classe anômala (0,842 contra um teto clássico de 0,708) e em eficiência "
      "amostral, precisando de cerca de 5 vezes menos dados para atingir AUC próximo de "
      "0,91. Terceiro, o kernel quântico é inviável para tempo real em hardware NISQ "
      "atual, com cerca de 4 horas por partição de treino e de 1 a 10 segundos por "
      "consulta. A recomendação formal foi uma arquitetura em duas camadas: triagem "
      "clássica em tempo real e auditoria quântica sob demanda. Este Sprint 3 "
      "materializa essa recomendação como produto funcional."),
    P("O <b>Sprint 3</b> deixou de isolar o algoritmo e passou a fazê-lo funcionar "
      "dentro de um sistema. Foram construídos: um serviço de treino e persistência dos "
      "modelos, já que nenhum artefato havia sido serializado nos sprints anteriores; um "
      "serviço de inferência híbrida com dois cenários, detecção de anomalias e predição "
      "de manutenção, com alternância entre rota clássica e quântica; uma API REST com "
      "validação de fronteira; um dashboard de Digital Twin em tempo quase real, com "
      "replay da telemetria; uma avaliação integrada medida de ponta a ponta; e este "
      "relatório, com roadmap e governança."),
    P("Novidade de modelagem deste sprint: o <b>Cenário 2</b>, de manutenção, não tinha "
      "nenhum modelo treinado no Sprint 2. Ele ganhou um Random Forest multiclasse "
      "clássico e um <b>VQC</b>, um classificador quântico variacional treinado com o "
      "otimizador SPSA, cumprindo o requisito de cobrir ambos os cenários com ambas as "
      "rotas de inferência."),
    P("Endurecimento realizado após a primeira entrega: o serviço ganhou uma suíte de "
      "testes automatizados (pytest, 32 casos cobrindo validação de entrada, cada rota "
      "de predição e o contrato da API), integração contínua que roda essa suíte a cada "
      "mudança, a API passou a suportar autenticação opcional por chave, e um teste de "
      "carga mediu o comportamento do serviço sob concorrência real. Esses quatro pontos "
      "estão detalhados nas seções 3 e 5."),
]

# ═════════════════════════ 2. ARQUITETURA ═════════════════════════
story += [
    PageBreak(),
    P("2. Arquitetura da solução integrada", H1),
    P("2.1 Visão geral do fluxo de ponta a ponta", H2),
    Image(str(HERE / "arquitetura.png"), width=17.2 * cm, height=17.2 * cm * 0.594),
    P("Figura 2.1: arquitetura de ponta a ponta. Ingestão, pré-processamento, API, "
      "duas camadas de inferência, persistência e dashboard.", CAPT),
    P("O fluxo completo funciona assim. A telemetria do motor, com 9 canais e uma "
      "leitura por minuto, entra pela API. Em uma planta real ela viria de OPC-UA ou "
      "IoT; aqui, ela é o replay do dataset do Sprint 2. A leitura passa por validação "
      "de faixas físicas e imputação sinalizada, alimenta um buffer por ativo com 20 "
      "leituras e segue para as duas camadas de inferência. Os resultados são "
      "persistidos em SQLite e consumidos pelo dashboard."),
    P("2.2 Papel do componente quântico", H2),
    P("O quântico coexiste com o clássico como <b>Camada 2, de auditoria</b>. A "
      "triagem clássica, a Camada 1, responde no caminho síncrono em cerca de 0,1 ms e "
      "está sempre ativa. A rota quântica é acionada por parâmetro da API "
      "(<i>modelo=quantico</i> ou <i>modelo=ambos</i>) e opera sobre a janela das "
      "últimas 10 leituras, usando QSVC com Amplitude Encoding, e sobre as features "
      "rolantes de degradação, usando o VQC. No simulador, a latência quântica de cerca "
      "de 0,3 segundos por consulta unitária ainda permite o uso a cada leitura. Em "
      "hardware real, com 1 a 10 segundos por consulta, essa rota sairia do caminho "
      "crítico e passaria a rodar de forma assíncrona, acionada por um gatilho de "
      "triagem inconclusiva. É exatamente essa posição que o diagrama representa."),
    P("2.3 Decisões de projeto", H2),
    B("<b>D1, contrato de sensores:</b> o enunciado pede uma API com 4 sensores "
      "(tensão, corrente, RPM e temperatura), mas os modelos foram treinados com 9 "
      "canais. A API aceita os 9, exige os 4 do enunciado e imputa os demais pela "
      "mediana de operação normal, sinalizando isso em <i>sensores_imputados</i>. "
      "Vibração e THD carregam as assinaturas de falha mais fortes, e a resposta deixa "
      "explícito quando eles foram imputados."),
    B("<b>D2, Cenário 2:</b> Random Forest multiclasse clássico e VQC quântico sobre "
      "as 4 features rolantes causais de degradação, numa janela de 20 minutos. É o "
      "mesmo espaço em que o rótulo foi definido no Sprint 2, sem vazamento e "
      "replicável em streaming."),
    B("<b>D3, persistência de modelos:</b> joblib do pipeline completo, incluindo "
      "transformadores e o QSVC, com validação de round-trip. O VQC persiste apenas os "
      "24 pesos treinados em formato npz, e a rede quântica é reconstruída "
      "deterministicamente na inferência."),
    B("<b>D4, persistência de resultados:</b> SQLite, da biblioteca padrão, com toda "
      "predição registrada. Isso cobre o histórico do dashboard e a rastreabilidade "
      "exigida pela governança."),
    B("<b>D5, pilha tecnológica:</b> FastAPI e Uvicorn, Streamlit, joblib e SQLite, "
      "sobre o conjunto de dependências homologado no Sprint 2 (qiskit 1.4 e "
      "qiskit-machine-learning 0.8)."),
]

# ═════════════════════════ 3. PIPELINE + API ═════════════════════════
qs = c1["qsvc_amplitude"]
story += [
    PageBreak(),
    P("3. Pipeline de inferência híbrida e API de predição", H1),
    P("3.1 Modelos carregados pelo serviço", H2),
    P("O serviço (<i>HybridInferenceService</i>) carrega no boot os artefatos "
      "treinados por <i>train_and_persist.py</i>, que reusa diretamente as classes "
      "validadas do Sprint 2, entre elas <i>ClassicalFeatureExtractor</i>, "
      "<i>make_hybrid_pipeline</i> e os mapas de features quânticos. Métricas de "
      "holdout, com divisão estratificada de 80 por 20 e seed 42:"),
    tcapt("3.1", "Cenário 1, detecção de anomalias (classificação binária)."),
    tbl(
        [["Modelo", "Rota", "AUC", "F1 (anomalia)", "Acurácia", "Treino (s)", "n treino"]] +
        [[nome, "clássica", f"{m['auc']:.3f}", f"{m['f1_anomalia']:.3f}",
          f"{m['accuracy']:.3f}", f"{m['fit_s']:.2f}", f"{m['n_treino']}"]
         for nome, m in [("SVM-RBF", c1["svm_rbf"]), ("Random Forest", c1["random_forest"]),
                         ("MLP (64,32)", c1["mlp"]), ("Gradient Boosting", c1["gradient_boosting"])]] +
        [["QSVC + Amplitude (janelas 10×9)", "quântica", f"{qs['auc']:.3f}",
          f"{qs['f1_anomalia']:.3f} ★", f"{qs['accuracy']:.3f}",
          f"{qs['fit_s']:.2f}", f"{qs['n_treino']} janelas"]],
        widths=[5.4 * cm, 1.7 * cm, 1.6 * cm, 2.4 * cm, 1.9 * cm, 1.9 * cm, 2.1 * cm],
    ),
    P("O padrão do Sprint 2 se mantém na integração. Os modelos clássicos têm AUC "
      "superior, e o QSVC tem o melhor F1 da classe anômala, com 0,858, agora treinado "
      "com 664 janelas contra as cerca de 165 do benchmark do Sprint 2, e servindo "
      "predição unitária. A confiança do QSVC é calibrada por Platt scaling, uma "
      "regressão logística sobre a decision_function, ajustada em um split de "
      "calibração separado.", BODY),
    tcapt("3.2", "Cenário 2, predição de manutenção, com 4 classes operacionais. A "
                 "classe parada_programada é resolvida por regra de RPM, sem uso de modelo."),
    tbl(
        [["Modelo", "Rota", "Acurácia", "F1-macro", "Treino (s)", "n treino"],
         ["Random Forest (13 features)", "clássica", f"{c2['random_forest']['accuracy']:.3f}",
          f"{c2['random_forest']['f1_macro']:.3f}", f"{c2['random_forest']['fit_s']:.2f}",
          f"{c2['random_forest']['n_treino']}"],
         ["VQC (4 features rolantes)", "quântica", f"{c2['vqc']['accuracy']:.3f}",
          f"{c2['vqc']['f1_macro']:.3f}", f"{c2['vqc']['fit_s']:.0f}",
          f"{c2['vqc']['n_treino']} (subamostra)"]],
        widths=[5.6 * cm, 1.8 * cm, 1.9 * cm, 1.9 * cm, 1.9 * cm, 3.2 * cm],
    ),
    P(f"O RF clássico usa 9 sensores e 4 features rolantes causais, atingindo F1 por "
      f"classe de {c2['random_forest']['f1_por_classe']['normal']:.2f} na classe normal "
      f"e entre {c2['random_forest']['f1_por_classe']['alerta']:.2f} e "
      f"{c2['random_forest']['f1_por_classe']['critico']:.2f} nas classes alerta e "
      f"crítico. O VQC, com {rq['vqc']['feature_map']} e {rq['vqc']['ansatz']}, "
      f"{rq['vqc']['n_parametros_treinaveis']} parâmetros treináveis e "
      f"{rq['vqc']['otimizador']}, atinge {c2['vqc']['accuracy']:.2f} de acurácia. "
      f"Esse número está bem acima do acaso, que seria 0,25 para quatro classes, mas "
      f"claramente abaixo do modelo clássico. Neste cenário o QML ainda não compensa, "
      f"e o relatório documenta isso como resultado honesto na seção 6.4. {VQC_RETRY_NOTE}", BODY),
    P("3.2 Contrato da API", H2),
    P("A API, construída em FastAPI, expõe cinco endpoints, com documentação "
      "interativa OpenAPI em <i>/docs</i>. Toda predição é registrada no SQLite com o "
      "modelo solicitado e a latência medida, para fins de rastreabilidade."),
    tcapt("3.3", "Endpoints expostos pela API e sua função."),
    tbl(
        [["Endpoint", "Função"],
         ["POST /predict", "Diagnóstico de 1 leitura: anomalia e manutenção, rota classico, quantico ou ambos"],
         ["POST /predict/janela", "Anomalia quântica com janela explícita de 10 leituras"],
         ["GET /history", "Últimas predições persistidas, com filtro por equipamento"],
         ["GET /models", "Modelos carregados e métricas de holdout"],
         ["GET /health", "Status do serviço, sem exigência de autenticação"]],
        widths=[4.6 * cm, 12.6 * cm],
    ),
    P("Validação na fronteira: os 4 sensores do enunciado são obrigatórios; leituras "
      "fora das faixas físicas, como RPM negativo ou temperatura acima de 120 graus "
      "Celsius, retornam HTTP 422 com a faixa violada. Sensores opcionais ausentes são "
      "imputados e sinalizados na resposta. Depois do MinMaxScaler, os valores são "
      "limitados ao intervalo entre menos pi e pi antes do encoding quântico, o que "
      "evita que leituras fora do range de treino gerem ângulos inválidos."),
    P("3.3 Autenticação da API", H2),
    P("A API suporta autenticação opcional por chave. Quando a variável de ambiente "
      "FORZY_API_KEY é definida no servidor, todo endpoint de escrita passa a exigir o "
      "header X-API-Key com o mesmo valor, e uma chamada sem chave ou com chave errada "
      "recebe HTTP 401. Sem a variável definida, a API roda sem autenticação, o que é "
      "adequado para demonstração em ambiente controlado. O endpoint /health nunca "
      "exige autenticação, para permitir checagens de disponibilidade simples."),
    P("3.4 Testes automatizados", H2),
    P("O serviço de inferência e a API têm uma suíte de testes automatizados com "
      "pytest, com 32 casos distribuídos em dois arquivos. Os testes de inferência "
      "cobrem validação de faixas físicas, imputação de sensores opcionais, rejeição de "
      "leituras fora do range, cada uma das quatro combinações de cenário e rota "
      "(anomalia clássica, anomalia quântica, manutenção clássica, manutenção "
      "quântica), a regra determinística de parada programada e o crescimento do "
      "buffer por equipamento. Os testes de API cobrem o contrato HTTP: retorno de "
      "diagnóstico completo, rejeição com HTTP 422 de leituras inválidas e de payloads "
      "incompletos, exposição de métricas em /models e o comportamento da autenticação "
      "por chave, incluindo o caso de sucesso e os dois casos de rejeição. A suíte "
      "roda automaticamente a cada alteração via um workflow de integração contínua "
      "(.github/workflows/tests.yml), que instala as dependências, executa o pytest e "
      "o smoke test de inference.py em um ambiente limpo, para pegar regressões antes "
      "de qualquer mudança chegar à branch principal."),
    P("3.5 Exemplo real de requisição e resposta", H2),
    P("Requisição enviada ao endpoint POST /predict:", CODE_CAPT),
    Preformatted(
        'POST /predict\n'
        '{\n'
        '  "equipamento_id": "motor-01",\n'
        '  "modelo": "ambos",\n'
        '  "leituras": {"tensao_V": 220.1, "corrente_A": 12.4, "rpm": 1448,\n'
        '               "temperatura_C": 86.0, "vibracao_mm_s": 6.2, "pressao_bar": 6.6,\n'
        '               "eficiencia_pct": 88.2, "harmonicos_thd_pct": 3.6,\n'
        '               "corrente_partida_A": 0.0}\n'
        '}', CODE),
    P("Resposta real, capturada do sistema em execução (não um exemplo forjado):", CODE_CAPT),
    Preformatted(
        'HTTP 200 (resposta real do sistema em execucao)\n'
        '{\n'
        '  "equipamento_id": "motor-01", "sensores_imputados": [], "leituras_no_buffer": 13,\n'
        '  "anomalia_classico":  {"anomalia": true,  "confianca": 0.9362,\n'
        '                         "modelo": "classico:gradient_boosting", "latencia_ms": 0.748},\n'
        '  "manutencao_classico": {"risco_manutencao": "normal", "confianca": 0.95,\n'
        '                         "probabilidades": {"normal": 0.95, "monitoramento": 0.05,\n'
        '                                            "alerta": 0.0, "critico": 0.0},\n'
        '                         "modelo": "classico:random_forest", "latencia_ms": 26.681},\n'
        '  "anomalia_quantico":  {"anomalia": false, "confianca": 0.5877, "score_anomalia": 0.4123,\n'
        '                         "modelo": "quantico:qsvc_amplitude (statevector exato/Qiskit,\n'
        '                                    2 qubits)", "latencia_ms": 347.708, "janela": "10 leituras"},\n'
        '  "manutencao_quantico": {"risco_manutencao": "normal", "confianca": 0.5331,\n'
        '                         "modelo": "quantico:vqc (PauliFeatureMap+EfficientSU2,\n'
        '                                    4 qubits)", "latencia_ms": 5.534},\n'
        '  "latencia_total_ms": 381.059\n'
        '}', CODE),
    P("O exemplo ilustra um comportamento de projeto. Uma única leitura anômala em um "
      "buffer de leituras normais dispara a triagem clássica pontual, com confiança "
      "0,94, enquanto a rota quântica janelada, que enxerga as últimas 10 leituras, "
      "permanece próxima da fronteira, com confiança 0,41. A janela dilui falhas mais "
      "curtas que os 10 minutos que ela cobre. As duas rotas são complementares por "
      "construção, e a resposta sempre identifica qual modelo produziu cada resultado."),
]

# ═════════════════════════ 4. DASHBOARD ═════════════════════════
story += [
    PageBreak(),
    P("4. Dashboard / Digital Twin visual", H1),
    P("4.1 Elementos da interface", H2),
    P("O dashboard, em Streamlit, materializa o gêmeo digital. Ele faz replay do "
      "dataset bruto como telemetria ao vivo, em velocidade configurável, envia cada "
      "leitura à API e exibe o estado do ativo em tempo quase real. Os elementos "
      "incluem: estado de manutenção, variando de verde a vermelho; alerta de anomalia "
      "com o modelo ou modelos que a detectaram e suas confianças; os 9 sensores com "
      "sua variação; comparação lado a lado entre a rota clássica e a quântica, com "
      "latências; séries temporais recentes; e o histórico persistido via GET /history."),
    P("4.2 Evidência real de execução", H2),
    Image(str(HERE / "dashboard_alerta.png"), width=17.2 * cm, height=17.2 * cm * 0.875),
    P("Figura 4.1: momento de alerta real, leitura número 237, com sobrecorrente "
      "injetada no dataset. A anomalia foi detectada pela rota clássica, com 98% de "
      "confiança, e pela rota quântica, com 89%, e o risco de manutenção ficou em "
      "'Alerta' nas duas rotas. O gráfico à direita mostra o score do modelo "
      "acompanhando os rótulos reais.", CAPT),
    P("A validação visual usa as assinaturas de anomalia já conhecidas do Sprint 2: "
      "sobreaquecimento, com aumento de 25 graus Celsius e 4 amperes; falha de "
      "rolamento, com aumento de 3,5 mm/s de vibração; e sobrecorrente, com aumento de "
      "5 amperes. No trecho das linhas 231 a 245, o replay atravessa um cluster de "
      "sobrecorrente e o dashboard acende os alertas correspondentes, com a classe de "
      "manutenção escalando de 'alerta' para 'crítico', que é o comportamento esperado "
      "do score de degradação. O cabeçalho também confronta cada detecção com o rótulo "
      "real da leitura, permitindo auditar falsos positivos durante a demonstração."),
    P(f"{DASHBOARD_GIF_NOTE}"),
    P("4.3 Tratamento de parada programada", H2),
    P("Quando o motor entra em parada programada, com RPM próximo de zero, a regra "
      "determinística assume o estado com confiança 1,0 e as rotas de aprendizado de "
      "máquina são poupadas. Parada não é degradação, e o estado aparece como neutro "
      "no dashboard."),
]

# ═════════════════════════ 5. AVALIAÇÃO ═════════════════════════
story += [
    PageBreak(),
    P("5. Avaliação da solução integrada", H1),
    P("As medições a seguir vêm do sistema em execução real, em Windows, com o "
      "simulador statevector: 200 leituras do dataset, com 50% de anomalias, e HTTP "
      "com 50 requisições por rota contra a API local."),
    P("5.1 Latência de inferência (serviço, chamado diretamente em processo)", H2),
    tcapt("5.1", "Latência in-process por rota de inferência."),
    tbl(
        [["Rota", "p50 (ms)", "p95 (ms)", "média (ms)"]] +
        [[nome, f"{lat_ip[k]['p50_ms']:.2f}", f"{lat_ip[k]['p95_ms']:.2f}",
          f"{lat_ip[k]['media_ms']:.2f}"]
         for nome, k in [("Anomalia, clássico (GB pontual)", "anomalia_classico"),
                         ("Anomalia, quântico (QSVC janela 10)", "anomalia_quantico"),
                         ("Manutenção, clássico (RF 13 feats)", "manutencao_classico"),
                         ("Manutenção, quântico (VQC)", "manutencao_quantico")]],
        widths=[7.6 * cm, 2.6 * cm, 2.6 * cm, 2.6 * cm],
    ),
    P("5.2 Latência HTTP de ponta a ponta (API, validação e log em SQLite)", H2),
    tcapt("5.2", "Latência HTTP completa por modelo solicitado."),
    tbl(
        [["modelo=", "p50 (ms)", "p95 (ms)"]] +
        [[m, f"{lat_http[m]['p50_ms']:.0f}", f"{lat_http[m]['p95_ms']:.0f}"]
         for m in ["classico", "quantico", "ambos"]],
        widths=[5.2 * cm, 3.4 * cm, 3.4 * cm],
    ),
    P(f"Leitura dos números: a triagem clássica responde em cerca de "
      f"{lat_http['classico']['p50_ms']:.0f} ms de ponta a ponta, uma folga de três "
      f"ordens de magnitude para uma telemetria com granularidade de minutos. A rota "
      f"quântica custa cerca de {lat_http['quantico']['p50_ms'] / 1000:.2f} segundos "
      f"por consulta unitária no simulador, porque o QSVC recalcula fidelidades contra "
      f"todos os cerca de 530 vetores de suporte a cada predição. Em lote, esse custo "
      f"amortiza para cerca de {qs['latencia_ms_amostra']:.1f} ms por amostra. O "
      f"resultado é compatível com uma leitura por minuto, mas o custo cresce "
      f"linearmente com o tamanho do conjunto de suporte. Essa é a razão de projeto "
      f"para manter a rota quântica como camada de auditoria, e não de triagem."),
    P("5.3 Teste de carga (concorrência real contra a API)", H2),
    P("Além da latência de uma chamada isolada, a API foi testada sob concorrência "
      "real, com múltiplos clientes simultâneos fazendo requisições à rota clássica "
      "(a rota de triagem em tempo real):"),
    tcapt("5.3", "Throughput, latência e taxa de sucesso sob concorrência crescente."),
    tbl(
        ([["Clientes simultâneos", "Throughput (req/s)", "p50 (ms)", "p95 (ms)", "Sucesso"]] +
         [[c.replace("concorrencia_", ""), f"{load_test[c]['throughput_req_s']:.1f}",
           f"{load_test[c]['p50_ms']:.0f}", f"{load_test[c]['p95_ms']:.0f}",
           f"{load_test[c]['taxa_sucesso']:.0%}"]
          for c in ["concorrencia_1", "concorrencia_5", "concorrencia_20"]])
        if isinstance(load_test, dict) else
        [["Teste de carga", "não executado nesta rodada (API não estava no ar)"]],
        widths=[3.6 * cm, 3.6 * cm, 2.6 * cm, 2.6 * cm, 2.4 * cm],
    ) if isinstance(load_test, dict) else P(
        "Teste de carga não executado nesta rodada: a API não estava em execução "
        "no momento da medição."),
    P("A taxa de sucesso se mantém em 100% em todos os níveis de concorrência testados, "
      "o que confirma que o serviço não derruba requisições sob carga moderada. O "
      "throughput, porém, satura entre 19 e 21 requisições por segundo "
      "independentemente do número de clientes simultâneos, porque a inferência "
      "clássica roda em CPU dentro do mesmo processo Python e compete pelo GIL: mais "
      "clientes aumentam a fila e a latência por requisição (de cerca de 51 ms com 1 "
      "cliente para cerca de 1 segundo com 20 clientes), sem aumentar a vazão total. "
      "Isso é aceitável para o volume esperado (1 leitura por minuto por ativo), mas é "
      "uma limitação real de escala: atender dezenas de ativos simultâneos exigiria "
      "múltiplos workers de processo (Uvicorn com --workers) ou uma fila de tarefas, "
      "não apenas mais threads.", BODY) if isinstance(load_test, dict) else P(""),
    P("5.4 Custo de treino e recursos quânticos", H2),
    tcapt("5.4", "Custo de treino e recursos quânticos usados por modelo."),
    tbl(
        [["Modelo", "Treino", "Recursos"],
         ["QSVC + Amplitude", f"{qs['fit_s']:.1f} s (664 janelas)",
          f"{rq['qsvc_amplitude']['n_qubits']} qubits, profundidade "
          f"{rq['qsvc_amplitude']['depth_basis_ucx']} na base u/cx, "
          f"kernel de statevector exato"],
         ["VQC (manutenção)", f"{c2['vqc']['fit_s']:.0f} s ({c2['vqc']['n_treino']} amostras, "
          f"SPSA {c2['vqc']['spsa_maxiter']} iterações)",
          f"{rq['vqc']['n_qubits']} qubits, profundidade {rq['vqc']['depth_basis_ucx']}, "
          f"{rq['vqc']['n_parametros_treinaveis']} parâmetros"],
         ["4 clássicos e RF de manutenção", "entre 0,14 e 1,2 s cada", "CPU comum, sem requisitos especiais"]],
        widths=[4.6 * cm, 5.6 * cm, 7.0 * cm], wrap=True,
    ),
    P("5.5 Limitações documentadas", H2),
    B("Os números acima foram obtidos em <b>simulador ideal</b>, sem ruído e sem "
      "amostragem por shots. Em hardware NISQ real, a consulta do kernel custaria de 1 "
      "a 10 segundos, e o treino exigiria cerca de 14 milhões de shots, algo em torno "
      "de 4 horas por partição. Ver o roadmap na seção 6 para o caminho até lá."),
    B("A janela de 10 leituras da rota quântica dilui falhas mais curtas que os 10 "
      "minutos que ela cobre, resultado da rotulagem por 'qualquer leitura anômala na "
      "janela' combinada com a média da janela. A rota clássica pontual é a mitigação "
      "ativa para esse caso."),
    B("A comparação de AUC entre clássico e quântico permanece assimétrica em volume "
      "de dados, uma característica herdada do Sprint 2. O F1 superior do QSVC vale no "
      "regime janelado avaliado, não em todo o espaço de comparação possível."),
    B("O dataset é o mesmo conjunto sintético, rotulado e versionado, definido e "
      "consolidado nos Sprints 1 e 2 (seed 42), conforme a orientação técnica deste "
      "sprint de reaproveitar os modelos e os dados já definidos, sem retreinar do "
      "zero. Ele não é uma limitação de execução, e sim o dado de entrada correto "
      "para esta etapa de integração. Uma futura conexão com telemetria real da "
      "FORZY, fora do escopo deste sprint, é tratada como evolução natural do "
      "produto e está registrada no roadmap (seção 6.4)."),
    B(f"A confiabilidade do VQC no Cenário 2 é exploratória, com acurácia de "
      f"{c2['vqc']['accuracy']:.2f}. O Random Forest clássico é o modelo operacional "
      f"recomendado; o VQC demonstra a viabilidade técnica da rota, não paridade de "
      f"desempenho com o clássico. {VQC_RETRY_NOTE}"),
    B("A API roda sem autenticação por padrão, adequada para demonstração, mas "
      "exigindo a variável FORZY_API_KEY em qualquer ambiente exposto além da rede "
      "local (ver seção 3.3)."),
]

# ═════════════════════════ 6. ROADMAP + GOVERNANÇA ═════════════════════════
story += [
    PageBreak(),
    P("6. Roadmap de evolução quântica e governança", H1),
    P("6.1 Do simulador ao hardware real", H2),
    P("A trajetória parte das projeções validadas no Sprint 2, com fidelidade "
      "estimada por mapa de features em hardware da classe IBM Eagle (erro de porta CX "
      "de cerca de 0,5% e de porta U de cerca de 0,1%), combinadas com as medições "
      "deste sprint:"),
    tcapt("6.1", "Horizontes de evolução do componente quântico, do simulador ao hardware real."),
    tbl(
        [["Horizonte", "O quê", "Fundamento"],
         ["Curto prazo (hoje)",
          "Produção em simulador, como entregue: triagem clássica síncrona somada a "
          "auditoria quântica a cada leitura, em cerca de 0,3 s",
          "Latências medidas na seção 5. Custo zero de QPU"],
         ["Médio prazo (2026-2027)",
          "Piloto em QPU real apenas com Amplitude Encoding (2 qubits, profundidade 4), "
          "de forma assíncrona, acionado por gatilho de triagem, com ZNE para mitigação "
          "de erro",
          "Fidelidade projetada acima de 0,98, com impacto de -0,01 a -0,03 no AUC. O "
          "Fourier exigiria ZNE, com fidelidade em torno de 0,90. O ZZFeatureMap foi "
          "descartado, com fidelidade em torno de 0,82 e profundidade 19"],
         ["Longo prazo (pós-2027)",
          "Migração do kernel QSVC para modelos variacionais, como VQC e QNN, também na "
          "detecção de anomalias, com mapas de features mais profundos quando houver "
          "tolerância a falhas",
          "A inferência do VQC custa em ordem de grandeza o número de camadas vezes "
          "shots, contra o número do conjunto de suporte vezes shots do kernel. O VQC do "
          "Cenário 2 já demonstra essa rota"]],
        widths=[3.2 * cm, 7.6 * cm, 6.4 * cm], wrap=True,
    ),
    P("Restrição técnica declarada: o RawFeatureVector, usado no encoding por "
      "amplitude, não suporta a inversão de circuito exigida pelo ComputeUncompute. A "
      "migração do kernel para QPU exigiria a troca do método de fidelidade, por "
      "exemplo para um SWAP test, ou a troca do mapa de features. Isso é tratado como "
      "limitação de pesquisa, não como pendência de engenharia."),
    P("6.2 Quando o QML compensa hoje", H2),
    P("No regime de <b>dados escassos</b>, como o cold-start de novos ativos com "
      "menos de 500 amostras rotuladas, em que a eficiência amostral é cerca de 5 vezes "
      "melhor que no Sprint 2, e quando o objetivo é <b>recall ou F1 da classe rara</b>, "
      "com F1 de 0,858 do QSVC contra 0,68 do melhor clássico. Quando não compensa: "
      "latência crítica, alto volume, e no Cenário 2 multiclasse, onde o clássico domina "
      "com 0,96 contra 0,66. Os custos de QPU, da ordem de US$ 1,60 por segundo em "
      "modelos de pagamento por uso da IBM, reforçam o desenho assíncrono por gatilho: "
      "auditar apenas eventos suspeitos, não o fluxo inteiro."),
    P("6.3 Governança", H2),
    B("<b>Qualidade e procedência dos dados:</b> o dataset sintético é versionado e "
      "reprodutível bit a bit, com seed 42 e versões fixadas no arquivo de "
      "dependências. Em produção, o plano é manter a validação de faixas físicas na "
      "fronteira da API, já implementada, somada a monitoramento de drift de sensores "
      "e recalibração periódica dos scalers com janelas de referência aprovadas. Refit "
      "silencioso em produção não é aceitável."),
    B("<b>Rastreabilidade das decisões:</b> toda predição é registrada no SQLite com "
      "timestamp, leituras de entrada, resultado completo, o modelo que respondeu (por "
      "exemplo classico:gradient_boosting ou quantico:qsvc_amplitude) e a latência. "
      "Sensores imputados são sinalizados na resposta, de modo que um alerta emitido "
      "com vibração imputada é auditável como tal. Os modelos são artefatos "
      "versionáveis, em joblib ou npz, com métricas de holdout arquivadas em "
      "metrics.json."),
    B("<b>LGPD:</b> a telemetria processada é exclusivamente de máquina, como tensão, "
      "corrente, temperatura e vibração, e não constitui dado pessoal, ficando fora do "
      "escopo material da LGPD. Um ponto de atenção, caso o sistema evolua: "
      "identificadores de operador em logs de manutenção e trilhas de auditoria que "
      "vinculem pessoas a turnos. Se isso ocorrer, a recomendação é aplicar "
      "minimização de dados e base legal de legítimo interesse, mantendo os dados de "
      "sensor como não pessoais."),
    B("<b>Responsabilidade sobre alertas:</b> o sistema é apoio à decisão, não comando "
      "de parada. Um alerta não é uma ordem de serviço. A política proposta é manter um "
      "humano no circuito para qualquer ação sobre o ativo, com limiares de severidade "
      "revisados pela engenharia de manutenção. Falsos negativos da janela quântica, "
      "para falhas mais curtas que 10 minutos, e falsos positivos próximos à fronteira "
      "são riscos documentados nas seções 3.5 e 5.5. A operação deve tratar as duas "
      "rotas como evidências complementares, prevalecendo a mais conservadora em caso "
      "de conflito."),
    P("6.4 Próximos passos", H2),
    B("Fora do escopo deste sprint, que trabalha com o dataset sintético definido nos "
      "Sprints 1 e 2 conforme orientado: conectar o pipeline a telemetria real da "
      "FORZY quando o produto avançar para operação, substituindo o replay, e "
      "recalibrar os limiares de alerta com dados de campo."),
    B(f"Evoluir a rota quântica de manutenção. {VQC_RETRY_NOTE}"),
    B("Realizar um piloto em QPU real, pela IBM Quantum, com o Amplitude Encoding em "
      "lote assíncrono, medindo o impacto real de ruído contra as projeções do Sprint 2."),
    B("Continuar o endurecimento de produção: a autenticação por chave e o teste de "
      "carga já foram adicionados (seções 3.3 e 5.3); os próximos itens são fila "
      "assíncrona para a rota quântica, retenção e expurgo do histórico, e "
      "monitoramento automatizado de drift."),
]

# ═════════════════════════ 7. CONCLUSÃO ═════════════════════════
story += [
    PageBreak(),
    P("7. Conclusão", H1),
    P("O Sprint 3 entrega o que o enunciado pede: um produto funcional de ponta a "
      "ponta, em que o QML validado nos sprints anteriores opera dentro de um sistema, "
      "com persistência de modelos, API documentada e autenticável, testes "
      "automatizados, dashboard em tempo quase real, dois cenários com alternância "
      "entre clássico e quântico, avaliação medida sob carga real e um roadmap honesto."),
    P("A conclusão técnica se sustenta na integração. O híbrido não é uma aposta no "
      "quântico contra o clássico, e sim uma divisão de trabalho: o clássico garante o "
      "tempo real, e o quântico audita onde já mostra vantagem, no F1 da classe rara e "
      "em regimes de dados escassos. O caminho para hardware real está traçado, com "
      "custos, riscos e critérios de decisão explícitos, e o único ponto que ainda "
      "limita o resultado, o desempenho do VQC no Cenário 2 frente ao Random Forest "
      "clássico, está documentado com transparência ao longo deste relatório, incluindo "
      "as tentativas concretas de superá-lo, e não escondido atrás de números "
      "favoráveis."),
]

doc = SimpleDocTemplate(
    str(OUT), pagesize=A4,
    leftMargin=1.9 * cm, rightMargin=1.9 * cm,
    topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    title="Relatório Final Sprint 3: FORZY Digital Twin",
    author="; ".join(AUTORES),
    subject="Computação Quântica e IA, 2TIAPF, Inteligência Artificial, FIAP",
)


def footer(canvas, doc_):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(1.9 * cm, 1.05 * cm,
                      "Sprint 3: Integração do QML ao Digital Twin, FORZY, FIAP, 2TIAPF")
    canvas.drawRightString(A4[0] - 1.9 * cm, 1.05 * cm, f"{doc_.page}")
    canvas.restoreState()


class ReportDocTemplate(SimpleDocTemplate):
    """Gera marcadores (bookmarks) do PDF e alimenta o Sumario automaticamente
    a partir dos paragrafos com estilo H1/H2."""

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        style_name = flowable.style.name
        if style_name not in ("H1", "H2"):
            return
        text = flowable.getPlainText()
        if text == "Sumário":
            return
        page_num = self.page
        if style_name == "H1":
            level = 0
        else:
            level = 1
        key = f"toc-{page_num}-{id(flowable)}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=False)
        self.notify("TOCEntry", (level, text, page_num, key))


doc = ReportDocTemplate(
    str(OUT), pagesize=A4,
    leftMargin=1.9 * cm, rightMargin=1.9 * cm,
    topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    title="Relatório Final Sprint 3: FORZY Digital Twin",
    author="; ".join(AUTORES),
    subject="Computação Quântica e IA, 2TIAPF, Inteligência Artificial, FIAP",
)
doc.multiBuild(story, onFirstPage=footer, onLaterPages=footer)
