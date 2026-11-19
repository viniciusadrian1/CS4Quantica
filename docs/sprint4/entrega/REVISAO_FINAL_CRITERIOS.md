# Revisão final pelos critérios da Sprint 4

**Versão documental: 1.8. Revisão: 19/11/2026. Consolidação inicial: 03/11/2026.** Repositório: [https://github.com/viniciusadrian1/CS4Quantica](https://github.com/viniciusadrian1/CS4Quantica).

## Cobertura e limites

| Critério | Peso | Evidência e resultado da revisão |
|---|---:|---|
| Evolução da Sprint 3 | 20% | Seções 7 e 7.1, slide 6 e registro de evolução. Datas individuais e CI histórica não comprovadas; 32 casos identificados estaticamente, sem nova execução. |
| Diferenciais e resultados | 25% | Valores conferidos com JSONs e CSV. Clássicos pontuais e QSVC janelado não são comparações equivalentes. Manutenção mede aproximação de rótulos sintéticos, com dependência temporal explicitada. |
| Pendências e melhorias | 20% | Seções 12 e 12.1 distinguem origem documental e propostas futuras. Avaliação cronológica e rastreabilidade precedem expansão para campo e QPU. |
| Clareza e organização | 20% | 22 páginas, sumário, referências E01-E12 e B01-B06, README, URL remota e inventários. |
| Apresentação final | 15% | 15 slides, 15 notas, 4 tabelas e 3 gráficos nativos com dados incorporados. Slide 8 separa resultados históricos e reconstruídos. |

Esta matriz não atribui nota nem substitui a avaliação do professor.

## Conferências metodológicas

- CSV: 5.200 leituras e 424 anomalias. QSVC: 558/1.039 janelas positivas (53,71%), uma população distinta das leituras pontuais (8,15%).
- RF e VQC históricos: mesmas 988 linhas de teste conforme o código, com diferentes atributos e tamanhos de treino. Resultados não reexecutados.
- Regra de manutenção: 4.935/4.940 concordâncias no total operacional (99,90%); 988/988 no teste reconstruído (100,00%, F1-macro 1,0000). As cinco divergências do total estão fora desse teste.
- Baseline normal, escolhida no treino: 674/988 acertos (68,22%), F1-macro 0,2028. Os 68,24% representam o dataset completo.
- Janelas de manutenção: 20 leituras antes do split aleatório. Todos os 988 testes intersectam o treino reconstruído; média 29,25 janelas (15-38). Cada leitura de teste participa de 3-19 janelas posteriores de treino (média 14,58).
- As contagens de sobreposição referem-se à partição completa de 3.952 registros, anterior à subamostra VQC de 400. Não quantificam inflação das métricas. Sem índices e ambiente históricos, a identidade exata com o teste antigo não é certificável.

Os scripts documentais e seus JSONs estão em `docs/sprint4/`. Ordem de execução: baseline, depois regra. Os 37 originais permanecem intactos.

## Publicação e entrega

A versão 1.6 inclui a URL do repositório na documentação, no README e no slide 15, além de disponibilizar os materiais finais em `docs/sprint4/entrega/`. O histórico desta publicação não é usado para inventar datas de implementação das sprints anteriores.

A V1.6 foi conferida sem login no Drive em 18/11/2026, com hashes iguais às cópias locais. A V1.8 deve substituir aquele pacote. Permanecem sem comprovação o envio no portal acadêmico e a data da banca.

## Validação

Conferidos: métricas e contagens, consistência entre relatório e slides, paginação, legibilidade, estrutura do PPTX, dados dos gráficos, hashes dos originais e integridade do ZIP. O PPTX não foi aberto no PowerPoint ou Google Slides. O PDF dos slides preserva a composição visual e inclui camada textual pesquisável. As capturas permanecem imagens; não se declara marcação semântica completa. O PPTX é editável.


## Revisão V1.8

Cronologia de publicação documentada sem atribuição retroativa de desenvolvimento. Motivos históricos não registrados identificados explicitamente. Captura ampliada no slide 5, ressalva metodológica destacada no slide 8 e roteiro principal reduzido a 937 palavras, com 10 minutos previstos. Detalhes adicionais ficam no apoio para perguntas. A revisão não cria evidências de CI, experimentos ou ambiente histórico ausentes.


## Refinamento final V1.8 — 19/11/2026

Indicadores da captura histórica transcritos em fonte maior no slide 5, com distinção explícita entre confiança da resposta e acurácia. Abertura e conclusão do pitch focam o valor demonstrado para a FORZY e a próxima decisão de validação. O relatório separa consulta de alertas, decisão humana e benefícios operacionais ainda não medidos. As lacunas de histórico permanecem declaradas; não houve retreino, execução de novos benchmarks ou alteração do produto.
