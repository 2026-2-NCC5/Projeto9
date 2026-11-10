"""
Segunda via de boleto FICTICIA (demonstracao academica).

Regras de seguranca:
- O estudante e SEMPRE derivado do JWT; nenhum student_id e aceito do cliente.
- Boletos de outro estudante respondem 404 (sem revelar existencia).
- Emitir/baixar a segunda via NAO altera o status financeiro.
- "Simular pagamento" apenas registra evento de auditoria (nenhuma transacao).
- Nenhum codigo de barras, PIX ou QR Code de pagamento e gerado.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.documents import build_fictitious_demo_pdf
from app.core.database import engine, get_db
from app.core.deps import get_current_user, record_audit_log
from app.models.entities import Boleto, Student, User

router = APIRouter()

BOLETO_STAMP = (
    "DOCUMENTO FICTÍCIO — AMBIENTE DE DEMONSTRAÇÃO ACADÊMICA — "
    "SEM VALIDADE FINANCEIRA OU BANCÁRIA"
)

_MONTHS_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

# (competencia, vencimento ISO, valor em centavos, status) — dados FICTICIOS
_DEMO_PLAN = {
    "DEMO001": [
        ("2026-07", "2026-07-10", 85000, "pago"),
        ("2026-08", "2026-08-10", 85000, "pendente"),
        ("2026-09", "2026-09-10", 85000, "pendente"),
        ("2026-10", "2026-10-10", 85000, "pendente"),
    ],
    "DEMO002": [
        ("2026-08", "2026-08-10", 92000, "pago"),
        ("2026-09", "2026-09-10", 92000, "pendente"),
        ("2026-10", "2026-10-10", 92000, "pendente"),
    ],
}

_table_ready = False


async def ensure_boletos_table() -> None:
    """Criacao idempotente (checkfirst) apenas da tabela boletos; nao toca em dados existentes."""
    global _table_ready
    if _table_ready:
        return
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Boleto.__table__.create(c, checkfirst=True))
    _table_ready = True


async def seed_demo_boletos(db: AsyncSession, student: Student) -> None:
    """Cria boletos de demonstracao para estudantes demo que ainda nao possuem nenhum (idempotente)."""
    if not student.is_demo:
        return
    existing = (
        await db.execute(select(Boleto.id).where(Boleto.student_id == student.id).limit(1))
    ).first()
    if existing:
        return
    plan = _DEMO_PLAN.get(student.ra, [
        ("2026-09", "2026-09-10", 85000, "pendente"),
        ("2026-10", "2026-10-10", 85000, "pendente"),
    ])
    for comp, due, cents, st in plan:
        db.add(
            Boleto(
                student_id=student.id,
                competence=comp,
                due_date=datetime.fromisoformat(due).replace(tzinfo=timezone.utc),
                amount_cents=cents,
                status=st,
                document_id=f"BOL-DEMO-{student.ra}-{comp.replace('-', '')}",
            )
        )
    await db.commit()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BoletoOut(BaseModel):
    id: str
    competence: str
    competence_label: str
    due_date: str
    amount_cents: int
    amount_label: str
    status: str  # pendente | vencido | pago
    status_label: str
    document_id: str


class PendingResponse(BaseModel):
    boletos: List[BoletoOut]
    count: int
    total_cents: int
    demo: bool = True
    disclaimer: str = BOLETO_STAMP


class SelectionRequest(BaseModel):
    boleto_ids: List[str] = Field(..., min_length=1, max_length=24)


class SimulatePaymentRequest(BaseModel):
    confirm: bool = False


def _brl(cents: int) -> str:
    reais, cent = divmod(cents, 100)
    return f"R$ {reais:,}".replace(",", ".") + f",{cent:02d}"


def _competence_label(comp: str) -> str:
    year, month = comp.split("-")
    return f"{_MONTHS_PT[int(month) - 1]}/{year}"


def _effective_status(b: Boleto) -> str:
    if b.status == "pago":
        return "pago"
    due = b.due_date if b.due_date.tzinfo else b.due_date.replace(tzinfo=timezone.utc)
    return "vencido" if due.date() < datetime.now(timezone.utc).date() else "pendente"


def _to_out(b: Boleto) -> BoletoOut:
    eff = _effective_status(b)
    return BoletoOut(
        id=b.id,
        competence=b.competence,
        competence_label=_competence_label(b.competence),
        due_date=b.due_date.strftime("%d/%m/%Y"),
        amount_cents=b.amount_cents,
        amount_label=_brl(b.amount_cents),
        status=eff,
        status_label={"pago": "Pago", "vencido": "Vencido", "pendente": "A vencer"}[eff],
        document_id=b.document_id,
    )


async def _current_student(user: User, db: AsyncSession) -> Student:
    await ensure_boletos_table()
    student = user.student_profile
    if student is None:
        res = await db.execute(select(Student).where(Student.user_id == user.id))
        student = res.scalar_one_or_none()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Perfil de estudante necessário para consultar boletos.",
        )
    await seed_demo_boletos(db, student)
    return student


async def _owned_boletos(db: AsyncSession, student: Student, ids: List[str]) -> List[Boleto]:
    unique_ids = list(dict.fromkeys(ids))
    res = await db.execute(
        select(Boleto).where(Boleto.student_id == student.id, Boleto.id.in_(unique_ids))
    )
    found = {b.id: b for b in res.scalars().all()}
    if len(found) != len(unique_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Boleto não encontrado para o estudante autenticado.",
        )
    return [found[i] for i in unique_ids]


def _build_pdf(b: Boleto, student: Student) -> bytes:
    paragraphs = [
        "SEGUNDA VIA DE BOLETO — SIMULAÇÃO:",
        f"Estudante (fictício): {student.name}",
        f"RA (fictício): {student.ra}",
        f"Competência: {_competence_label(b.competence)}",
        f"Vencimento: {b.due_date.strftime('%d/%m/%Y')}",
        f"Valor: {_brl(b.amount_cents)}",
        f"Situação: {_to_out(b).status_label}",
        f"Identificação do documento: {b.document_id}",
        "",
        "AVISO:",
        "Este documento não possui código de barras, chave PIX ou QR Code e não pode ser pago.",
        "Não representa cobrança, boleto bancário nem documento oficial da FECAP.",
        "A emissão desta segunda via não altera a situação financeira no ambiente de demonstração.",
        "",
        BOLETO_STAMP,
    ]
    return build_fictitious_demo_pdf(
        title=f"Segunda via de boleto — {_competence_label(b.competence)}",
        category="Financeiro (Demonstração)",
        body_paragraphs=paragraphs,
        doc_key=b.document_id,
        stamp=BOLETO_STAMP,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/pending", response_model=PendingResponse)
async def list_pending_boletos(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PendingResponse:
    """Lista os boletos fictícios pendentes/vencidos do estudante autenticado."""
    student = await _current_student(user, db)
    res = await db.execute(
        select(Boleto)
        .where(Boleto.student_id == student.id, Boleto.status != "pago")
        .order_by(Boleto.due_date)
    )
    items = [_to_out(b) for b in res.scalars().all()]
    await record_audit_log(db, "boletos.list", "boletos", f"pendentes={len(items)}", user.id)
    return PendingResponse(
        boletos=items, count=len(items), total_cents=sum(i.amount_cents for i in items)
    )


@router.post("/summary")
async def selection_summary(
    payload: SelectionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Calcula o total (no backend) dos boletos selecionados."""
    student = await _current_student(user, db)
    selected = await _owned_boletos(db, student, payload.boleto_ids)
    total = sum(b.amount_cents for b in selected)
    return {"count": len(selected), "total_cents": total, "total_label": _brl(total)}


@router.post("/issue")
async def issue_second_copies(
    payload: SelectionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Prepara a segunda via (PDFs individuais) dos boletos escolhidos. NÃO altera status."""
    student = await _current_student(user, db)
    selected = await _owned_boletos(db, student, payload.boleto_ids)
    await record_audit_log(
        db, "boletos.issue", "boletos",
        "documentos=" + ",".join(b.document_id for b in selected), user.id,
    )
    total = sum(b.amount_cents for b in selected)
    return {
        "count": len(selected),
        "total_cents": total,
        "total_label": _brl(total),
        "documents": [
            {
                "id": b.id,
                "document_id": b.document_id,
                "filename": f"{b.document_id}.pdf",
                "competence_label": _competence_label(b.competence),
                "download_url": f"/api/v1/boletos/{b.id}/pdf",
            }
            for b in selected
        ],
        "disclaimer": BOLETO_STAMP,
    }


@router.get("/{boleto_id}/pdf")
async def download_boleto_pdf(
    boleto_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    student = await _current_student(user, db)
    (boleto,) = await _owned_boletos(db, student, [boleto_id])
    pdf_bytes = _build_pdf(boleto, student)
    await record_audit_log(db, "boletos.download", "boletos", boleto.document_id, user.id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{boleto.document_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/{boleto_id}/simulate-payment")
async def simulate_payment(
    boleto_id: str,
    payload: SimulatePaymentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Simulação: apenas registra evento de auditoria. Nenhuma transação; status inalterado."""
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirme que se trata de uma simulação (confirm=true).",
        )
    student = await _current_student(user, db)
    (boleto,) = await _owned_boletos(db, student, [boleto_id])
    await record_audit_log(db, "boletos.simulate_payment", "boletos", boleto.document_id, user.id)
    return {
        "simulated": True,
        "document_id": boleto.document_id,
        "status": _effective_status(boleto),
        "message": (
            "Simulação registrada no ambiente de demonstração. Nenhum pagamento foi realizado "
            "e a situação do boleto não foi alterada."
        ),
        "disclaimer": BOLETO_STAMP,
    }
