# REGISTRO EVOLUCAO

Consolidação inicial: 03/11/2026. Revisão 1.8: 19/11/2026. Consulte o relatório para o contexto completo.

## 7. Evolução técnica e limites históricos

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

Tabela 5. Antes/depois documental, sem alterações no produto

| Antes | Depois comprovável | Evidência |
| --- | --- | --- |
| Relatório S3 e artefatos dispersos. | Relatório final, slides e README de navegação. | Seções 1-15; README e apresentação. |
| Métricas sem leitura crítica consolidada. | 424 anomalias; regra, baseline e dependência temporal conferidas. | Seções 3 e 8-11; JSONs e scripts documentais. |
| CI e persistência tratadas como garantidas. | CI sem comprovação; log best effort explicitado. | Seções 4, 7 e 12. |
| Organização apenas no pacote local. | Publicação V1.6 e acesso aos materiais conferidos. | Commit 6e67026; registro de fechamento. |
| Pitch denso e PDF visual sem texto. | V1.8: indicadores da captura transcritos para projeção, valor para a FORZY explícito e PDF pesquisável. | Slides 5, 6 e 8; roteiro revisado. |

Marcos verificáveis da publicação

03/11/2026: data de consolidação registrada na V1.6. O commit 6e67026 publicou os artefatos; sua data e fuso constam de REGISTRO_FECHAMENTO.md. O commit não data a construção das funcionalidades anteriores.

18/11/2026: conferência pública da V1.6: quatro arquivos do Drive idênticos às cópias locais por SHA-256; 58 arquivos no GitHub conferidos e 37 originais preservados. Regra e baseline reconferidas, sem executar RF/VQC ou API.

19/11/2026, V1.8: revisão de comunicação e fechamento. A nova versão deve substituir os arquivos da V1.6 no Drive. O envio no portal da disciplina e a data da banca não foram comprovados.

E11: REGISTRO_FECHAMENTO.md e conferencia_publicacao_v1_6.json. Datas de publicação e conferência são distintas das datas de desenvolvimento. Nenhuma melhoria numérica dos modelos é atribuída à sprint 4.
