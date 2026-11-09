# Integração do Classificador com a Fila de Atendimento Humano

**Data:** 2026-11-08  
**Status:** Especificação técnica aprovada — implementação front/back pendente de autorização

---

## 1. Visão Geral

O classificador de assuntos sugere automaticamente uma das 8 categorias para tickets da Fila de Atendimento Humano. A categoria é exibida como **sugestão** — o orientador pode corrigi-la. As correções ficam **apenas na sessão do navegador** (React state), sem gravação no SQLite.

---

## 2. Comportamento Especificado

| Comportamento | Regra |
|---|---|
| Exibição | "Assunto sugerido pela IA: **[Categoria]** (confiança: XX%)" |
| Correção | Dropdown com 8 categorias + "Não classificado" — somente em estado React |
| Baixa confiança | Badge laranja "⚠ Revisão recomendada" quando `confiança < 40%` |
| Prioridades Alta/Média | **Não modificadas** pelo classificador |
| Escrita em SQLite | **Nunca** — correções ficam na sessão do navegador |
| Encaminhamento | Predições com `baixa_confianca=True` já sinalizam revisão humana |

---

## 3. Componentes Prontos (já implementados)

| Componente | Arquivo | Status |
|---|---|---|
| Módulo de inferência | `entrega_2_ia/inference.py` | ✅ Pronto e testado |
| Modelos treinados | `entrega_2_ia/models/asa_topic_best_v1.joblib` | ✅ Pronto |
| Metadados do modelo | `entrega_2_ia/models/metadata_v1.json` | ✅ Pronto |

---

## 4. Componentes Pendentes (requerem autorização)

### 4a. Backend — Novo arquivo `triage.py` *(não modifica existentes)*

**Arquivo a criar:** `C:\SecretaRIA\fecap-guia\backend\app\api\v1\triage.py`

```python
from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.models.entities import User
import sys, pathlib

# Adicionar entrega_2_ia ao path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "entrega_2_ia"))
from inference import classificar

router = APIRouter()

@router.post("/classify")
async def classify_subject(
    payload: dict,
    current_user: User = Depends(get_current_user)
):
    """Classifica o assunto de um texto. Não grava nada no banco."""
    texto = payload.get("text", "")
    resultado = classificar(texto)
    return resultado
```

**Arquivo existente a modificar:** `backend/app/api/router.py`  
**Modificação necessária:** adicionar `from app.api.v1.triage import router as triage_router` e `router.include_router(triage_router, prefix="/triage", tags=["triage"])`

> [!WARNING]
> **Esta modificação requer autorização específica** antes de ser executada.

### 4b. Frontend — Campo na Fila de Atendimento *(modifica App.tsx)*

**Arquivo existente a modificar:** `frontend/src/App.tsx`  
**Modificação:** adicionar campo "Assunto sugerido pela IA" no painel da Fila de Atendimento Humano (admin view), com dropdown de correção em estado React.

> [!WARNING]
> **Esta modificação requer autorização específica** antes de ser executada.

**Código proposto para o campo React:**
```tsx
// Estado local — NÃO persiste em SQLite
const [assuntoCorrigido, setAssuntoCorrigido] = useState<string | null>(null);
const [assuntoIA, setAssuntoIA] = useState<{
  categoria: string | null;
  confianca: number;
  baixa_confianca: boolean;
} | null>(null);

// Ao abrir um ticket:
useEffect(() => {
  if (ticket?.description) {
    fetch('/api/v1/triage/classify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text: ticket.description }),
    })
      .then(r => r.json())
      .then(data => setAssuntoIA(data));
  }
}, [ticket]);

// No JSX (dentro do modal/painel do ticket):
{assuntoIA && (
  <div className="ia-subject-suggestion">
    <span className="label">Assunto sugerido pela IA:</span>
    <span className="category">{assuntoCorrigido ?? assuntoIA.categoria}</span>
    <span className="confidence">({(assuntoIA.confianca * 100).toFixed(0)}%)</span>
    {assuntoIA.baixa_confianca && (
      <span className="badge badge-warning">⚠ Revisão recomendada</span>
    )}
    <select
      value={assuntoCorrigido ?? assuntoIA.categoria ?? ''}
      onChange={e => setAssuntoCorrigido(e.target.value)}
    >
      {CATEGORIAS_8.map(c => <option key={c} value={c}>{c}</option>)}
      <option value="">Não classificado</option>
    </select>
    <small>Correção salva apenas nesta sessão — não gravada no banco.</small>
  </div>
)}
```

---

## 5. Dependências para Deploy em Container

Para que o endpoint funcione dentro do container `fecap_guia_backend`, será necessário:

1. `docker cp C:\SecretaRIA\entrega_2_ia\models\ fecap_guia_backend:/app/app/ml/models/`
2. `docker cp C:\SecretaRIA\entrega_2_ia\inference.py fecap_guia_backend:/app/app/ml/`
3. Verificar se `scikit-learn` e `joblib` já estão no container (confirmado: sklearn 1.9.1, joblib 1.6.0 ✅)

> [!CAUTION]
> O `docker cp` **requer autorização específica** e não foi executado.

---

## 6. Fluxo de Dados (sem gravação em banco)

```
[Orientador abre ticket]
         ↓
[Frontend chama POST /api/v1/triage/classify]
         ↓
[Backend: inference.py → modelo joblib → retorna categoria + confiança]
         ↓
[Frontend exibe sugestão + badge de confiança]
         ↓
[Orientador pode corrigir via dropdown → estado React local]
         ↓
[Sessão encerrada → correção descartada]
         (nada é gravado no SQLite)
```
