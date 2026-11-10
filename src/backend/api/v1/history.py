"""
Router de Historico de Conversas e Mensagens.
Garante isolamento: estudante so acessa suas proprias conversas.
Administrador pode visualizar todas as conversas ou por usuario.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, record_audit_log
from app.models.entities import Conversation, Message, User
from app.schemas.schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)

router = APIRouter()


@router.get("/", response_model=List[ConversationResponse], status_code=status.HTTP_200_OK)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ConversationResponse]:
    """Lista as conversas do usuario autenticado (ou todas se admin)."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.updated_at.desc())
    )

    if current_user.role != "admin":
        stmt = stmt.where(Conversation.user_id == current_user.id)

    result = await db.execute(stmt)
    conversations = result.scalars().all()
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Cria uma nova conversa para o usuario autenticado."""
    conv = Conversation(
        user_id=current_user.id,
        title=payload.title or "Nova Orientacao",
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    await record_audit_log(
        db=db,
        action="conversation_created",
        resource="conversation",
        detail=f"Conversa {conv.id} criada por {current_user.email}",
        user_id=current_user.id,
    )

    # Carregar relacionamento messages vazio
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conv.id)
    )
    res = await db.execute(stmt)
    loaded_conv = res.scalar_one()

    return ConversationResponse.model_validate(loaded_conv)


@router.get("/{conversation_id}", response_model=ConversationResponse, status_code=status.HTTP_200_OK)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Retorna detalhes e mensagens de uma conversa com controle de isolamento."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa nao encontrada.",
        )

    # Verificacao de isolamento
    if current_user.role != "admin" and conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso nao autorizado a esta conversa.",
        )

    return ConversationResponse.model_validate(conv)


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    conversation_id: str,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Adiciona uma mensagem manual a uma conversa existente."""
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa nao encontrada.",
        )

    if current_user.role != "admin" and conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso nao autorizado a esta conversa.",
        )

    msg = Message(
        conversation_id=conv.id,
        role=payload.role,
        content=payload.content,
        steps=payload.steps,
        next_action=payload.next_action,
        source=payload.source,
        document_version=payload.document_version,
        evidence=payload.evidence,
        confidence=payload.confidence,
        requires_human=payload.requires_human,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    return MessageResponse.model_validate(msg)
