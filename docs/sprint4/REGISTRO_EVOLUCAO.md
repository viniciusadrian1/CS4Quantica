# REGISTRO EVOLUCAO

Consolidação em 03/11/2026. Consulte o relatório para o contexto completo.

## 7. Evolução após a primeira entrega

O relatório S3 descreve avanços posteriores à sua primeira entrega. O quadro separa esse relato daquilo que o pacote permite inspecionar. Não há evidência suficiente para afirmar que todos ocorreram depois do encerramento formal da sprint 3. [E01]

Tabela 4. Registro antes/depois com nível de comprovação

| Frente | Antes relatado / depois disponível | Data e evidência |
| --- | --- | --- |
| Testes | Antes: smoke test. Depois: suíte de inferência e API, 32 casos por contagem estática incluindo parametrização. | Após a primeira entrega, sem data individual. Arquivos presentes em E06; execução não refeita. |
| Autenticação | Antes: API sem mecanismo de chave segundo o relato. Depois: proteção opcional dos endpoints POST. | Após a primeira entrega, sem data individual. require_api_key e testes em E06. |
| Carga concorrente | Antes: avaliação limitada segundo o relato. Depois: ensaios de 1, 5 e 20 clientes. | Após a primeira entrega, sem data individual. Script e JSON E03. |
| VQC | Depois: três estratégias adicionais de treino relatadas; configuração original mantida. | Após a primeira entrega, sem data individual. Apenas relato em E01, pp. 7 e 15. |
| Integração contínua | Depois alegado: workflow do GitHub Actions. Arquivo e logs não estão no pacote. | Não verificável. README e E01 citam .github/workflows/tests.yml. |

Conclusão sobre o avanço técnico

Testes, autenticação e avaliação de carga estão representados por código ou resultados persistidos. Os experimentos adicionais do VQC têm evidência documental secundária. O funcionamento da CI e o instante de cada mudança permanecem pendentes de comprovação. Não se atribuem melhorias numéricas de desempenho à sprint 4.

## 7.1. Evolução documental na sprint 4

Tabela 5. Consolidação executada em 03/11/2026

| Antes | Depois | Evidência nesta entrega |
| --- | --- | --- |
| Relatório centrado na sprint 3. | Narrativa final com contexto, jornada, resultados, pendências e conclusão. | Documentacao_Final_FORZY_Sprint4.pdf e fonte Markdown. |
| Métricas distribuídas em JSONs e narrativa. | Tabelas com unidades, amostras e distinção entre lote, serviço e HTTP. | Seções 8 a 11 e metricas_consolidadas.csv. |
| 430 anomalias citadas no relatório. | 424 anomalias confirmadas no CSV entregue. | conferencia_dataset.json e seção 3. |
| Regra de manutenção sem conferência quantitativa e baseline ausente. | V1.5: regra e baseline conferidas; 988/988 janelas de manutenção no teste se sobrepõem ao treino reconstruído. | Seção 9.1; JSONs e scripts documentais em docs/sprint4/. |
| Afirmações de CI e persistência integral. | CI não comprovada; registro best effort explicitado. | Seções 4, 7 e 12. |
| Arquivo compactado sem guia de entrega final. | README de navegação, inventário de fontes e roteiro de apresentação. | repositorio/README.md, docs/sprint4/ e LEIA-ME_ENTREGA.md. |
| Apresentação final ausente no pacote. | Slides e roteiro com a mesma base factual do relatório. | Apresentacao_Final_FORZY_Sprint4.pptx e PDF. |

Esses avanços tornam o trabalho legível e verificável, sem alterar o produto. A conferência incluiu leitura, contagem, revisão do código e, nas V1.3-V1.5, conferência da regra, baseline e sobreposição temporal nos índices reconstruídos. Os resultados de RF/VQC, testes funcionais e benchmark continuam sendo históricos.

O que não se pode preencher por inferência

O pacote histórico não contém datas individuais de desenvolvimento, logs das tentativas adicionais do VQC nem histórico Git. A publicação atual organiza os artefatos, mas não recupera essas evidências antigas. O repositório do projeto está indicado na seção 13; a data da banca ainda deve ser confirmada.
