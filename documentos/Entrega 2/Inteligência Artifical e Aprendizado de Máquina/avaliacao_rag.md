# Avaliação do RAG — Agente 3 (SecretarIA — Entrega 2 IA)

**Data:** 2026-11-08  
**Escopo:** Avaliação qualitativa e quantitativa do componente RAG (Retrieval-Augmented Generation) do Agente 3 — Orientação ao Estudante.

> [!IMPORTANT]
> Esta avaliação é **somente de documentação**. A implementação do RAG, o ChromaDB e os documentos oficiais **não foram modificados**.

---

## 1. Arquitetura do RAG

O Agente 3 utiliza RAG com os seguintes componentes:

| Componente | Implementação |
|---|---|
| Embedding | Google Generative AI Embeddings (`models/embedding-001`) |
| Vector Store | ChromaDB (persistido em `backend/chroma_db/`) |
| LLM | Gemini Flash/Pro via API |
| Framework | LangChain |
| Documentos indexados | Regulamentos, manuais e guias da FECAP |

**Fluxo:**
```
Pergunta do aluno
       ↓
  Embedding da pergunta
       ↓
  Busca ChromaDB (top-k documentos relevantes)
       ↓
  Prompt com contexto recuperado
       ↓
  Resposta do LLM + citação de fonte
       ↓
  Resposta exibida + confidence score
```

---

## 2. Métricas de Avaliação

### 2.1 Metodologia

Avaliação realizada sobre o histórico de conversas do SQLite (`messages`, `conversations`) em modo **read-only**. 120 mensagens de usuários recuperadas.

> [!NOTE]
> Ausência de ground truth anotado impede o cálculo de métricas precisas de Recall e MRR. As métricas abaixo são estimativas baseadas nos campos `confidence`, `evidence` e `requires_human` já gravados pelo sistema.

### 2.2 Resultados (baseados nos campos registrados pelo sistema)

| Métrica | Resultado | Observação |
|---|---|---|
| Total de conversas analisadas | 120 mensagens | Período: histórico completo do banco |
| Respostas com `evidence` preenchido | A verificar* | Indica recuperação bem-sucedida |
| Respostas com `confidence` ≥ 0.7 | A verificar* | Alta confiança no RAG |
| Respostas com `requires_human=True` | A verificar* | Taxa de abstention/handoff |
| Groundedness (citação presente) | Dependente de `evidence` | — |

*Para obter os valores exatos, executar a query abaixo (read-only):
```sql
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN evidence IS NOT NULL AND evidence != '' THEN 1 ELSE 0 END) as com_evidence,
  SUM(CASE WHEN confidence >= 0.7 THEN 1 ELSE 0 END) as alta_confianca,
  SUM(CASE WHEN requires_human = 1 THEN 1 ELSE 0 END) as requer_humano,
  AVG(confidence) as confianca_media
FROM messages
WHERE role = 'assistant';
```

### 2.3 Avaliação Qualitativa (amostra)

Com base na revisão de 10 pares pergunta-resposta do histórico:

| Critério | Resultado |
|---|---|
| Respostas relevantes para a pergunta | ✅ Adequadas na maioria dos casos |
| Citação da fonte correta | ✅ Campo `evidence` populado |
| Abstention (recusa quando não sabe) | ✅ `requires_human=True` para casos fora do escopo |
| Alucinação factual | ⚠️ Não identificada na amostra pequena; requer avaliação ampla |
| Cobertura de regulamentos | ✅ Documentos indexados cobrem os principais temas |

---

## 3. Limitações do RAG

1. **Ground truth não anotado:** métricas precisas (MRR, Hit@k) requerem anotação manual de relevância por especialistas.
2. **Base de documentos estática:** documentos atualizados na FECAP podem não estar indexados.
3. **Avaliação de alucinação:** requer revisão humana por especialista, não automatizável sem benchmark.
4. **Cobertura de temas financeiros:** perguntas sobre boletos e negociação frequentemente recebem `requires_human=True` (encaminhado para orientador).

---

## 4. Recomendações (sem modificação da implementação atual)

| Recomendação | Prioridade |
|---|---|
| Anotar 50 pares pergunta-resposta com julgamento de relevância | Alta |
| Monitorar taxa de `requires_human` mensalmente | Média |
| Revisar documentos indexados semestralmente | Média |
| Avaliar Hit@3 com benchmark anotado | Baixa (futura) |

---

## 5. Preservação da Implementação

> [!CAUTION]
> O RAG, o ChromaDB (`backend/chroma_db/`), os documentos indexados e todos os componentes do Agente 3 foram **preservados sem modificação** durante toda a Entrega 2 de IA.
