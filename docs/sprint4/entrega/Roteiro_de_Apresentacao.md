# Roteiro de apresentação FORZY - Sprint 4

Duração sugerida: aproximadamente 9 a 10 minutos para os slides 1 a 13. Slides 14 e 15: créditos e consulta. Os tempos são sugestões de ensaio.

## Slide 1

Abertura, 25 segundos. Este trabalho fecha a trilha do Challenge FORZY. Consolidamos a solução de QML integrada ao Digital Twin, seus resultados e o que ainda precisa de validação. Nesta sprint, o escopo foi documental, sem alterar os modelos ou desenvolver funcionalidades. A base é o pacote da sprint 3 recebido do grupo. Referências: enunciado E12 e relatório S3 E01.

## Slide 2

Contexto, 40 segundos. O desafio é apoiar a leitura do estado de um motor industrial. O dataset recebido tem 5.200 registros e nove sensores. Contamos diretamente 424 anomalias, incluindo os 120 registros adversariais. O relatório antigo citava 430; mantivemos a contagem verificável e registramos a divergência. A manutenção usa classes de estado geradas por regras sintéticas. Portanto, o projeto ainda não comprova antecedência de falhas nem redução de paradas reais. Fontes: sprint3/sprint2_core/dataset_motor_sprint2_bruto.csv, docs/sprint4/conferencia_dataset.json e common.py.

## Slide 3

Jornada, 40 segundos. A primeira sprint investigou a viabilidade do QML. A segunda consolidou os dados e o pipeline de processamento. A terceira integrou os modelos à API, ao histórico e ao dashboard. A quarta torna esse conjunto navegável e explica seu alcance. O pacote contém diretamente parte dos artefatos da sprint 2 e os materiais da sprint 3. A reconstrução da sprint 1 depende do relato anterior. Não temos uma série completa de experimentos para calcular uma melhoria numérica entre todas as etapas. Fontes: E01, E07 e E09.

## Slide 4

Arquitetura, 50 segundos. O replay fornece os sensores. A API valida a entrada e completa os opcionais ausentes. O serviço mantém um buffer por equipamento com até vinte leituras. A anomalia clássica usa a leitura atual e o QSVC usa dez leituras. Na manutenção, o RF usa nove sensores e quatro atributos rolantes; o VQC usa os quatro atributos rolantes. A implementação executa as rotas solicitadas de forma síncrona. A auditoria assíncrona é uma proposta futura. O SQLite fornece histórico, mas uma falha de gravação não impede o retorno da predição. Fontes: sprint3/inference.py, common.py e api.py. Fundamentação conceitual consultada na revisão: B01-B04 para QML e B05 para Digital Twin; links completos no slide 15 e no relatório.

## Slide 5

Demonstração, 40 segundos. A captura preservada mostra API online, nove sensores e as duas rotas no mesmo painel. O estado do ativo aparece como alerta. Esse é o principal resultado de integração: a decisão dos modelos chega à interface do Digital Twin. Os percentuais na tela são confianças de uma resposta específica. Não os tratamos como indicadores de acurácia global. A captura é histórica, reaproveitada para esta documentação, e o timestamp é do dataset. Fonte: sprint3/relatorio/dashboard_alerta.png. A captura de parada e o GIF também acompanham o repositório.

## Slide 6

Evolução, 50 segundos. O relatório anterior descreve melhorias após sua primeira entrega. Hoje vemos os testes, o mecanismo de chave e a avaliação de carga no pacote. A suíte representa 32 casos por contagem estática, incluindo parametrização; não a executamos nesta consolidação. Já a CI está apenas citada: o workflow e os logs não foram fornecidos. As tentativas adicionais do VQC também aparecem apenas no relato. Na sprint 4, avançamos na organização e na interpretação da evidência. Isso evita inventar mudanças ou datas que o material não comprova. Fontes: E01, E03, E06 e registro de evolução.

## Slide 7

Anomalia, 55 segundos. Entre os clássicos, o MLP lidera os três indicadores apresentados. O serviço usa Gradient Boosting por padrão, uma escolha herdada. O QSVC tem F1 de 0,8584 no problema janelado, mas sua janela é positiva se qualquer uma das dez leituras tiver anomalia. No conjunto completo, as janelas têm 558 positivos em 1.039, ou 53,71%, enquanto as leituras pontuais têm 8,15%. Isso muda a unidade de avaliação e a proporção de positivos. Por isso, não declaramos superioridade quântica comparando diretamente esses F1. Além disso, o pré-processamento clássico foi ajustado antes do split e as janelas sobrepostas foram separadas aleatoriamente. Esses limites precisam ser resolvidos em uma avaliação futura. Fonte: models/metrics.json, train_and_persist.py e inference.py.

## Slide 8

Manutenção, 90 segundos. O RF histórico registra 96,26% de acurácia e F1-macro 0,9279; o VQC, 65,59% e 0,5357. A diferença de 30,67 pontos percentuais não isola efeito quântico: entradas e amostras de treino diferem. Ambos usam o mesmo holdout de 988 linhas conforme o código. A ressalva central é que o alvo sintético deriva das quatro variáveis rolantes também fornecidas aos modelos. Nesta revisão, a regra reproduziu 4.935 dos 4.940 rótulos operacionais, ou 99,90%, com cinco divergências cuja causa não foi estabelecida. Os 99,90% cobrem o total operacional. Nos mesmos 988 índices salvos pela baseline reconstruída, a regra reproduziu 988 rótulos: 100,00% de concordância e F1-macro 1,0000. As cinco divergências do total ficaram fora desse recorte. A regra não teve pesos ou limiares ajustados no teste. Isso não comprova previsão de falhas independentes. Portanto, a acurácia do RF mede aproximação da regra, não previsão independente de falhas. Calculamos uma baseline constante normal, escolhida no treino: 674/988 acertos, ou 68,22%, e F1-macro 0,2028. O teste foi reconstruído do código com estratificação, 20% e seed 42; índices históricos e ambiente original não foram fornecidos, impedindo certificar a identidade exata com a execução antiga. Nessa referência, o VQC histórico fica abaixo da baseline em acurácia, mas acima em F1-macro. A proporção 68,24% se refere ao dataset completo. Há uma segunda limitação, distinta da definição sintética dos rótulos: as janelas causais de manutenção têm 20 leituras e são calculadas antes do split aleatório. Na reconstrução, 988 de 988 janelas de teste se sobrepõem ao treino, com média de 29,25 janelas e intervalo 15 a 38. Cada leitura de teste também entra em 3 a 19 janelas posteriores de treino, média 14,58. Esses números referem-se à partição completa de 3.952 linhas, antes da subamostra VQC de 400, não a uma auditoria específica dessa subamostra. Logo, o holdout não é temporalmente independente. Não sabemos quanto isso influencia a acurácia; não invalidamos numericamente os 96,26%. O próximo protocolo deve usar blocos cronológicos, treino anterior ao teste e tratar explicitamente as fronteiras das janelas. Não houve retreino nem inferência de RF/VQC. Fontes: relatório, seções 9 e 9.1; E02, E04, E05 e JSONs de conferência em E11.

## Slide 9

Latência, 45 segundos. A medição HTTP inclui o caminho completo da API, diferentemente dos tempos de predição em lote. Com ambas as rotas, o p95 foi de aproximadamente 719 milissegundos. O teste de carga da rota clássica ficou entre 19 e 21 requisições por segundo. O sucesso foi de 100% nesse ensaio, mas a latência aumentou com a concorrência, chegando a p95 de 1,224 segundo com vinte clientes. Esses são ensaios curtos, sem registro completo do ambiente. Não estabelecem um SLA nem comprovam comportamento em produção. Fonte: relatorio/avaliacao_integrada.json e evaluate_integration.py.

## Slide 10

Custo e diferenciais, 45 segundos. O QSVC usa dois qubits e o VQC usa quatro. Seus tempos históricos de ajuste são 4,919 e 187,831 segundos. O fit do QSVC não inclui a calibração posterior. Não há medida de custo financeiro, energia ou memória máxima, nem execução em QPU. O valor comprovado está no fluxo integrado, na possibilidade de comparar as rotas e na exposição dos resultados. Benefícios como redução de downtime ou economia de manutenção continuam como hipóteses para um piloto real. Fonte: metrics.json e train_and_persist.py.

## Slide 11

Limites, 45 segundos. A transparência é parte central do fechamento. Os dados não vêm de uma planta em operação. O alvo de manutenção não mede tempo até falha. A avaliação atual tem limitações de independência. Na operação, o buffer é local ao processo e o log pode falhar sem bloquear a resposta. A autenticação é opcional nos endpoints de escrita e não protege os endpoints de leitura. Também faltam evidências de CI e dos experimentos adicionais. Essas limitações estão documentadas, junto com seu efeito e o que seria necessário para avançar. Fontes: E01 e E04-E07.

## Slide 12

Roadmap, 45 segundos. Primeiro, propomos corrigir o protocolo de avaliação e recuperar a rastreabilidade dos experimentos. Depois, conectar telemetria real e definir os controles operacionais. Só então faz sentido ampliar o experimento quântico e medir impacto no negócio. Cada frente tem um critério de aceite no relatório. Por exemplo, o piloto exige eventos de manutenção confirmados e avaliação por ativo, e a QPU exige custo por decisão e ruído medidos. São propostas, não entregas já concluídas ou compromissos de calendário. Fonte: seção 12.1 do relatório final.

## Slide 13

Fechamento, 30 segundos. A conclusão se sustenta na integração construída. O clássico apresenta resultados mais fortes na manutenção, e o QML está disponível como componente experimental integrado. A sprint 4 reúne o que foi feito, explicita o que os números permitem concluir e prepara uma continuidade responsável. Entregamos o relatório, os slides, o roteiro e o repositório organizado localmente. A validação de campo e a investigação quântica permanecem como próximos passos.

## Slide 14

Créditos. Integrantes transcritos do README e da capa do relatório original. Não foram atribuídas funções individuais ou contribuições sem evidência.

## Slide 15

Os números são evidências internas E01-E12. A bibliografia foi consultada nesta revisão para fundamentação conceitual, sem alegação de uso nas sprints anteriores. As páginas atuais da API não comprovam a versão do benchmark. Repositório do projeto: https://github.com/viniciusadrian1/CS4Quantica. Materiais finais: docs/sprint4/entrega/. O grupo deve concluir o envio ao Drive e conferir o acesso da banca.

B01 HAVLÍČEK, V. et al. Supervised learning with quantum-enhanced feature spaces. Nature, v. 567, p. 209-212, 2019. DOI: 10.1038/s41586-019-0980-2. https://doi.org/10.1038/s41586-019-0980-2

B02 SAHIN, M. E. et al. Qiskit Machine Learning: an open-source library for quantum machine learning tasks at scale on quantum hardware and classical simulators. arXiv:2505.17756, 2025. https://arxiv.org/abs/2505.17756

B03 QISKIT COMMUNITY. QSVC. Qiskit Machine Learning 0.9.1, documentação da API. https://qiskit-community.github.io/qiskit-machine-learning/stubs/qiskit_machine_learning.algorithms.QSVC.html

B04 QISKIT COMMUNITY. VQC. Qiskit Machine Learning 0.9.1, documentação da API. https://qiskit-community.github.io/qiskit-machine-learning/stubs/qiskit_machine_learning.algorithms.VQC.html

B05 SHAO, G. Use Case Scenarios for Digital Twin Implementation Based on ISO 23247. NIST Advanced Manufacturing Series 400-2, 2021. DOI: 10.6028/NIST.AMS.400-2. https://nvlpubs.nist.gov/nistpubs/ams/NIST.AMS.400-2.pdf

B06 MILLER, K.; DUBRAWSKI, A. System-Level Predictive Maintenance: Review of Research Literature and Gap Analysis. arXiv:2005.05239, 2020. https://arxiv.org/abs/2005.05239

## Perguntas prováveis da banca

**Houve vantagem quântica?** O pacote não permite concluir isso. O QSVC avalia janelas e os clássicos avaliam leituras. A manutenção usa entradas e amostras de treino diferentes.

**Por que manter o VQC?** Ele demonstra a integração de um classificador variacional e permite investigar seus limites; o resultado não sustenta substituir o RF.

**O sistema prevê quando o motor vai falhar?** Não. Ele classifica um estado de manutenção definido por regras no dataset sintético.

**Os 100% de sucesso garantem produção?** Não. São resultados de um ensaio curto com 40, 40 e 80 requisições, sem SLA.

**O que mudou na sprint 4?** A documentação, a conferência das evidências e a organização da entrega. Nas V1.3-V1.5, conferimos a regra, a baseline e a sobreposição temporal das janelas de manutenção na divisão reconstruída. Nenhuma funcionalidade foi desenvolvida e os modelos não foram retreinados.

**Como demonstrar sem depender da API?** Abrir as capturas e o GIF em repositorio/sprint3/relatorio/. Identificar que são registros históricos. Para demonstração ao vivo, seguir o README e verificar o ambiente antes da banca.
