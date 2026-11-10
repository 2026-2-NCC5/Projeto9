# Análise de Erros — Classificador de Assuntos

**Data:** 2026-11-08 13:50

## Regressao Logistica

**Erros no hold-out:** 14 de 59 (23.7%)

| Motivo | Esperado | Predito |
|---|---|---|
| Cancelamento de parcelas | Financeiro, Bolsas e Financiam | Matrícula, Rematrícula e Tranc |
| Análise de Grade (Certidão de estudos) | Documentação Acadêmica | Vida Acadêmica e Avaliações |
| Prouni: Transferência para Outra Instituição | Financeiro, Bolsas e Financiam | Matrícula, Rematrícula e Tranc |
| Entrega de Trabalho e Solicitação Diploma | Documentação Acadêmica | Estágio, Carreira e Atividades |
| Cópia de Documentos Técnico-Científicos (COMUT) | Documentação Acadêmica | Estágio, Carreira e Atividades |
| Solicitação de DP | Vida Acadêmica e Avaliações | Carteirinha e Transporte |
| Ouvinte FECAP+ | Vida Acadêmica e Avaliações | Estágio, Carreira e Atividades |
| Instituto de Finanças | NAF - Inscrição para Trabalho Volunt | Estágio, Carreira e Atividades | Financeiro, Bolsas e Financiam |
| Apoio Externo no Entorno | Atendimento Geral e Serviços d | Financeiro, Bolsas e Financiam |
| Acesso a Imagens de Câmeras de Segurança | Atendimento Geral e Serviços d | Portal e Sistemas |
| Nivelamento | Vida Acadêmica e Avaliações | Matrícula, Rematrícula e Tranc |
| PEIEX | Participação em Grupos de Estudos | Estágio, Carreira e Atividades | Atendimento Geral e Serviços d |
| Disciplinas em Inglês - Validação de Horas Complementares | Estágio, Carreira e Atividades | Vida Acadêmica e Avaliações |
| Laboratório de Métodos Quantitativos | Vida Acadêmica e Avaliações | Estágio, Carreira e Atividades |

## Arvore de Decisao

**Erros no hold-out:** 32 de 59 (54.2%)

| Motivo | Esperado | Predito |
|---|---|---|
| Restituições | Financeiro, Bolsas e Financiam | Portal e Sistemas |
| Prouni: Inscrição- 1ª e 2ª Chamadas | Financeiro, Bolsas e Financiam | Vida Acadêmica e Avaliações |
| Prouni: Solicitação de Cancelamento | Financeiro, Bolsas e Financiam | Matrícula, Rematrícula e Tranc |
| Dificuldades Acadêmicas no Moodle | Portal e Sistemas | Vida Acadêmica e Avaliações |
| Cancelamento de parcelas | Financeiro, Bolsas e Financiam | Matrícula, Rematrícula e Tranc |
| Isenção/Abono de Mensalidade | Financeiro, Bolsas e Financiam | Estágio, Carreira e Atividades |
| Diploma | Documentação Acadêmica | Estágio, Carreira e Atividades |
| Eventos - Apoio com Representante do Marketing | Atendimento Geral e Serviços d | Vida Acadêmica e Avaliações |
| Trancamento de curso - para cursar antecipação | Matrícula, Rematrícula e Tranc | Financeiro, Bolsas e Financiam |
| Solicitação de Passe Escolar EMTU | Carteirinha e Transporte | Documentação Acadêmica |
| Nota não lançada | Vida Acadêmica e Avaliações | Estágio, Carreira e Atividades |
| Eventos - Link do Evento para Inscrição | Atendimento Geral e Serviços d | Estágio, Carreira e Atividades |
| Disciplinas Isoladas (Alunos Estrangeiros) | Vida Acadêmica e Avaliações | Financeiro, Bolsas e Financiam |
| Entrega de Trabalho e Solicitação Diploma | Documentação Acadêmica | Estágio, Carreira e Atividades |
| Cópia de Documentos Técnico-Científicos (COMUT) | Documentação Acadêmica | Estágio, Carreira e Atividades |
| Solicitação de DP | Vida Acadêmica e Avaliações | Documentação Acadêmica |
| Apoio Psicológico | Atendimento Geral e Serviços d | Vida Acadêmica e Avaliações |
| Carta de quitação de débito | Financeiro, Bolsas e Financiam | Documentação Acadêmica |
| Alteração de gênero no registro de matrícula | Atendimento Geral e Serviços d | Matrícula, Rematrícula e Tranc |
| Alteração de horário de provas (oficial e exame) | Vida Acadêmica e Avaliações | Portal e Sistemas |
| Assinatura de contrato para estágio | Estágio, Carreira e Atividades | Vida Acadêmica e Avaliações |
| Instituto de Finanças | NAF - Inscrição para Trabalho Volunt | Estágio, Carreira e Atividades | Vida Acadêmica e Avaliações |
| Programa de Bolsa Restituível - Quitação Antecipada | Financeiro, Bolsas e Financiam | Estágio, Carreira e Atividades |
| Suporte para Impressão | Portal e Sistemas | Atendimento Geral e Serviços d |
| Apoio Externo no Entorno | Atendimento Geral e Serviços d | Vida Acadêmica e Avaliações |
| Limpeza de áreas comuns e salas de aula | Atendimento Geral e Serviços d | Estágio, Carreira e Atividades |
| Alteração de Vencimento das Mensalidades | Financeiro, Bolsas e Financiam | Estágio, Carreira e Atividades |
| Suporte ao uso local de computadores (Laboratórios de Inform | Portal e Sistemas | Vida Acadêmica e Avaliações |
| Acesso a Imagens de Câmeras de Segurança | Atendimento Geral e Serviços d | Documentação Acadêmica |
| Eventos - Locação de Espaço | Atendimento Geral e Serviços d | Portal e Sistemas |

*(+ 2 erros adicionais omitidos)*

## Padrões de Erro Identificados

1. **Fronteira Financeiro/Matrícula**: motivos com 'isencao' e 'trancamento' simultaneamente.
2. **Fronteira Estágio/Vida Acadêmica**: 'atividade complementar' vs 'dispensa de disciplina'.
3. **Motivos muito curtos**: nomes genéricos (<3 palavras) tendem a errar mais.
4. **Categorias com poucos exemplos** (Carteirinha, Portal): maior variância nas predições.

## Recomendações

- Revisar manualmente os motivos sinalizados com `revisar=True` no `mapeamento_motivos.csv`.
- Adicionar mais exemplos manuais para Carteirinha e Portal e Sistemas.
- Avaliar com perguntas livres dos alunos (ver `test_externo.py`).
