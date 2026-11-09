# Model Card — Classificador de Assuntos (SecretarIA — Entrega 2 IA)

**Versão:** v1  
**Data:** 2026-11-08  
**Responsável:** Equipe SecretarIA — FECAP  
**Projeto:** SecretarIA — Assistente Virtual para Secretaria Acadêmica  

---

## 1. Descrição do Modelo

Modelo de classificação supervisionada que atribui automaticamente uma das **8 categorias de assunto** a textos relacionados a atendimentos da Secretaria Acadêmica da FECAP.

**Pipeline:** `TfidfVectorizer(analyzer='char_wb', ngram_range=(2,4), sublinear_tf=True)` → `LogisticRegression(C=1.0, class_weight='balanced', max_iter=2000)`

**Uso pretendido:**  
Sugerir a categoria de assunto de um ticket na **Fila de Atendimento Humano**, para apoio ao orientador. A categoria é exibida como sugestão e pode ser corrigida manualmente.

**Uso fora do escopo:**  
- Classificação definitiva sem revisão humana em casos de baixa confiança  
- Uso em dados pessoais ou sensíveis como atributo  
- Substituição do orientador em decisões acadêmicas  
- Inferência sobre textos em idiomas diferentes do português  

---

## 2. Dados de Treinamento

| Item | Valor |
|---|---|
| Fonte | `Relacionamentos.xlsx` — sistema ASA da FECAP |
| Total de registros no arquivo | 96.628 |
| Período | 2022-07-27 a 2026-08-31 |
| Alunos distintos | 10.845 |
| Motivos únicos identificados | 319 |
| **Motivos usados no treino** | **294** |
| Motivos excluídos (`__AMBIGUO__`) | 9 (Serviço Especial, Ouvidoria, Reclame Aqui…) |
| Motivos excluídos (`__NAO_ASSUNTO__`) | 3 (Não Compareceu, Cancelado, Contato não realizado) |
| Atributos do classificador | Texto do motivo (campo administrativo padronizado) |
| Atributos **não utilizados** | ID_ALUNO, datas, temas, evasão, alternativa de permanência |

> [!IMPORTANT]
> **Nenhum dado pessoal ou sensível** (RA, e-mail, nome, CPF) foi utilizado como atributo do classificador.

**Rótulos:** atribuídos por regras auditáveis (ver `rotulagem.py`). Não passaram por validação humana independente nesta versão — essa é uma limitação declarada.

**Split:** `StratifiedKFold(5)` sobre motivos únicos. O mesmo texto de motivo não aparece simultaneamente em treino e teste.

---

## 3. Categorias (8)

| Categoria | Motivos únicos | Registros no treino |
|---|---|---|
| Documentação Acadêmica | 33 | 6.850 |
| Matrícula, Rematrícula e Trancamento | 27 | 13.122 |
| Vida Acadêmica e Avaliações | 45 | 14.166 |
| Portal e Sistemas | 21 | 6.301 |
| Estágio, Carreira e Atividades Complementares | 32 | 15.694 |
| Financeiro, Bolsas e Financiamento | 76 | 12.626 |
| Carteirinha e Transporte | 13 | 10.335 |
| Atendimento Geral e Serviços do Campus | 47 | 4.121 |

---

## 4. Métricas de Avaliação

> [!NOTE]
> Métricas obtidas em **teste técnico** (hold-out e cross-validation). Não representam validação humana independente.

### Cross-Validation (5 Folds — sobre 294 motivos únicos)

| Modelo | Accuracy | F1-macro |
|---|---|---|
| **Regressão Logística** ✅ | 0.7552 ± 0.0243 | 0.7677 ± 0.0274 |
| Árvore de Decisão | 0.5104 ± 0.0319 | 0.5010 ± 0.0478 |

### Hold-out 20% (59 motivos)

| Modelo | Accuracy | Precision | Recall | F1-macro |
|---|---|---|---|---|
| **Regressão Logística** ✅ | 0.7627 | 0.7592 | 0.7867 | 0.7547 |
| Árvore de Decisão | 0.4576 | 0.5402 | 0.4930 | 0.4787 |

### Avaliação Externa — Perguntas Sintéticas (96 perguntas, 12/categoria)

| Métrica | Valor |
|---|---|
| Accuracy | 0.8438 |
| F1-macro | 0.8434 |
| Erros | 15/96 (15,6%) |

> [!WARNING]
> Perguntas **sintéticas** foram elaboradas pela equipe. NÃO representam perguntas reais de alunos.

### Avaliação Externa — Perguntas Reais (120 mensagens do histórico SQLite)

- 120 mensagens reais de usuários recuperadas (read-only, anonimizadas)
- **Ground truth não disponível** → não é possível calcular acurácia
- Distribuição das predições: Documentação Acadêmica (68), Atendimento Geral (36), Matrícula (12), Financeiro (3), Portal (1)
- **Observação:** concentração em Documentação Acadêmica pode indicar viés para textos livres curtos

---

## 5. Limitações Conhecidas

1. **Domínio fechado:** o modelo foi treinado em 294 motivos padronizados (textos administrativos curtos). Desempenho em linguagem livre de alunos é menor — confiança frequentemente abaixo de 0,40.
2. **Sem validação humana independente dos rótulos:** categorias atribuídas por regras automáticas auditáveis, não por especialistas.
3. **Categorias com poucos exemplos:** Carteirinha e Transporte (13 motivos) e Portal e Sistemas (21) têm menor representatividade.
4. **Fronteiras ambíguas:** Estágio/Vida Acadêmica e Financeiro/Matrícula são fontes frequentes de erro.
5. **Desvio temporal:** a base cobre 2022-2026; motivos novos introduzidos após o treino não serão bem classificados.
6. **Sem retreino automático:** o modelo é estático; requer retreino manual para incorporar novos motivos.

---

## 6. Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| Classificação incorreta prejudica aluno | Sugestão apenas — orientador decide |
| Baixa confiança aceita sem revisão | Interface sinaliza `baixa_confiança` quando prob < 40% |
| Dados pessoais vazam para o modelo | Atributos restringidos a textos administrativos padronizados |
| Correção do orientador gravada sem consentimento | Correções ficam **somente na sessão** (React state), sem escrita em SQLite |

---

## 7. Arquivos do Modelo

| Arquivo | Descrição |
|---|---|
| `models/asa_topic_best_v1.joblib` | Pipeline completo (TF-IDF + LR), treinado em todos os 294 motivos |
| `models/asa_topic_lr_v1.joblib` | Pipeline LR treinado no split 80% |
| `models/asa_topic_dt_v1.joblib` | Pipeline DT treinado no split 80% |
| `models/metadata_v1.json` | Metadados, métricas e hash dos dados de treino |
| `rotulagem.py` | Regras de rotulagem auditáveis |
| `mapeamento_motivos.csv` | 319 motivos com categoria e regra aplicada |
| `inference.py` | Módulo de inferência para integração |

---

## 8. Referências

- Base de dados: Sistema ASA — FECAP (uso interno, dados anonimizados)
- Scikit-learn 1.9.1 — [scikit-learn.org](https://scikit-learn.org)
- Projeto SecretarIA — FECAP, 2026
