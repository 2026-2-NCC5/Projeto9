"""
Router de Encaminhamento para Atendimento Humano (Handoff).
Permite ao estudante gerar um protocolo quando a orientacao automatica nao for suficiente.
"""
from datetime import datetime, timezone
import random
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, record_audit_log, require_admin
from app.models.entities import Conversation, HandoffTicket, User
from app.schemas.schemas import HandoffCreate, HandoffResponse, HandoffUpdate

router = APIRouter()


def generate_protocol() -> str:
    """Gera um numero de protocolo unico e legivel."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")
    rand_suffix = f"{random.randint(1000, 9999)}"
    return f"FECAP-{date_str}-{rand_suffix}"


@router.post("/", response_model=HandoffResponse, status_code=status.HTTP_201_CREATED)
async def create_handoff(
    payload: HandoffCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HandoffResponse:
    """Cria um ticket de encaminhamento para a Secretaria Acadêmica."""
    if payload.conversation_id:
        stmt = select(Conversation).where(Conversation.id == payload.conversation_id)
        res = await db.execute(stmt)
        conv = res.scalar_one_or_none()
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversa informada para encaminhamento nao existe.",
            )
        if current_user.role != "admin" and conv.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso nao autorizado a esta conversa.",
            )

    protocol = generate_protocol()
    is_demo = settings.llm_mode.lower() == "demo"
    default_attendant = (
        "Orientador Carlos (SIMULADO — Secretaria Acadêmica ASA)"
        if is_demo
        else "Orientador Carlos — Secretaria Acadêmica ASA"
    )

    ticket = HandoffTicket(
        protocol=protocol,
        conversation_id=payload.conversation_id,
        user_id=current_user.id,
        category=payload.category,
        priority=payload.priority,
        reason=payload.reason,
        summary=payload.summary or payload.reason[:200],
        status="pending",
        attendant=default_attendant,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    await record_audit_log(
        db=db,
        action="handoff_created",
        resource="handoff",
        detail=f"Protocolo {protocol} criado na categoria {payload.category} (conv={payload.conversation_id})",
        user_id=current_user.id,
    )

    return HandoffResponse.model_validate(ticket)


@router.get("/", response_model=List[HandoffResponse], status_code=status.HTTP_200_OK)
async def list_handoffs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[HandoffResponse]:
    """Lista os tickets de encaminhamento do usuario (ou todos se admin)."""
    stmt = select(HandoffTicket).order_by(HandoffTicket.created_at.desc())
    if current_user.role != "admin":
        stmt = stmt.where(HandoffTicket.user_id == current_user.id)

    res = await db.execute(stmt)
    tickets = res.scalars().all()
    return [HandoffResponse.model_validate(t) for t in tickets]


@router.get("/{protocol}", response_model=HandoffResponse, status_code=status.HTTP_200_OK)
async def get_handoff(
    protocol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HandoffResponse:
    """Consulta os detalhes e o status de um encaminhamento pelo protocolo."""
    stmt = select(HandoffTicket).where(HandoffTicket.protocol == protocol)
    res = await db.execute(stmt)
    ticket = res.scalar_one_or_none()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encaminhamento com protocolo {protocol} nao encontrado.",
        )

    if current_user.role != "admin" and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso nao autorizado a este protocolo.",
        )

    return HandoffResponse.model_validate(ticket)


@router.patch("/{protocol}", response_model=HandoffResponse, status_code=status.HTTP_200_OK)
async def update_handoff(
    protocol: str,
    payload: HandoffUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> HandoffResponse:
    """Atualiza status, responsável (attendant) e observações (summary) de um encaminhamento (exclusivo admin)."""
    stmt = select(HandoffTicket).where(HandoffTicket.protocol == protocol)
    res = await db.execute(stmt)
    ticket = res.scalar_one_or_none()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encaminhamento com protocolo {protocol} nao encontrado.",
        )

    changes = []
    if payload.status is not None:
        valid_statuses = {"pending", "in_progress", "resolved", "transferred"}
        if payload.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status inválido. Use pending, in_progress, resolved ou transferred.",
            )
        changes.append(f"status={payload.status}")
        ticket.status = payload.status

    if payload.attendant is not None:
        changes.append(f"attendant='{payload.attendant.strip()}'")
        ticket.attendant = payload.attendant.strip()

    if payload.summary is not None:
        changes.append("observacoes atualizadas")
        ticket.summary = payload.summary.strip()

    if payload.priority is not None:
        changes.append(f"priority={payload.priority}")
        ticket.priority = payload.priority

    await db.commit()
    await db.refresh(ticket)

    await record_audit_log(
        db=db,
        action="handoff_updated",
        resource="handoff",
        detail=f"Protocolo {protocol} atualizado: {', '.join(changes) if changes else 'sem mudancas'}",
        user_id=admin.id,
    )

    return HandoffResponse.model_validate(ticket)


@router.post("/{protocol}/close", response_model=HandoffResponse, status_code=status.HTTP_200_OK)
async def close_handoff_by_student(
    protocol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HandoffResponse:
    """Permite ao proprio estudante (ou admin) encerrar o atendimento humano de seu protocolo."""
    stmt = select(HandoffTicket).where(HandoffTicket.protocol == protocol)
    res = await db.execute(stmt)
    ticket = res.scalar_one_or_none()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encaminhamento com protocolo {protocol} nao encontrado.",
        )

    if current_user.role != "admin" and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso nao autorizado para encerrar este protocolo.",
        )

    ticket.status = "resolved"
    await db.commit()
    await db.refresh(ticket)

    await record_audit_log(
        db=db,
        action="handoff_closed_by_student",
        resource="handoff",
        detail=f"Protocolo {protocol} encerrado pelo usuario (status=resolved)",
        user_id=current_user.id,
    )

    return HandoffResponse.model_validate(ticket)

