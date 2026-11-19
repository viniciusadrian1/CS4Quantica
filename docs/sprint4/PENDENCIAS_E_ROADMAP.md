# PENDENCIAS E ROADMAP

Consolidação inicial: 03/11/2026. Revisão 1.8: 19/11/2026. Consulte o relatório para o contexto completo.

## 12. Pendências e justificativas

Origem do registro: H = pendência herdada ou já prevista na S3; C = lacuna explicitada na conferência S4. A marca indica a origem documental, não a data de implementação. As melhorias futuras estão separadas na seção 12.1.

Tabela 14. Lacunas do escopo entregue

| Pendência | Motivo ou limite comprovável | Consequência |
| --- | --- | --- |
| [H] Telemetria real e integração de planta | A S3 prevê conexão futura. A causa original da postergação não foi registrada; não se infere falta de tempo ou acesso. | Generalização e ganho operacional não comprovados. |
| [H] Hardware quântico real | Entregues somente simuladores, sem jobs de QPU. Não há registro que atribua a decisão a custo, hardware ou prazo. | Ruído e latência de hardware desconhecidos. |
| [C] Validação temporal independente | Anomalia: pré-processamento global e janelas QSVC. Manutenção: janelas de 20 leituras antes do split; 988/988 testes sobrepostos ao treino reconstruído. | Holdout pode superestimar generalização. |
| [C] Previsão de falha futura | A regra recomposta reproduz 99,90% dos rótulos operacionais; o alvo é uma classe de estado. | Não se estima RUL ou horizonte até falha. |
| [H] VQC competitivo | A configuração persistida tem F1-macro 0,5357; alternativas relatadas não melhoraram. | Uso exploratório, sem fundamento para substituir o RF. |
| [H/C] Operação em produção | Chave opcional nos POST, buffer em memória e log best effort. | Autorização, continuidade e durabilidade incompletas. |
| [C] CI e experimentos auditáveis | Workflow, logs de CI e resultados brutos das tentativas VQC ausentes. | Não é possível certificar execução nem datas. |
| [C] Atualização e submissão acadêmica | V1.6 acessível no Drive em 18/11. V1.8 deve substituí-la. Envio no portal e data da banca não comprovados. | Substituir os arquivos e confirmar o protocolo acadêmico. |

A ausência de um artefato não demonstra que ele nunca existiu. A tabela distingue previsão de escopo, limitação observada e causa histórica não documentada. Para recuperar o motivo original, seria necessário registro da decisão ou confirmação dos responsáveis. Não se atribuem atrasos a tempo, orçamento ou hardware por inferência.

A sprint 4 registra essas pendências; resolvê-las tecnicamente exigiria novos desenvolvimentos ou experimentos, fora do escopo solicitado.

## 12.1. Melhorias futuras e critérios de aceite

Tabela 15. Roadmap proposto, sem compromisso de data

| Prioridade / frente | Ação futura | Critério de aceite proposto |
| --- | --- | --- |
| P0 / avaliação | Dividir cronologicamente por blocos e ativo; treino anterior ao teste. Tratar fronteiras das janelas QSVC (10) e manutenção (20); ajustar transformadores só no treino. | Holdout intocado, sem leituras brutas compartilhadas entre partições; protocolo comum, métricas por classe e incerteza. |
| P0 / auditabilidade | Recuperar workflow, logs, versões do ambiente, data dos benchmarks e histórico dos experimentos. | Cada indicador vinculado a execução, configuração e artefato verificáveis. |
| P1 / campo | Integrar sensores reais, conservar timestamps e validar missing data e cadência. | Piloto com eventos de manutenção confirmados e avaliação por equipamento. |
| P1 / operação | Proteger leituras e escritas, gerir segredos, monitorar falhas de log e persistir estado quando necessário. | Testes de acesso, reinício, recuperação de histórico e retenção acordada. |
| P1 / escala | Avaliar fila quântica e workers com estratégia consistente para o buffer por ativo. | p95, taxa de erro e throughput atendem à carga e ao SLA definidos com a FORZY. |
| P2 / QML | Testar VQC sob orçamento comparável e realizar piloto pequeno em QPU. | Comparação com baselines, múltiplas seeds, custo por decisão e ruído medidos. |
| P2 / negócio | Relacionar alertas a falhas futuras e decisões reais de manutenção. | Medir antecedência útil, falsos alarmes, falhas não detectadas e efeito operacional. |

A sequência proposta prioriza validade da avaliação e rastreabilidade antes de ampliar a complexidade. Hardware quântico real faz sentido como experimento controlado, condicionado a um problema e um orçamento de comparação claros.

Responsabilidades sugeridas: modelagem e dados para avaliação; integração para campo e operação; equipe do projeto para evidências e publicação. São papéis propostos, sem designação nominal ou compromisso de execução.
