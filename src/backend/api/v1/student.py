"""
Router de perfil do estudante.
Permite ao estudante autenticado consultar e atualizar seu proprio perfil.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.entities import Student, User
from app.schemas.schemas import StudentResponse

router = APIRouter()


@router.get("/profile", response_model=StudentResponse, status_code=status.HTTP_200_OK)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentResponse:
    """Retorna o perfil do estudante vinculado ao usuario logado."""
    stmt = select(Student).where(Student.user_id == current_user.id)
    result = await db.execute(stmt)
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de estudante nao encontrado para o usuario autenticado.",
        )

    return StudentResponse.model_validate(student)
