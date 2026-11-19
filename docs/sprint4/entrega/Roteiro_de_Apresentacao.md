# Roteiro de apresentação FORZY - Sprint 4

**Versão 1.7 — revisão de 18/11/2026.** Consolidação inicial: 03/11/2026.

Slides 1 a 13: **10 minutos de fala planejada**, mais até 1 minuto para transições. O tempo é uma estimativa para ensaio, não uma medição realizada. Slides 14 e 15 são de consulta. Leia somente os blocos “Fala”; fontes e apoio técnico não entram no pitch. Ajuste a duração ao tempo informado pelo professor.

| Slide | Tempo | Palavras da fala |
|---|---:|---:|
| 1 | 25 s | 40 |
| 2 | 40 s | 62 |
| 3 | 40 s | 62 |
| 4 | 50 s | 75 |
| 5 | 40 s | 61 |
| 6 | 55 s | 95 |
| 7 | 55 s | 77 |
| 8 | 90 s | 145 |
| 9 | 45 s | 70 |
| 10 | 40 s | 66 |
| 11 | 45 s | 66 |
| 12 | 45 s | 61 |
| 13 | 30 s | 51 |

## Slide 1

Tempo previsto: 25 segundos.

**Fala:** Este trabalho encerra a trilha do Challenge FORZY. A entrega reúne a solução integrada, seus resultados e as pendências. A revisão 1.7 melhora a documentação e a apresentação. Os modelos, a API e o dashboard permanecem preservados, sem novas funcionalidades.

**Fontes e apoio, sem leitura obrigatória:** Enunciado E12; relatório final, seções 1 e 14.

## Slide 2

Tempo previsto: 40 segundos.

**Fala:** O desafio é acompanhar o estado de um motor industrial. Trabalhamos com 5.200 leituras sintéticas de nove sensores. O CSV contém 424 anomalias, incluindo os registros adversariais. A manutenção classifica estados definidos por regras do dataset. Ainda não existe validação em planta nem estimativa de tempo até falha. Por isso, o resultado deve ser entendido como um protótipo integrado, com limites conhecidos.

**Fontes e apoio, sem leitura obrigatória:** E07 e E11; relatório, seções 1 e 3.

## Slide 3

Tempo previsto: 40 segundos.

**Fala:** A sprint 1 explorou a prova de conceito. A sprint 2 consolidou dados e processamento. A sprint 3 integrou modelos, API e dashboard. A sprint 4 organiza as evidências e fecha a comunicação. Parte desse histórico vem do relatório anterior: não recebemos os artefatos originais completos da sprint 1. As datas de publicação dos documentos não comprovam quando cada funcionalidade foi construída.

**Fontes e apoio, sem leitura obrigatória:** E01, E07 e E09; relatório, seção 2.

## Slide 4

Tempo previsto: 50 segundos.

**Fala:** O replay envia nove sensores à API. O serviço valida a entrada, informa imputações e mantém até vinte leituras por equipamento. A anomalia clássica usa a leitura atual; o QSVC usa dez leituras. Na manutenção, o RF recebe treze atributos e o VQC recebe quatro atributos rolantes. O serviço executa as rotas solicitadas de forma síncrona. Tenta registrar o resultado no SQLite e o devolve ao dashboard. Uma falha de gravação não bloqueia a resposta.

**Fontes e apoio, sem leitura obrigatória:** E05-E06; relatório, seções 4 e 5. Conceitos: B01-B05.

## Slide 5

Tempo previsto: 40 segundos.

**Fala:** Este recorte amplia a captura histórica da leitura 237. O painel mostra anomalia detectada e o estado de alerta, com os resultados clássico e quântico lado a lado. Essa é a evidência visual da integração. Os percentuais exibidos são confianças daquela resposta, não acurácias globais. O timestamp pertence ao replay sintético. A imagem original completa permanece no relatório e no repositório.

**Fontes e apoio, sem leitura obrigatória:** E08: sprint3/relatorio/dashboard_alerta.png; relatório, seção 6. Recorte apenas de enquadramento, sem alterar os indicadores.

## Slide 6

Tempo previsto: 55 segundos.

**Fala:** O relatório anterior descreve testes, autenticação e carga acrescentados após sua primeira entrega. O pacote contém 32 casos identificados por inspeção estática, chave opcional nos POST e resultados de carga. Não temos datas individuais que situem essas mudanças após o encerramento formal da sprint 3. O avanço comprovado da sprint 4 é documental: revisão das métricas, organização, publicação e apresentação. O commit de publicação é de 3 de novembro. Em 18 de novembro conferimos o acesso ao Drive e os hashes. A revisão 1.7 melhora o fechamento e deve substituir os arquivos anteriores no Drive.

**Fontes e apoio, sem leitura obrigatória:** E01, E03, E06 e E11; relatório, seções 7 e 7.1; REGISTRO_FECHAMENTO.md. Testes funcionais não reexecutados.

## Slide 7

Tempo previsto: 55 segundos.

**Fala:** Entre os clássicos, o MLP apresenta os melhores indicadores desta tabela. O serviço mantém Gradient Boosting por padrão, uma escolha herdada. O QSVC registra F1 de 0,8584, mas avalia janelas positivas quando qualquer leitura contém anomalia. Os clássicos avaliam leituras individuais. Essa diferença de alvo e prevalência impede concluir vantagem quântica pela comparação direta. Também há limitações do protocolo: pré-processamento clássico ajustado antes da divisão e janelas sobrepostas separadas aleatoriamente. A avaliação independente fica como próxima etapa.

**Fontes e apoio, sem leitura obrigatória:** E02, E04, E07 e E11; relatório, seção 8.

## Slide 8

Tempo previsto: 90 segundos.

**Fala:** A ressalva principal aparece no topo: estes modelos aproximam rótulos sintéticos, sem comprovar previsão de falhas. O RF histórico registra 96,26% de acurácia; o VQC, 65,59%. Entradas e quantidades de treino diferem, então a diferença não isola o efeito quântico. A regra existente coincide com 99,90% dos rótulos operacionais. No teste reconstruído, regra e baseline usam os mesmos 988 índices: a regra acerta todos, e a baseline sempre normal acerta 68,22%. Essa referência não certifica a identidade com o teste histórico dos modelos, pois faltam os índices e o ambiente original. Há ainda dependência temporal: todas as janelas do teste reconstruído compartilham leituras com a partição completa de treino. Não sabemos quanto isso influencia as métricas. O valor entregue é a integração e a exposição desses limites. A continuidade exige avaliação cronológica independente. Os detalhes da reconstrução ficam no relatório e no apoio para perguntas.

**Fontes e apoio, sem leitura obrigatória:** E02, E04-E05 e E11; relatório, seções 9 e 9.1. RF/VQC não reexecutados. Dados detalhados no apoio técnico deste roteiro.

## Slide 9

Tempo previsto: 45 segundos.

**Fala:** O ensaio HTTP mede o caminho completo da API. Com as duas rotas, o p95 ficou próximo de 719 milissegundos. Na rota clássica, o teste de carga registrou entre 19 e 21 requisições por segundo. Com vinte clientes, o p95 subiu para 1,224 segundo. O sucesso de 100% vale somente para os ensaios curtos fornecidos. O ambiente não está completamente registrado, e esses números não estabelecem um SLA de produção.

**Fontes e apoio, sem leitura obrigatória:** E03: relatorio/avaliacao_integrada.json e evaluate_integration.py; relatório, seção 10.

## Slide 10

Tempo previsto: 40 segundos.

**Fala:** O custo registrado é computacional. O ajuste do QSVC levou 4,919 segundos, sem incluir a calibração posterior. O VQC levou 187,831 segundos. Foram usados dois e quatro qubits, respectivamente, em simulação. Não há custo financeiro, energia ou execução em QPU medidos. O diferencial demonstrado é conectar os dois cenários, selecionar rotas e apresentar os resultados na interface. Ganhos de manutenção em campo ainda precisam de validação.

**Fontes e apoio, sem leitura obrigatória:** E02 e E04; relatório, seção 11.

## Slide 11

Tempo previsto: 45 segundos.

**Fala:** O projeto ainda usa telemetria sintética e simuladores. Faltam validação temporal independente, previsão de falha futura e controles para produção. A documentação separa a limitação observada do motivo histórico: em alguns casos, o motivo da postergação não foi registrado. Não atribuímos essas lacunas a orçamento ou falta de tempo sem evidência. Também continuam ausentes o workflow de CI e os logs das tentativas adicionais do VQC.

**Fontes e apoio, sem leitura obrigatória:** E01 e E04-E07; relatório, seção 12.

## Slide 12

Tempo previsto: 45 segundos.

**Fala:** A prioridade é corrigir o protocolo de avaliação e recuperar a rastreabilidade dos experimentos. Depois vêm sensores reais, timestamps e controles operacionais. A experimentação em QPU deve usar orçamento comparável, medir ruído e custo por decisão. O piloto de negócio deverá relacionar alertas a falhas e decisões reais. São propostas com critérios de aceite, sem datas ou compromissos de execução inventados.

**Fontes e apoio, sem leitura obrigatória:** Relatório, seção 12.1; PENDENCIAS_E_ROADMAP.md.

## Slide 13

Tempo previsto: 30 segundos.

**Fala:** A entrega consolida uma integração de QML simulado ao acompanhamento do motor. Os resultados são apresentados com seus limites, sem promessa de vantagem quântica ou de previsão independente de falhas. O repositório está publicado. A revisão documental 1.7 reúne relatório, slides e roteiro atualizados para substituir a versão anterior no Drive.

**Fontes e apoio, sem leitura obrigatória:** Relatório, seções 13 e 14; REGISTRO_FECHAMENTO.md.

## Slide 14

Slide de consulta, fora do tempo principal.

**Fala:** Integrantes e RMs conforme os materiais originais. Não foram atribuídas contribuições individuais sem evidência.

**Fontes e apoio, sem leitura obrigatória:** README histórico e capa do relatório S3.

## Slide 15

Slide de consulta, fora do tempo principal.

**Fala:** As métricas vêm das evidências internas E01-E12. A bibliografia fundamenta conceitos e foi consultada na revisão documental. O GitHub contém os materiais finais em docs/sprint4/entrega/. Acesso à V1.6 no Drive conferido em 18/11/2026. Esta V1.7 deve substituir os arquivos anteriores; a submissão no portal acadêmico e a data da banca dependem de confirmação do grupo.

**Fontes e apoio, sem leitura obrigatória:** Relatório, seções 13, 15 e 15.1; REGISTRO_FECHAMENTO.md.

## Apoio técnico de manutenção — somente para perguntas

O RF histórico registra 96,26% de acurácia e F1-macro 0,9279; o VQC, 65,59% e 0,5357. A diferença de 30,67 pontos percentuais não isola efeito quântico: entradas e amostras de treino diferem. Ambos usam o mesmo holdout de 988 linhas conforme o código. A ressalva central é que o alvo sintético deriva das quatro variáveis rolantes também fornecidas aos modelos. Nesta revisão, a regra reproduziu 4.935 dos 4.940 rótulos operacionais, ou 99,90%, com cinco divergências cuja causa não foi estabelecida. Os 99,90% cobrem o total operacional. Nos mesmos 988 índices salvos pela baseline reconstruída, a regra reproduziu 988 rótulos: 100,00% de concordância e F1-macro 1,0000. As cinco divergências do total ficaram fora desse recorte. A regra não teve pesos ou limiares ajustados no teste. Isso não comprova previsão de falhas independentes. Portanto, a acurácia do RF mede aproximação da regra, não previsão independente de falhas. Calculamos uma baseline constante normal, escolhida no treino: 674/988 acertos, ou 68,22%, e F1-macro 0,2028. O teste foi reconstruído do código com estratificação, 20% e seed 42; índices históricos e ambiente original não foram fornecidos, impedindo certificar a identidade exata com a execução antiga. Nessa referência, o VQC histórico fica abaixo da baseline em acurácia, mas acima em F1-macro. A proporção 68,24% se refere ao dataset completo. Há uma segunda limitação, distinta da definição sintética dos rótulos: as janelas causais de manutenção têm 20 leituras e são calculadas antes do split aleatório. Na reconstrução, 988 de 988 janelas de teste se sobrepõem ao treino, com média de 29,25 janelas e intervalo 15 a 38. Cada leitura de teste também entra em 3 a 19 janelas posteriores de treino, média 14,58. Esses números referem-se à partição completa de 3.952 linhas, antes da subamostra VQC de 400, não a uma auditoria específica dessa subamostra. Logo, o holdout não é temporalmente independente. Não sabemos quanto isso influencia a acurácia; não invalidamos numericamente os 96,26%. O próximo protocolo deve usar blocos cronológicos, treino anterior ao teste e tratar explicitamente as fronteiras das janelas. Não houve retreino nem inferência de RF/VQC. Fontes: relatório, seções 9 e 9.1; E02, E04, E05 e JSONs de conferência em E11.

## Perguntas prováveis da banca

**Houve vantagem quântica?** O pacote não permite concluir isso. O QSVC avalia janelas e os clássicos avaliam leituras. A manutenção usa entradas e amostras de treino diferentes.

**Por que manter o VQC?** Ele demonstra a integração de um classificador variacional e permite investigar seus limites; o resultado não sustenta substituir o RF.

**O sistema prevê quando o motor vai falhar?** Não. Ele classifica um estado de manutenção definido por regras no dataset sintético.

**Os 100% de sucesso garantem produção?** Não. São resultados de um ensaio curto com 40, 40 e 80 requisições, sem SLA.

**O que mudou na sprint 4?** A documentação, a conferência das evidências e a organização da entrega. Nas V1.3-V1.5, conferimos a regra, a baseline e a sobreposição temporal das janelas de manutenção na divisão reconstruída. Nenhuma funcionalidade foi desenvolvida e os modelos não foram retreinados.

**Como demonstrar sem depender da API?** Abrir as capturas e o GIF em repositorio/sprint3/relatorio/. Identificar que são registros históricos. Para demonstração ao vivo, seguir o README e verificar o ambiente antes da banca.


**Por que não houve telemetria real ou QPU?** A S3 as prevê como evolução futura; o pacote não documenta a causa original da postergação. Não é possível afirmar falta de prazo, orçamento ou acesso sem registro.

**O Drive já foi conferido?** Sim, os quatro arquivos da V1.6 foram baixados sem login em 18/11/2026 e conferidos por SHA-256. A V1.7 precisa substituir aquele pacote; o protocolo de envio à disciplina não foi fornecido.
