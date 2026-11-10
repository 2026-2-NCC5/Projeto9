"""
Router de Dashboard Administrativo — Fase 6.
Calcula métricas reais do SQLite (conversas, mensagens, feedbacks, encaminhamentos,
abstenções, validações humanas RF08 e categorias consultadas).
Restrito a administradores (RBAC).
"""
from collections import Counter
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.entities import (
    Feedback,
    HandoffTicket,
    HumanValidation,
    KnowledgeDocument,
    Message,
    User,
)
from app.schemas.schemas import (
    CategoryCountItem,
    DailyQuestionCountItem,
    DashboardMetricsResponse,
)

router = APIRouter()


@router.get("/", response_model=DashboardMetricsResponse, status_code=status.HTTP_200_OK)
async def get_dashboard_metrics(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> DashboardMetricsResponse:
    """Retorna indicadores reais de operação do Agente RAG e atendimento."""
    # 1. Mensagens (user e assistant)
    msg_res = await db.execute(select(Message).order_by(Message.created_at.asc()))
    all_messages = msg_res.scalars().all()

    user_messages = [m for m in all_messages if m.role == "user"]
    assistant_messages = [m for m in all_messages if m.role == "assistant"]

    total_questions = len(user_messages)
    total_answers = len(assistant_messages)

    # Respostas fundamentadas (sem requires_human e com evidencia/source)
    answered_with_evidence = [
        m for m in assistant_messages if not m.requires_human and (m.evidence or m.source)
    ]
    unanswered_messages = [m for m in assistant_messages if m.requires_human]
    unanswered_count = len(unanswered_messages)

    if total_answers > 0:
        answers_with_evidence_rate = round((len(answered_with_evidence) / total_answers) * 100.0, 1)
    else:
        answers_with_evidence_rate = 0.0

    # 2. Feedbacks
    fb_res = await db.execute(select(Feedback))
    feedbacks = fb_res.scalars().all()
    if feedbacks:
        pos_count = sum(1 for f in feedbacks if f.rating in ("positive", "4", "5") or (f.rating_value and f.rating_value >= 4))
        positive_feedback_rate = round((pos_count / len(feedbacks)) * 100.0, 1)
    else:
        positive_feedback_rate = 0.0

    # 3. Encaminhamentos Humanos (Handoffs)
    ho_res = await db.execute(select(HandoffTicket))
    handoffs = ho_res.scalars().all()
    handoffs_count = len(handoffs)

    # 4. Documentos ativos e mapeamento título -> categoria
    doc_res = await db.execute(select(KnowledgeDocument))
    docs = doc_res.scalars().all()
    active_docs = [d for d in docs if d.status == "active"]
    title_to_category = {d.title: d.category for d in docs}

    # 5. Validações Humanas RF08
    val_res = await db.execute(select(HumanValidation))
    validations = val_res.scalars().all()
    validations_count = len(validations)

    # 6. Categorias mais consultadas (baseadas em source das respostas e categorias de handoff)
    category_counter: Counter = Counter()
    for m in assistant_messages:
        if m.source and m.source in title_to_category:
            category_counter[title_to_category[m.source]] += 1
        elif m.requires_human:
            category_counter["abstencao_sem_evidencia"] += 1
    for h in handoffs:
        if h.category:
            category_counter[h.category] += 1

    top_categories = [
        CategoryCountItem(category=cat, count=cnt)
        for cat, cnt in category_counter.most_common(6)
    ]

    # 7. Evolução diária real baseada nas datas das perguntas dos estudantes
    daily_counter: Counter = Counter()
    for m in user_messages:
        if m.created_at:
            day_str = m.created_at.strftime("%d/%m")
            daily_counter[day_str] += 1

    questions_per_day = [
        DailyQuestionCountItem(date=day, count=cnt)
        for day, cnt in list(daily_counter.items())[-7:]
    ]

    # Tempo médio calculado apenas quando há respostas reais (0 se vazio)
    avg_response_time_ms = 0

    return DashboardMetricsResponse(
        total_questions=total_questions,
        total_answers=total_answers,
        answers_with_evidence_rate=answers_with_evidence_rate,
        positive_feedback_rate=positive_feedback_rate,
        handoffs_count=handoffs_count,
        unanswered_count=unanswered_count,
        avg_response_time_ms=avg_response_time_ms,
        active_documents_count=len(active_docs),
        validations_count=validations_count,
        top_categories=top_categories,
        questions_per_day=questions_per_day,
    )
