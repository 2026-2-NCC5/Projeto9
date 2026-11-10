# Avaliação Externa do Classificador — Entrega 2 IA
**IMPORTANTE:** estes conjuntos NÃO foram usados no treinamento.
Perguntas sintéticas são claramente identificadas como tal.

## 1. Perguntas Sintéticas (fonte: equipe SecretarIA)
- **Total:** 96 perguntas (12 por categoria, 8 categorias)
- **Rótulos:** definidos pela equipe, revisados antes da avaliação
- **Fonte:** sintético — NÃO representam perguntas reais de alunos

| Métrica | Valor |
|---|---|
| Accuracy | 0.8438 |
| F1-macro | 0.8434 |

### Classification Report (Sintético)

```
                                               precision    recall  f1-score   support

       Atendimento Geral e Serviços do Campus       0.77      0.83      0.80        12
                     Carteirinha e Transporte       1.00      1.00      1.00        12
                       Documentação Acadêmica       0.91      0.83      0.87        12
Estágio, Carreira e Atividades Complementares       0.73      0.67      0.70        12
           Financeiro, Bolsas e Financiamento       0.75      1.00      0.86        12
         Matrícula, Rematrícula e Trancamento       1.00      0.83      0.91        12
                            Portal e Sistemas       0.82      0.75      0.78        12
                  Vida Acadêmica e Avaliações       0.83      0.83      0.83        12

                                     accuracy                           0.84        96
                                    macro avg       0.85      0.84      0.84        96
                                 weighted avg       0.85      0.84      0.84        96
```

### Erros no conjunto sintético: 15 de 96

| Pergunta | Esperado | Predito |
|---|---|---|
| Como pedir comprovante de matrícula? | Documentação Acadêmica | Atendimento Geral e Serviços d |
| Como solicitar declaração para estágio? | Documentação Acadêmica | Estágio, Carreira e Atividades |
| Perdi o prazo de matrícula, ainda consigo? | Matrícula, Rematrícula e Tranc | Atendimento Geral e Serviços d |
| Quero solicitar afastamento temporário. | Matrícula, Rematrícula e Tranc | Vida Acadêmica e Avaliações |
| Como funciona a grade curricular do meu curso? | Vida Acadêmica e Avaliações | Documentação Acadêmica |
| Quero participar das aulas concentradas. | Vida Acadêmica e Avaliações | Financeiro, Bolsas e Financiam |
| Como uso a VPN da instituição remotamente? | Portal e Sistemas | Financeiro, Bolsas e Financiam |
| O computador do laboratório não está funcionando. | Portal e Sistemas | Estágio, Carreira e Atividades |
| Como configurar o Zoom institucional? | Portal e Sistemas | Estágio, Carreira e Atividades |
| Quero submeter meu TCC para avaliação. | Estágio, Carreira e Atividades | Financeiro, Bolsas e Financiam |
| Como faço intercâmbio acadêmico? | Estágio, Carreira e Atividades | Atendimento Geral e Serviços d |
| Quero informações sobre soft skills. | Estágio, Carreira e Atividades | Portal e Sistemas |
| Como validar horas de curso externo? | Estágio, Carreira e Atividades | Vida Acadêmica e Avaliações |
| Preciso de informações sobre cursos de extensão. | Atendimento Geral e Serviços d | Portal e Sistemas |
| Minha restrição religiosa afeta provas? | Atendimento Geral e Serviços d | Financeiro, Bolsas e Financiam |

## 2. Perguntas Reais Anonimizadas (histórico SQLite)

- **Total recuperado:** 120 mensagens de usuários
- **Anonimização:** e-mails, RAs e siglas pessoais removidos
- **Rótulos:** NÃO disponíveis (ausência de ground truth rotulado)
- **Avaliação possível:** distribuição das predições (sem métricas de acurácia)

### Distribuição das Categorias Preditas (sem ground truth)

| Categoria | Predições | % |
|---|---|---|
| Documentação Acadêmica | 68 | 56.7% |
| Atendimento Geral e Serviços do Campus | 36 | 30.0% |
| Matrícula, Rematrícula e Trancamento | 12 | 10.0% |
| Financeiro, Bolsas e Financiamento | 3 | 2.5% |
| Portal e Sistemas | 1 | 0.8% |

*Predições salvas em `test_reais_predicoes.csv`.*

## 3. Limitações da Avaliação Externa

1. O modelo foi treinado em **motivos padronizados** (texto administrativo curto).
2. Perguntas livres dos alunos têm vocabulário diferente — desempenho pode ser menor.
3. Perguntas sintéticas foram criadas pela equipe e podem não refletir dúvidas reais.
4. Ausência de ground truth rotulado para perguntas reais impede cálculo de acurácia.
5. Validação humana independente ainda não realizada.
