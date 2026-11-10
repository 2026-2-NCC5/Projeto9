"""
Router do Agente RAG — Orientacao ao Estudante.
Integra execucao do pipeline RAG e persistencia opcional em conversa/mensagens no SQLite.
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.rag_pipeline import RAGPipeline
from app.core.database import get_db
from app.core.deps import get_optional_current_user, record_audit_log
from app.models.entities import Conversation, Message, User
from app.schemas.schemas import AgentQuery, AgentResponse

router = APIRouter()

_pipeline = RAGPipeline()


def get_rag_pipeline() -> RAGPipeline:
    return _pipeline


@router.get("/", status_code=status.HTTP_200_OK)
async def get_agent_status():
    return {
        "status": "online",
        "agent": "Orientacao ao Estudante",
        "fase": "FASE 4 — Autenticacao e APIs Reais",
    }


@router.post("/query", response_model=AgentResponse, status_code=status.HTTP_200_OK)
async def query_agent(
    query: AgentQuery,
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """
    Recebe pergunta do estudante, executa o pipeline RAG no ChromaDB e
    retorna a orientacao fundamentada em evidencias com passos e grau de confianca.
    Se autenticado, persiste o turno (pergunta e resposta) no historico.
    """
    # Executa operacoes sincronas/CPU-bound em thread separada
    loop = asyncio.get_running_loop()
    response: AgentResponse = await loop.run_in_executor(None, pipeline.run, query)

    # Persistencia de conversa caso o usuario esteja autenticado ou forneca conversation_id
    conversation_id = query.conversation_id
    if current_user:
        try:
            conv = None
            if conversation_id:
                stmt = select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id,
                )
                res = await db.execute(stmt)
                conv = res.scalar_one_or_none()

            if not conv:
                title = query.question[:60] if query.question else "Nova Orientacao"
                conv = Conversation(
                    user_id=current_user.id,
                    title=title,
                )
                db.add(conv)
                await db.commit()
                await db.refresh(conv)

            conversation_id = conv.id
            response.conversation_id = conv.id

            # Salvar mensagem do usuario
            user_msg = Message(
                conversation_id=conv.id,
                role="user",
                content=query.question,
            )
            db.add(user_msg)

            # Salvar mensagem do assistente
            asst_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=response.answer,
                steps=response.steps,
                next_action=response.next_action,
                source=response.source,
                document_version=response.version,

                evidence=[e.model_dump() for e in response.evidence] if response.evidence else None,
                confidence=response.confidence,
                requires_human=response.requires_human,
            )
            db.add(asst_msg)
            await db.commit()
            await db.refresh(asst_msg)

            # Usar o ID da mensagem salva como ID da resposta (para permitir feedback posterior)
            response.id = asst_msg.id

            await record_audit_log(
                db=db,
                action="agent_query",
                resource="agent",
                detail=f"Pergunta processada: {query.question[:50]} (requires_human={response.requires_human})",
                user_id=current_user.id,
            )
        except Exception:
            await db.rollback()

    return response


from typing import List
from fastapi import HTTPException
from app.core.deps import require_admin
from app.models.entities import HumanValidation
from app.schemas.schemas import (
    HumanValidationCreate,
    HumanValidationResponse,
    UnansweredQuestionItem,
)


@router.get("/unanswered", response_model=List[UnansweredQuestionItem], status_code=status.HTTP_200_OK)
async def list_unanswered_questions(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[UnansweredQuestionItem]:
    """
    Lista consultas em que o agente realizou abstenção (requires_human=True),
    trazendo a pergunta original do estudante e eventual validação/classificação do admin.
    """
    stmt = (
        select(Message)
        .where(Message.role == "assistant", Message.requires_human.is_(True))
        .order_by(Message.created_at.desc())
    )
    res = await db.execute(stmt)
    abstention_msgs = res.scalars().all()

    val_res = await db.execute(select(HumanValidation).order_by(HumanValidation.created_at.desc()))
    all_validations = val_res.scalars().all()
    latest_val_by_msg = {}
    for v in all_validations:
        if v.message_id not in latest_val_by_msg:
            latest_val_by_msg[v.message_id] = v

    items: List[UnansweredQuestionItem] = []
    for asst_msg in abstention_msgs:
        # Busca a pergunta imediatamente anterior na mesma conversa
        user_stmt = (
            select(Message)
            .where(
                Message.conversation_id == asst_msg.conversation_id,
                Message.role == "user",
                Message.created_at <= asst_msg.created_at,
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        u_res = await db.execute(user_stmt)
        user_msg = u_res.scalar_one_or_none()
        question_text = user_msg.content if user_msg else "Pergunta registrada na conversa"

        val = latest_val_by_msg.get(asst_msg.id)
        items.append(
            UnansweredQuestionItem(
                message_id=asst_msg.id,
                conversation_id=asst_msg.conversation_id,
                question=question_text,
                agent_answer=asst_msg.content,
                confidence=float(asst_msg.confidence or 0.0),
                created_at=asst_msg.created_at,
                validation_status="reviewed" if val else "pending",
                validation_decision=val.decision if val else None,
                classification=val.classification if val else None,
                justification=val.justification if val else None,
            )
        )

    return items


@router.get("/validations", response_model=List[HumanValidationResponse], status_code=status.HTTP_200_OK)
async def list_human_validations(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[HumanValidationResponse]:
    """Lista todas as validações humanas RF08 registradas por administradores."""
    stmt = select(HumanValidation).order_by(HumanValidation.created_at.desc())
    res = await db.execute(stmt)
    validations = res.scalars().all()
    return [HumanValidationResponse.model_validate(v) for v in validations]


@router.post("/validations", response_model=HumanValidationResponse, status_code=status.HTTP_201_CREATED)
async def create_human_validation(
    payload: HumanValidationCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> HumanValidationResponse:
    """
    RF08 — Validação Humana de Resposta do Agente.
    Permite confirmar, ajustar, rejeitar ou complementar uma resposta do agente.
    Exige justificativa para decisões de ajuste, rejeição ou complementação.
    """
    valid_decisions = {"confirm", "adjust", "reject", "complement"}
    if payload.decision not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Decisão inválida. Valores aceitos: {', '.join(sorted(valid_decisions))}.",
        )

    if payload.decision in {"adjust", "reject", "complement"}:
        if not payload.justification or len(payload.justification.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Justificativa é obrigatória (mínimo 5 caracteres) ao ajustar, rejeitar ou complementar uma resposta.",
            )

    stmt = select(Message).where(Message.id == payload.message_id)
    res = await db.execute(stmt)
    msg = res.scalar_one_or_none()
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mensagem do agente não encontrada para validação.",
        )

    # Calcula nova versão da resposta quando ajustada ou complementada
    current_ver = msg.document_version or payload.response_version or "1.0"
    new_version = current_ver
    if payload.decision in {"adjust", "complement"} and payload.adjusted_answer:
        msg.content = payload.adjusted_answer.strip()
        new_version = f"{current_ver}-REV"
        msg.document_version = new_version
        if payload.decision == "adjust":
            msg.requires_human = False

    validation = HumanValidation(
        message_id=msg.id,
        reviewer_id=admin.id,
        decision=payload.decision,
        justification=payload.justification.strip() if payload.justification else "Resposta confirmada pela supervisão.",
        adjusted_answer=payload.adjusted_answer.strip() if payload.adjusted_answer else None,
        classification=payload.classification,
        response_version=new_version,
    )
    db.add(validation)
    await db.commit()
    await db.refresh(validation)

    await record_audit_log(
        db=db,
        action="human_validation_recorded",
        resource="human_validation",
        detail=(
            f"RF08 decisao='{payload.decision}' na mensagem {msg.id} "
            f"(versao={new_version}, class={payload.classification or 'geral'})"
        ),
        user_id=admin.id,
    )

    return HumanValidationResponse.model_validate(validation)

