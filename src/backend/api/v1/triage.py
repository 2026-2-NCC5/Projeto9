"""
Router de Triagem de Assunto — Entrega 2 IA.

Endpoint: POST /api/v1/triage/classify
  - Requer autenticação JWT válida (qualquer perfil)
  - Classifica o texto em uma das 8 categorias usando o modelo treinado
  - NÃO grava nada no SQLite
  - NÃO altera prioridades, status ou encaminhamentos
  - Retorna a categoria sugerida, confiança e top-3 para o frontend

Fallback: se o modelo não carregar (arquivo ausente ou erro de importação),
retorna HTTP 503 sem bloquear o restante da aplicação.
"""

import pathlib
import sys
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.deps import get_current_user
from app.models.entities import User

logger = logging.getLogger(__name__)

router = APIRouter()

# ------------------------------------------------------------------ #
# Carregamento lazy do modelo (evita falha na inicialização da API)   #
# ------------------------------------------------------------------ #
_MODEL_DIR = pathlib.Path("/app/entrega_2_ia/models")
_HOST_MODEL_DIR = pathlib.Path(__file__).parent.parent.parent.parent.parent.parent / "entrega_2_ia" / "models"

_pipe = None
_meta = None
_load_error: str | None = None


def _lazy_load():
    global _pipe, _meta, _load_error
    if _pipe is not None or _load_error is not None:
        return

    # Detectar se estamos no container ou no host
    model_dir = _MODEL_DIR if _MODEL_DIR.exists() else _HOST_MODEL_DIR
    model_path = model_dir / "asa_topic_best_v1.joblib"
    meta_path = model_dir / "metadata_v1.json"

    if not model_path.exists():
        _load_error = f"Modelo não encontrado em {model_path}"
        logger.warning(_load_error)
        return

    try:
        import joblib, json
        _pipe = joblib.load(model_path)
        _meta = json.loads(meta_path.read_text(encoding="utf-8"))
        logger.info(f"Modelo carregado: {model_path} (versão {_meta.get('versao', '?')})")
    except Exception as e:
        _load_error = str(e)
        logger.error(f"Erro ao carregar modelo de triagem: {e}")


# ------------------------------------------------------------------ #
# Schema de entrada                                                    #
# ------------------------------------------------------------------ #
class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000,
                      description="Texto da pergunta ou motivo a classificar")


# ------------------------------------------------------------------ #
# Endpoint                                                             #
# ------------------------------------------------------------------ #
@router.post("/classify", status_code=status.HTTP_200_OK)
async def classify_subject(
    payload: ClassifyRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Classifica o assunto de um texto em uma das 8 categorias do SecretarIA.

    - Requer autenticação JWT.
    - NÃO grava no banco de dados.
    - NÃO altera prioridades, status ou encaminhamentos.
    - Em caso de baixa confiança (< 40%), retorna baixa_confianca=true
      para sinalizar revisão humana.
    """
    _lazy_load()

    if _load_error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Classificador de assuntos indisponível: {_load_error}",
        )

    texto = payload.text.strip()
    if not texto:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Texto não pode ser vazio.",
        )

    try:
        probs = _pipe.predict_proba([texto])[0]
        classes = _pipe.classes_
        top_idx = probs.argsort()[::-1]

        categoria = str(classes[top_idx[0]])
        confianca = float(probs[top_idx[0]])
        top3 = [
            {"categoria": str(classes[i]), "prob": round(float(probs[i]), 4)}
            for i in top_idx[:3]
        ]

        return {
            "categoria": categoria,
            "confianca": round(confianca, 4),
            "top3": top3,
            "baixa_confianca": confianca < 0.40,
            "modelo": _meta.get("melhor_modelo", "Regressao Logistica") if _meta else "v1",
            "versao": _meta.get("versao", "v1") if _meta else "v1",
        }
    except Exception as e:
        logger.error(f"Erro na inferência de assunto: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na classificação: {str(e)}",
        )
