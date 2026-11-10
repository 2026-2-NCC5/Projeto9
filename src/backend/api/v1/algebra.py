"""
Router de Álgebra Linear — Entrega 2.
Fornece endpoint autenticado para o experimento didático de Transformação Linear.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.deps import get_current_user
from app.models.entities import User
from app.services.linear_algebra_service import apply_linear_transformation

router = APIRouter()

class TransformWeightsRequest(BaseModel):
    w_portal: float = Field(default=1.0, ge=0.01, le=10.0, description="Peso do Eixo 1 (Sistemas/Portal)")
    w_documentos: float = Field(default=1.0, ge=0.01, le=10.0, description="Peso do Eixo 2 (Documentos/Secretaria)")
    w_canais: float = Field(default=1.0, ge=0.01, le=10.0, description="Peso do Eixo 3 (Canais/Setores)")

@router.post("/transform", status_code=status.HTTP_200_OK)
async def calculate_linear_transformation(
    payload: TransformWeightsRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Calcula a transformação linear A * v sobre a pergunta e artigos didáticos da Entrega 1.
    Exige autenticação JWT válida para qualquer estudante ou administrador.
    """
    try:
        result = apply_linear_transformation(
            w_portal=payload.w_portal,
            w_documentos=payload.w_documentos,
            w_canais=payload.w_canais,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no cálculo de álgebra linear: {str(e)}",
        )
