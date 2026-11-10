"""
Router de Feedback de Respostas do Agente.
Permite aos estudantes avaliar as mensagens e aos admins consultar estatisticas.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, record_audit_log, require_admin
from app.models.entities import Feedback, Message, User
from app.schemas.schemas import FeedbackCreate, FeedbackResponse

router = APIRouter()


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Registra avaliacao positiva/negativa ou nota sobre uma resposta."""
    if payload.message_id:
        stmt = select(Message).where(Message.id == payload.message_id)
        res = await db.execute(stmt)
        msg = res.scalar_one_or_none()
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mensagem informada para feedback nao existe.",
            )

    feedback = Feedback(
        message_id=payload.message_id,
        user_id=current_user.id,
        rating=payload.rating,
        rating_value=payload.rating_value,
        comment=payload.comment,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    await record_audit_log(
        db=db,
        action="feedback_submitted",
        resource="feedback",
        detail=f"Feedback '{payload.rating}' registrado para mensagem {payload.message_id}",
        user_id=current_user.id,
    )

    return FeedbackResponse.model_validate(feedback)


@router.get("/", response_model=List[FeedbackResponse], status_code=status.HTTP_200_OK)
async def list_feedbacks(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[FeedbackResponse]:
    """Lista todos os feedbacks registrados (exclusivo para administradores), identificando respostas que precisam de revisão."""
    stmt = select(Feedback).order_by(Feedback.created_at.desc())
    res = await db.execute(stmt)
    feedbacks = res.scalars().all()

    enriched: List[FeedbackResponse] = []
    for f in feedbacks:
        item = FeedbackResponse.model_validate(f)
        is_neg = f.rating == "negative" or (f.rating_value is not None and f.rating_value <= 2)
        item.needs_review = is_neg

        if f.message_id:
            msg_res = await db.execute(select(Message).where(Message.id == f.message_id))
            asst_msg = msg_res.scalar_one_or_none()
            if asst_msg:
                item.answer_context = asst_msg.content
                u_stmt = (
                    select(Message)
                    .where(
                        Message.conversation_id == asst_msg.conversation_id,
                        Message.role == "user",
                        Message.created_at <= asst_msg.created_at,
                    )
                    .order_by(Message.created_at.desc())
                    .limit(1)
                )
                u_res = await db.execute(u_stmt)
                u_msg = u_res.scalar_one_or_none()
                if u_msg:
                    item.question_context = u_msg.content
        enriched.append(item)

    return enriched

